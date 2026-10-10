import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Final, NoReturn, cast, final

from prompt_evals.managers.configuration_providers.settings_models.claude_cli_settings import ClaudeCliSettings
from prompt_evals.managers.exceptions.llm_session_exceptions import (
    LlmCliStartFailedException,
    LlmSessionExitedWithErrorException,
    LlmSessionFailedException,
    LlmSessionOutputMalformedException,
    LlmSessionTimeoutException,
)
from prompt_evals.managers.gateways.claude_cli_resources.claude_event_stream_resources import (
    ClaudeEventStreamResource,
    ClaudeResultResource,
    ClaudeToolResultResource,
)
from prompt_evals.managers.gateways.claude_cli_resources.validator_claude_event_stream_resource import (
    CLAUDE_CODE_ASSISTANT_NAME,
    ValidatorClaudeEventStreamResource,
)
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome
from prompt_evals.managers.models.eval_suite_models import InputFile, ToolKind
from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript, ToolCall, ToolCallOutcome

SANDBOX_DIRECTORY_PREFIX: Final[str] = "prompt-evals-session-"
SUCCESSFUL_EXIT_CODE: Final[int] = 0
# Every other result subtype (error_during_execution, error_max_turns, ...) is a failed session, whatever is_error says.
SUCCESS_RESULT_SUBTYPE: Final[str] = "success"

# Every session is a fresh, isolated `claude -p` run:
# --restricted ignores the user's settings files (so their plugins, hooks and permission rules do not
#   leak in) and confines file tools to the sandbox working directory;
# --strict-mcp-config with no --mcp-config loads no MCP servers; --disable-slash-commands loads no skills;
# --no-session-persistence keeps eval sessions out of the user's session history;
# --permission-mode dontAsk denies anything not pre-approved instead of waiting for a human.
ISOLATION_ARGUMENTS: Final[tuple[str, ...]] = (
    "--restricted",
    "--strict-mcp-config",
    "--disable-slash-commands",
    "--no-session-persistence",
    "--permission-mode",
    "dontAsk",
)
EVENT_STREAM_ARGUMENTS: Final[tuple[str, ...]] = ("--output-format", "stream-json", "--verbose")
START_FAILURE_REMEDY: Final[str] = "Install Claude Code or set PROMPT_EVALS_CLAUDE_EXECUTABLE."
TOOL_INPUT_LINE_SEPARATOR: Final[str] = "\n"
# The domain names tools by what they do; Claude Code has its own name for each.
CLAUDE_TOOL_NAME_BY_TOOL_KIND: Final[Mapping[ToolKind, str]] = {
    ToolKind.SHELL: "Bash",
    ToolKind.READ_FILE: "Read",
    ToolKind.WRITE_FILE: "Write",
    ToolKind.EDIT_FILE: "Edit",
    ToolKind.FIND_FILES: "Glob",
    ToolKind.SEARCH_FILE_CONTENTS: "Grep",
}
TOOL_KIND_BY_CLAUDE_TOOL_NAME: Final[Mapping[str, ToolKind]] = {
    claude_tool_name: tool_kind for tool_kind, claude_tool_name in CLAUDE_TOOL_NAME_BY_TOOL_KIND.items()
}
# A check matches what a call ran or touched, so only the input fields that carry it count, as with Codex: the model's own
# narration of a call (Bash's description) and the text a call writes (Write's content, Edit's old and new strings) do not.
CLAUDE_TOOL_INPUT_FIELD_NAMES_BY_TOOL_KIND: Final[Mapping[ToolKind, tuple[str, ...]]] = {
    ToolKind.SHELL: ("command",),
    ToolKind.READ_FILE: ("file_path",),
    ToolKind.WRITE_FILE: ("file_path",),
    ToolKind.EDIT_FILE: ("file_path",),
    ToolKind.FIND_FILES: ("pattern", "path"),
    ToolKind.SEARCH_FILE_CONTENTS: ("pattern", "path", "glob"),
}


@final
class GatewayLlmClaudeCli:
    """Runs one session through the Claude Code CLI and answers in the domain's terms, translating tool kinds,
    flags and the stream-json format on the way."""

    def __init__(self, claude_cli_settings: ClaudeCliSettings, process_runner: ProcessRunnerBase) -> None:
        self._claude_cli_settings: ClaudeCliSettings = claude_cli_settings
        self._process_runner: ProcessRunnerBase = process_runner

    async def run_session(self, llm_session_request: LlmSessionRequest) -> LlmSessionTranscript:
        process_outcome: ProcessOutcome = await self._run_in_fresh_sandbox(llm_session_request)
        if process_outcome.exit_code != SUCCESSFUL_EXIT_CODE:
            self._raise_process_failure(process_outcome, llm_session_request.model_name)
        claude_event_stream_resource: ClaudeEventStreamResource = ValidatorClaudeEventStreamResource.parse_event_stream(
            process_outcome.standard_output_text,
            llm_session_request.model_name,
        )
        self._raise_if_session_failed(claude_event_stream_resource, llm_session_request.model_name)
        return self._map_to_transcript(claude_event_stream_resource, process_outcome.standard_output_text)

    def read_recorded_session(self, event_stream_text: str, model_name: str) -> LlmSessionTranscript:
        claude_event_stream_resource: ClaudeEventStreamResource = ValidatorClaudeEventStreamResource.parse_event_stream(event_stream_text, model_name)
        self._raise_if_session_failed(claude_event_stream_resource, model_name)
        return self._map_to_transcript(claude_event_stream_resource, event_stream_text)

    async def _run_in_fresh_sandbox(self, llm_session_request: LlmSessionRequest) -> ProcessOutcome:
        with tempfile.TemporaryDirectory(prefix=SANDBOX_DIRECTORY_PREFIX, ignore_cleanup_errors=True) as sandbox_directory_name:
            sandbox_directory: Path = Path(sandbox_directory_name)
            self._write_input_files(sandbox_directory, llm_session_request.input_files)
            return await self._run_claude_process(
                self._compose_process_invocation(llm_session_request, sandbox_directory),
                llm_session_request.model_name,
            )

    @staticmethod
    def _write_input_files(sandbox_directory: Path, input_files: tuple[InputFile, ...]) -> None:
        for input_file in input_files:
            (sandbox_directory / input_file.file_name).write_bytes(input_file.content)

    def _compose_process_invocation(self, llm_session_request: LlmSessionRequest, sandbox_directory: Path) -> ProcessInvocation:
        return ProcessInvocation(
            command_arguments=self._compose_command_arguments(llm_session_request),
            standard_input_text=llm_session_request.prompt_text,
            working_directory=sandbox_directory,
            timeout_seconds=self._claude_cli_settings.session_timeout_seconds,
        )

    @staticmethod
    def _raise_process_failure(process_outcome: ProcessOutcome, model_name: str) -> NoReturn:
        # Claude Code writes an error result (for example an API error) to stdout and can exit non-zero with stderr empty;
        # that result explains the failure, so it is preferred over the exit code whenever stdout holds a readable one.
        claude_event_stream_resource: ClaudeEventStreamResource | None = GatewayLlmClaudeCli._try_parse_event_stream(
            process_outcome.standard_output_text, model_name
        )
        if claude_event_stream_resource is not None:
            GatewayLlmClaudeCli._raise_if_session_failed(claude_event_stream_resource, model_name)
        raise LlmSessionExitedWithErrorException(
            CLAUDE_CODE_ASSISTANT_NAME,
            model_name,
            process_outcome.exit_code,
            process_outcome.standard_error_text,
            process_outcome.standard_output_text,
        )

    @staticmethod
    def _try_parse_event_stream(event_stream_text: str, model_name: str) -> ClaudeEventStreamResource | None:
        """None when the output of a failed process is not a readable event stream; the exit code then explains the failure."""
        try:
            return ValidatorClaudeEventStreamResource.parse_event_stream(event_stream_text, model_name)
        except LlmSessionOutputMalformedException:
            return None

    @staticmethod
    def _raise_if_session_failed(claude_event_stream_resource: ClaudeEventStreamResource, model_name: str) -> None:
        claude_result_resource: ClaudeResultResource = claude_event_stream_resource.claude_result_resource
        if claude_result_resource.is_error or claude_result_resource.subtype != SUCCESS_RESULT_SUBTYPE:
            raise LlmSessionFailedException(
                CLAUDE_CODE_ASSISTANT_NAME,
                model_name,
                claude_result_resource.subtype,
                GatewayLlmClaudeCli._describe_session_failure(claude_result_resource),
            )

    @staticmethod
    def _describe_session_failure(claude_result_resource: ClaudeResultResource) -> str:
        return "\n".join(
            failure_text for failure_text in (claude_result_resource.result_text, *claude_result_resource.error_messages) if failure_text
        )

    def _compose_command_arguments(self, llm_session_request: LlmSessionRequest) -> tuple[str, ...]:
        tool_names_argument: str = ",".join(CLAUDE_TOOL_NAME_BY_TOOL_KIND[tool_kind] for tool_kind in llm_session_request.tool_kinds)
        command_arguments: list[str] = [
            self._claude_cli_settings.executable_path,
            "-p",
            "--model",
            llm_session_request.model_name,
            "--effort",
            llm_session_request.effort_level.value,
            *ISOLATION_ARGUMENTS,
            "--tools",
            tool_names_argument,
            *EVENT_STREAM_ARGUMENTS,
        ]
        if llm_session_request.tool_kinds:
            command_arguments.extend(("--allowedTools", tool_names_argument))
        if llm_session_request.structured_output_schema is not None:
            command_arguments.extend(("--json-schema", llm_session_request.structured_output_schema))
        return tuple(command_arguments)

    async def _run_claude_process(self, process_invocation: ProcessInvocation, model_name: str) -> ProcessOutcome:
        try:
            return await self._process_runner.run_process(process_invocation)
        except TimeoutError as timeout_error:
            raise LlmSessionTimeoutException(CLAUDE_CODE_ASSISTANT_NAME, model_name, process_invocation.timeout_seconds) from timeout_error
        except OSError as operating_system_error:
            # TimeoutError is itself an OSError, so it must be caught first. Every other OSError here means the
            # executable could not be started: missing, not executable, or not a valid program for this platform.
            raise LlmCliStartFailedException(
                CLAUDE_CODE_ASSISTANT_NAME,
                self._claude_cli_settings.executable_path,
                f"{type(operating_system_error).__name__}: {operating_system_error}",
                START_FAILURE_REMEDY,
            ) from operating_system_error

    @staticmethod
    def _map_to_transcript(claude_event_stream_resource: ClaudeEventStreamResource, event_stream_text: str) -> LlmSessionTranscript:
        claude_result_resource: ClaudeResultResource = claude_event_stream_resource.claude_result_resource
        return LlmSessionTranscript(
            final_text=claude_result_resource.result_text,
            structured_output_json=claude_result_resource.structured_output_json,
            tool_calls=GatewayLlmClaudeCli._map_tool_calls(claude_event_stream_resource),
            resolved_model_name=claude_event_stream_resource.model_name,
            duration_milliseconds=claude_result_resource.duration_milliseconds,
            total_cost_usd=claude_result_resource.total_cost_usd,
            event_stream_text=event_stream_text,
        )

    @staticmethod
    def _map_tool_calls(claude_event_stream_resource: ClaudeEventStreamResource) -> tuple[ToolCall, ...]:
        claude_tool_result_resource_by_tool_use_id: dict[str, ClaudeToolResultResource] = {
            claude_tool_result_resource.tool_use_id: claude_tool_result_resource
            for claude_tool_result_resource in claude_event_stream_resource.claude_tool_result_resources
        }
        tool_calls: list[ToolCall] = []
        for claude_tool_use_resource in claude_event_stream_resource.claude_tool_use_resources:
            tool_kind: ToolKind | None = TOOL_KIND_BY_CLAUDE_TOOL_NAME.get(claude_tool_use_resource.tool_name)
            # A Claude Code tool with no domain tool kind (an internal tool) cannot satisfy any check; the full
            # event stream, including that call, is still kept as the trial's event-stream artifact.
            if tool_kind is None:
                continue
            tool_calls.append(
                ToolCall(
                    tool_kind=tool_kind,
                    tool_input_text=GatewayLlmClaudeCli._read_tool_input_text(tool_kind, claude_tool_use_resource.tool_input_json),
                    tool_call_outcome=GatewayLlmClaudeCli._decide_tool_call_outcome(
                        claude_tool_result_resource_by_tool_use_id.get(claude_tool_use_resource.tool_use_id)
                    ),
                )
            )
        return tuple(tool_calls)

    @staticmethod
    def _decide_tool_call_outcome(claude_tool_result_resource: ClaudeToolResultResource | None) -> ToolCallOutcome:
        if claude_tool_result_resource is None:
            return ToolCallOutcome.UNFINISHED
        return ToolCallOutcome.FAILED if claude_tool_result_resource.is_error else ToolCallOutcome.SUCCEEDED

    @staticmethod
    def _read_tool_input_text(tool_kind: ToolKind, tool_input_json: str) -> str:
        # Keep what the model typed, not its JSON encoding. Encoded, a newline becomes a backslash and an "n",
        # so a command ending with a heredoc and then "python an.py" would hide the word boundary in front of "python".
        tool_input: object = json.loads(tool_input_json)
        if not isinstance(tool_input, dict):
            return ""
        tool_input_object: dict[str, object] = cast(dict[str, object], tool_input)
        field_values: list[object] = [tool_input_object.get(field_name) for field_name in CLAUDE_TOOL_INPUT_FIELD_NAMES_BY_TOOL_KIND[tool_kind]]
        return TOOL_INPUT_LINE_SEPARATOR.join(field_value for field_value in field_values if isinstance(field_value, str))
