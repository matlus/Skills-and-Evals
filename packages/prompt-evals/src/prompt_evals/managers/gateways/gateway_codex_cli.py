import tempfile
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Final, NoReturn, final

from prompt_evals.managers.configuration_providers.settings_models.codex_cli_settings import CodexCliSettings
from prompt_evals.managers.exceptions.llm_session_exceptions import (
    LlmCliProcessContainmentFailedException,
    LlmCliProcessResumeFailedException,
    LlmCliStartFailedException,
    LlmSessionExitedWithErrorException,
    LlmSessionFailedException,
    LlmSessionOutputMalformedBaseException,
    LlmSessionTimeoutException,
)
from prompt_evals.managers.exceptions.process_runner_exceptions import (
    ProcessContainmentFailedException,
    ProcessResumeFailedException,
    ProcessStartFailedException,
    ProcessTimedOutException,
)
from prompt_evals.managers.gateways.codex_cli_resources.codex_event_stream_resources import (
    CodexAgentMessageResource,
    CodexCommandExecutionResource,
    CodexEventStreamResource,
    CodexFileChangeResource,
    CodexToolItemResource,
    CodexTurnFailureResource,
)
from prompt_evals.managers.gateways.codex_cli_resources.validator_codex_event_stream_resource import (
    CODEX_ASSISTANT_NAME,
    ValidatorCodexEventStreamResource,
)
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome
from prompt_evals.managers.models.eval_suite_models import InputFile, ToolKind
from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript, ToolCall, ToolCallOutcome

SANDBOX_DIRECTORY_PREFIX: Final[str] = "prompt-evals-session-"
OUTPUT_SCHEMA_DIRECTORY_PREFIX: Final[str] = "prompt-evals-output-schema-"
OUTPUT_SCHEMA_FILE_NAME: Final[str] = "output_schema.json"
SUCCESSFUL_EXIT_CODE: Final[int] = 0
MILLISECONDS_PER_SECOND: Final[int] = 1000
EXEC_SUBCOMMAND: Final[str] = "exec"
MODEL_OPTION: Final[str] = "-m"
CONFIGURATION_OVERRIDE_OPTION: Final[str] = "-c"
REASONING_EFFORT_OVERRIDE_TEMPLATE: Final[str] = 'model_reasoning_effort="{effort_level}"'
WORKING_DIRECTORY_OPTION: Final[str] = "-C"
OUTPUT_SCHEMA_OPTION: Final[str] = "--output-schema"
# "-" as the prompt argument makes `codex exec` read the prompt from standard input.
PROMPT_FROM_STANDARD_INPUT_ARGUMENT: Final[str] = "-"
EVENT_STREAM_ARGUMENTS: Final[tuple[str, ...]] = ("--json",)

# Every session is a fresh, isolated `codex exec` run:
# --ephemeral keeps eval sessions out of the user's session history;
# --ignore-user-config ignores the user's config.toml, so their profiles, MCP servers and model defaults do not leak in;
# --ignore-rules ignores the user's and the project's rules files;
# --skip-git-repo-check lets Codex run in the sandbox, a temporary directory that is not a git repository.
ISOLATION_ARGUMENTS: Final[tuple[str, ...]] = ("--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check")
# Codex cannot offer a chosen subset of tools the way Claude Code's --tools does: any requested tool kind enables Codex's
# shell and file-edit tools, confined to the sandbox directory. --approve-for-me runs commands in the workspace-write sandbox
# with automatic approval; plain `--sandbox workspace-write` with approval "never" rejects python commands on Windows
# (verified with codex-cli 0.160.0), so a trial could never prove that its code ran.
TOOL_SANDBOX_ARGUMENTS: Final[tuple[str, ...]] = ("--approve-for-me",)
# A session without tools (a grader) may read nothing it was not given and change nothing.
TOOL_LESS_SANDBOX_ARGUMENTS: Final[tuple[str, ...]] = ("--sandbox", "read-only")
START_FAILURE_REMEDY: Final[str] = "Install Codex or set PROMPT_EVALS_CODEX_EXECUTABLE."
ITEM_STATUS_IN_PROGRESS: Final[str] = "in_progress"
ITEM_STATUS_COMPLETED: Final[str] = "completed"
CHANGED_FILE_PATH_SEPARATOR: Final[str] = "\n"
# The domain names tools by what they do; Codex reports every file edit as one file_change item with a kind per file.
TOOL_KIND_BY_CODEX_FILE_CHANGE_KIND: Final[Mapping[str, ToolKind]] = {
    "add": ToolKind.WRITE_FILE,
    "update": ToolKind.EDIT_FILE,
    "delete": ToolKind.EDIT_FILE,
}


@final
class GatewayLlmCodexCli:
    """Runs one session through the OpenAI Codex CLI and answers in the domain's terms, translating tool kinds,
    flags and the `--json` event stream on the way.

    The stream names no model and reports tokens but no cost, so the transcript carries the requested model name
    and no cost; the duration is measured around the process, so a recorded session read again reports no duration.
    """

    def __init__(self, codex_cli_settings: CodexCliSettings, process_runner: ProcessRunnerBase) -> None:
        self._codex_cli_settings: CodexCliSettings = codex_cli_settings
        self._process_runner: ProcessRunnerBase = process_runner

    async def run_session(self, llm_session_request: LlmSessionRequest) -> LlmSessionTranscript:
        started_monotonic_seconds: float = time.monotonic()
        process_outcome: ProcessOutcome = await self._run_in_fresh_sandbox(llm_session_request)
        duration_milliseconds: int = self._measure_elapsed_milliseconds(started_monotonic_seconds)
        if process_outcome.exit_code != SUCCESSFUL_EXIT_CODE:
            self._raise_process_failure(process_outcome, llm_session_request.model_name)
        codex_event_stream_resource: CodexEventStreamResource = ValidatorCodexEventStreamResource.parse_event_stream(
            process_outcome.standard_output_text,
            llm_session_request.model_name,
        )
        self._raise_if_session_failed(codex_event_stream_resource, llm_session_request.model_name)
        return self._map_to_transcript(
            codex_event_stream_resource,
            process_outcome.standard_output_text,
            llm_session_request.model_name,
            structured_output_json=self._read_structured_output_json(llm_session_request, codex_event_stream_resource),
            duration_milliseconds=duration_milliseconds,
        )

    def read_recorded_session(self, event_stream_text: str, model_name: str) -> LlmSessionTranscript:
        codex_event_stream_resource: CodexEventStreamResource = ValidatorCodexEventStreamResource.parse_event_stream(event_stream_text, model_name)
        self._raise_if_session_failed(codex_event_stream_resource, model_name)
        # Recorded sessions are trials, which never request structured output.
        return self._map_to_transcript(
            codex_event_stream_resource, event_stream_text, model_name, structured_output_json=None, duration_milliseconds=None
        )

    async def _run_in_fresh_sandbox(self, llm_session_request: LlmSessionRequest) -> ProcessOutcome:
        with tempfile.TemporaryDirectory(prefix=SANDBOX_DIRECTORY_PREFIX, ignore_cleanup_errors=True) as sandbox_directory_name:
            sandbox_directory: Path = Path(sandbox_directory_name)
            self._write_input_files(sandbox_directory, llm_session_request.input_files)
            if llm_session_request.structured_output_schema is None:
                return await self._run_codex_process(
                    self._compose_process_invocation(llm_session_request, sandbox_directory, None), llm_session_request.model_name
                )
            return await self._run_with_output_schema_file(llm_session_request, sandbox_directory, llm_session_request.structured_output_schema)

    async def _run_with_output_schema_file(
        self, llm_session_request: LlmSessionRequest, sandbox_directory: Path, structured_output_schema: str
    ) -> ProcessOutcome:
        # --output-schema takes a file. It is written outside the sandbox, so it never appears among the session's files.
        with tempfile.TemporaryDirectory(prefix=OUTPUT_SCHEMA_DIRECTORY_PREFIX, ignore_cleanup_errors=True) as output_schema_directory_name:
            output_schema_file: Path = self._write_output_schema_file(Path(output_schema_directory_name), structured_output_schema)
            return await self._run_codex_process(
                self._compose_process_invocation(llm_session_request, sandbox_directory, output_schema_file), llm_session_request.model_name
            )

    @staticmethod
    def _write_input_files(sandbox_directory: Path, input_files: Iterable[InputFile]) -> None:
        for input_file in input_files:
            (sandbox_directory / input_file.file_name).write_bytes(input_file.content)

    @staticmethod
    def _write_output_schema_file(output_schema_directory: Path, structured_output_schema: str) -> Path:
        output_schema_file: Path = output_schema_directory / OUTPUT_SCHEMA_FILE_NAME
        output_schema_file.write_text(structured_output_schema, encoding="utf-8")
        return output_schema_file

    def _compose_process_invocation(
        self, llm_session_request: LlmSessionRequest, sandbox_directory: Path, output_schema_file: Path | None
    ) -> ProcessInvocation:
        return ProcessInvocation(
            command_arguments=self._compose_command_arguments(llm_session_request, sandbox_directory, output_schema_file),
            standard_input_text=llm_session_request.prompt_text,
            working_directory=sandbox_directory,
            timeout_seconds=self._codex_cli_settings.session_timeout_seconds,
        )

    def _compose_command_arguments(
        self, llm_session_request: LlmSessionRequest, sandbox_directory: Path, output_schema_file: Path | None
    ) -> tuple[str, ...]:
        command_arguments: list[str] = [
            self._codex_cli_settings.executable_path,
            EXEC_SUBCOMMAND,
            *EVENT_STREAM_ARGUMENTS,
            *ISOLATION_ARGUMENTS,
            MODEL_OPTION,
            llm_session_request.model_name,
            CONFIGURATION_OVERRIDE_OPTION,
            REASONING_EFFORT_OVERRIDE_TEMPLATE.format(effort_level=llm_session_request.effort_level.value),
            WORKING_DIRECTORY_OPTION,
            str(sandbox_directory),
            *(TOOL_SANDBOX_ARGUMENTS if llm_session_request.tool_kinds else TOOL_LESS_SANDBOX_ARGUMENTS),
        ]
        if output_schema_file is not None:
            command_arguments.extend((OUTPUT_SCHEMA_OPTION, str(output_schema_file)))
        command_arguments.append(PROMPT_FROM_STANDARD_INPUT_ARGUMENT)
        return tuple(command_arguments)

    async def _run_codex_process(self, process_invocation: ProcessInvocation, model_name: str) -> ProcessOutcome:
        try:
            return await self._process_runner.run_process(process_invocation)
        except ProcessStartFailedException as process_start_failed_exception:
            raise LlmCliStartFailedException(
                CODEX_ASSISTANT_NAME,
                self._codex_cli_settings.executable_path,
                process_start_failed_exception.operating_system_error_description,
                START_FAILURE_REMEDY,
            ) from process_start_failed_exception
        except ProcessContainmentFailedException as process_containment_failed_exception:
            raise LlmCliProcessContainmentFailedException(
                CODEX_ASSISTANT_NAME, model_name, process_containment_failed_exception.operating_system_error_description
            ) from process_containment_failed_exception
        except ProcessResumeFailedException as process_resume_failed_exception:
            raise LlmCliProcessResumeFailedException(
                CODEX_ASSISTANT_NAME, model_name, process_resume_failed_exception.operating_system_error_description
            ) from process_resume_failed_exception
        except ProcessTimedOutException as process_timed_out_exception:
            raise LlmSessionTimeoutException(CODEX_ASSISTANT_NAME, model_name, process_invocation.timeout_seconds) from process_timed_out_exception

    @staticmethod
    def _measure_elapsed_milliseconds(started_monotonic_seconds: float) -> int:
        return round((time.monotonic() - started_monotonic_seconds) * MILLISECONDS_PER_SECOND)

    @staticmethod
    def _raise_process_failure(process_outcome: ProcessOutcome, model_name: str) -> NoReturn:
        # Codex reports a failed turn (for example a rejected model) as events on stdout and exits with 1; those events
        # explain the failure, so they are preferred over the exit code whenever stdout holds a readable stream.
        codex_event_stream_resource: CodexEventStreamResource | None = GatewayLlmCodexCli._try_parse_event_stream(
            process_outcome.standard_output_text, model_name
        )
        if codex_event_stream_resource is not None:
            GatewayLlmCodexCli._raise_if_session_failed(codex_event_stream_resource, model_name)
        raise LlmSessionExitedWithErrorException(
            CODEX_ASSISTANT_NAME,
            model_name,
            process_outcome.exit_code,
            process_outcome.standard_error_text,
            process_outcome.standard_output_text,
        )

    @staticmethod
    def _try_parse_event_stream(event_stream_text: str, model_name: str) -> CodexEventStreamResource | None:
        """None when the output of a failed process is not a readable event stream; the exit code then explains the failure."""
        try:
            return ValidatorCodexEventStreamResource.parse_event_stream(event_stream_text, model_name)
        except LlmSessionOutputMalformedBaseException:
            return None

    @staticmethod
    def _raise_if_session_failed(codex_event_stream_resource: CodexEventStreamResource, model_name: str) -> None:
        codex_turn_failure_resource: CodexTurnFailureResource | None = codex_event_stream_resource.codex_turn_failure_resource
        if codex_turn_failure_resource is not None:
            raise LlmSessionFailedException(
                CODEX_ASSISTANT_NAME,
                model_name,
                codex_turn_failure_resource.failure_kind,
                "\n".join(codex_turn_failure_resource.provider_messages),
            )

    @staticmethod
    def _map_to_transcript(
        codex_event_stream_resource: CodexEventStreamResource,
        event_stream_text: str,
        model_name: str,
        *,
        structured_output_json: str | None,
        duration_milliseconds: int | None,
    ) -> LlmSessionTranscript:
        final_message_text: str | None = GatewayLlmCodexCli._read_final_message_text(codex_event_stream_resource.codex_agent_message_resources)
        return LlmSessionTranscript(
            # A session that sent no message answered with nothing.
            final_text="" if final_message_text is None else final_message_text,
            structured_output_json=structured_output_json,
            tool_calls=GatewayLlmCodexCli._map_tool_calls(codex_event_stream_resource.codex_tool_item_resources),
            resolved_model_name=model_name,
            duration_milliseconds=duration_milliseconds,
            total_cost_usd=None,
            event_stream_text=event_stream_text,
        )

    @staticmethod
    def _read_structured_output_json(llm_session_request: LlmSessionRequest, codex_event_stream_resource: CodexEventStreamResource) -> str | None:
        if llm_session_request.structured_output_schema is None:
            return None
        # With --output-schema, the final message is the JSON that matches the schema.
        return GatewayLlmCodexCli._read_final_message_text(codex_event_stream_resource.codex_agent_message_resources)

    @staticmethod
    def _read_final_message_text(codex_agent_message_resources: tuple[CodexAgentMessageResource, ...]) -> str | None:
        if not codex_agent_message_resources:
            return None
        return codex_agent_message_resources[-1].message_text

    @staticmethod
    def _map_tool_calls(codex_tool_item_resources: Iterable[CodexToolItemResource]) -> tuple[ToolCall, ...]:
        return tuple(
            tool_call
            for codex_tool_item_resource in codex_tool_item_resources
            for tool_call in GatewayLlmCodexCli._map_tool_item(codex_tool_item_resource)
        )

    @staticmethod
    def _map_tool_item(codex_tool_item_resource: CodexToolItemResource) -> tuple[ToolCall, ...]:
        match codex_tool_item_resource:
            case CodexCommandExecutionResource():
                return (
                    ToolCall(
                        tool_kind=ToolKind.SHELL,
                        tool_input_text=codex_tool_item_resource.command,
                        tool_call_outcome=GatewayLlmCodexCli._decide_command_outcome(codex_tool_item_resource),
                    ),
                )
            case CodexFileChangeResource():
                return GatewayLlmCodexCli._map_file_change(codex_tool_item_resource)

    @staticmethod
    def _decide_command_outcome(codex_command_execution_resource: CodexCommandExecutionResource) -> ToolCallOutcome:
        if codex_command_execution_resource.status == ITEM_STATUS_IN_PROGRESS:
            return ToolCallOutcome.UNFINISHED
        # Every other final status (failed, declined, ...) and every non-zero exit code is a command that did not succeed.
        is_succeeded: bool = (
            codex_command_execution_resource.status == ITEM_STATUS_COMPLETED and codex_command_execution_resource.exit_code == SUCCESSFUL_EXIT_CODE
        )
        return ToolCallOutcome.SUCCEEDED if is_succeeded else ToolCallOutcome.FAILED

    @staticmethod
    def _map_file_change(codex_file_change_resource: CodexFileChangeResource) -> tuple[ToolCall, ...]:
        file_paths_by_tool_kind: dict[ToolKind, list[str]] = {}
        for codex_file_update_resource in codex_file_change_resource.codex_file_update_resources:
            tool_kind: ToolKind | None = TOOL_KIND_BY_CODEX_FILE_CHANGE_KIND.get(codex_file_update_resource.change_kind)
            # A change kind with no domain tool kind cannot satisfy any check; the full event stream, including that
            # change, is still kept as the trial's event-stream artifact.
            if tool_kind is None:
                continue
            file_paths_by_tool_kind.setdefault(tool_kind, []).append(codex_file_update_resource.file_path)
        tool_call_outcome: ToolCallOutcome = GatewayLlmCodexCli._decide_file_change_outcome(codex_file_change_resource)
        return tuple(
            ToolCall(tool_kind=tool_kind, tool_input_text=CHANGED_FILE_PATH_SEPARATOR.join(file_paths), tool_call_outcome=tool_call_outcome)
            for tool_kind, file_paths in file_paths_by_tool_kind.items()
        )

    @staticmethod
    def _decide_file_change_outcome(codex_file_change_resource: CodexFileChangeResource) -> ToolCallOutcome:
        if codex_file_change_resource.status == ITEM_STATUS_IN_PROGRESS:
            return ToolCallOutcome.UNFINISHED
        return ToolCallOutcome.SUCCEEDED if codex_file_change_resource.status == ITEM_STATUS_COMPLETED else ToolCallOutcome.FAILED
