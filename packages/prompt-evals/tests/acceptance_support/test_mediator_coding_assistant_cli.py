from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from acceptance_support.claude_event_stream_builder import ClaudeEventStreamBuilder
from acceptance_support.codex_event_stream_builder import CodexEventStreamBuilder
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.scripted_cli_sessions import (
    ScriptedAnswerSession,
    ScriptedClaudeEventStreamSession,
    ScriptedCliSession,
    ScriptedCodexEventStreamSession,
    ScriptedFailedStartSession,
    ScriptedRawOutputSession,
    ScriptedTimedOutSession,
)
from prompt_evals.managers.exceptions.process_runner_exceptions import ProcessTimedOutException
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome

# The executables the tests configure (PROMPT_EVALS_CLAUDE_EXECUTABLE, PROMPT_EVALS_CODEX_EXECUTABLE); the launched one
# tells the mediator which CLI's event stream to print.
CLAUDE_EXECUTABLE_PATH: Final[str] = "claude"
CODEX_EXECUTABLE_PATH: Final[str] = "codex"
CLAUDE_MODEL_ARGUMENT: Final[str] = "--model"
CODEX_OUTPUT_SCHEMA_ARGUMENT: Final[str] = "--output-schema"
SUCCESSFUL_EXIT_CODE: Final[int] = 0


@dataclass(frozen=True)
class CapturedCliInvocation:
    """One process the real gateway launched. `output_schema_text` is the content of the schema file Codex was given, if any,
    read while the session ran (the gateway deletes the file afterwards)."""

    command_arguments: tuple[str, ...]
    prompt_text: str
    working_directory: Path
    sandbox_file_names: tuple[str, ...]
    timeout_seconds: float
    output_schema_text: str | None

    @property
    def executable_path(self) -> str:
        return self.command_arguments[0]


@dataclass
class _ScriptedResponse:
    required_prompt_fragments: tuple[str, ...]
    scripted_cli_sessions: list[ScriptedCliSession] = field(default_factory=list[ScriptedCliSession])


class TestMediatorCodingAssistantCli:
    """Scripts what each coding-assistant session does and captures every invocation the real gateways made.

    One mediator answers every CLI an evaluation launches (for example Codex trials graded in Claude Code); the launched
    executable chooses the event-stream format. A response is chosen by the first registration whose prompt fragments all
    appear in the prompt. A registration with several sessions plays them in order, then repeats the last one.
    """

    __test__: bool = False

    def __init__(self) -> None:
        self._scripted_responses: list[_ScriptedResponse] = []
        self._captured_cli_invocations: list[CapturedCliInvocation] = []

    @property
    def captured_cli_invocations(self) -> tuple[CapturedCliInvocation, ...]:
        return tuple(self._captured_cli_invocations)

    @property
    def captured_claude_invocations(self) -> tuple[CapturedCliInvocation, ...]:
        return self._select_captured_invocations(CLAUDE_EXECUTABLE_PATH)

    @property
    def captured_codex_invocations(self) -> tuple[CapturedCliInvocation, ...]:
        return self._select_captured_invocations(CODEX_EXECUTABLE_PATH)

    def script_sessions(self, required_prompt_fragments: tuple[str, ...], *scripted_cli_sessions: ScriptedCliSession) -> None:
        self._scripted_responses.append(_ScriptedResponse(required_prompt_fragments, list(scripted_cli_sessions)))

    def respond_to_invocation(self, process_invocation: ProcessInvocation) -> ProcessOutcome:
        self._captured_cli_invocations.append(self._capture_invocation(process_invocation))
        scripted_cli_session: ScriptedCliSession = self._take_scripted_session(process_invocation.standard_input_text)
        match scripted_cli_session:
            case ScriptedFailedStartSession(raised_exception=raised_exception):
                raise raised_exception
            case ScriptedTimedOutSession():
                raise ProcessTimedOutException(RandomDataGenerator.create_random_process_id(), process_invocation.timeout_seconds, TimeoutError())
            case ScriptedRawOutputSession():
                return ProcessOutcome(
                    exit_code=scripted_cli_session.exit_code,
                    standard_output_text=scripted_cli_session.raw_standard_output_text,
                    standard_error_text=scripted_cli_session.standard_error_text,
                )
            case ScriptedAnswerSession():
                return ProcessOutcome(
                    exit_code=SUCCESSFUL_EXIT_CODE,
                    standard_output_text=self._build_answer_event_stream(process_invocation.command_arguments, scripted_cli_session),
                    standard_error_text="",
                )
            case ScriptedClaudeEventStreamSession():
                return ProcessOutcome(
                    exit_code=scripted_cli_session.exit_code,
                    standard_output_text=self._build_claude_event_stream(process_invocation.command_arguments, scripted_cli_session),
                    standard_error_text=scripted_cli_session.standard_error_text,
                )
            case ScriptedCodexEventStreamSession():
                self._require_launched_executable(process_invocation.command_arguments, CODEX_EXECUTABLE_PATH, scripted_cli_session)
                return ProcessOutcome(
                    exit_code=scripted_cli_session.exit_code,
                    standard_output_text=CodexEventStreamBuilder.build_event_stream(scripted_cli_session),
                    standard_error_text=scripted_cli_session.standard_error_text,
                )

    def _select_captured_invocations(self, executable_path: str) -> tuple[CapturedCliInvocation, ...]:
        return tuple(
            captured_cli_invocation
            for captured_cli_invocation in self._captured_cli_invocations
            if captured_cli_invocation.executable_path == executable_path
        )

    @staticmethod
    def _capture_invocation(process_invocation: ProcessInvocation) -> CapturedCliInvocation:
        working_directory: Path = Path(process_invocation.working_directory)
        return CapturedCliInvocation(
            command_arguments=process_invocation.command_arguments,
            prompt_text=process_invocation.standard_input_text,
            working_directory=working_directory,
            sandbox_file_names=tuple(sorted(sandbox_path.name for sandbox_path in working_directory.iterdir())),
            timeout_seconds=process_invocation.timeout_seconds,
            output_schema_text=TestMediatorCodingAssistantCli._read_output_schema_text(process_invocation.command_arguments),
        )

    @staticmethod
    def _read_output_schema_text(command_arguments: tuple[str, ...]) -> str | None:
        if CODEX_OUTPUT_SCHEMA_ARGUMENT not in command_arguments:
            return None
        output_schema_file: Path = Path(command_arguments[command_arguments.index(CODEX_OUTPUT_SCHEMA_ARGUMENT) + 1])
        return output_schema_file.read_text(encoding="utf-8")

    @staticmethod
    def _build_answer_event_stream(command_arguments: tuple[str, ...], scripted_answer_session: ScriptedAnswerSession) -> str:
        executable_path: str = command_arguments[0]
        if executable_path == CLAUDE_EXECUTABLE_PATH:
            return TestMediatorCodingAssistantCli._build_claude_event_stream(
                command_arguments,
                ScriptedClaudeEventStreamSession(
                    final_text=scripted_answer_session.final_text, structured_output=scripted_answer_session.structured_output
                ),
            )
        if executable_path == CODEX_EXECUTABLE_PATH:
            return CodexEventStreamBuilder.build_event_stream(
                ScriptedCodexEventStreamSession(
                    final_text=scripted_answer_session.final_text, structured_output=scripted_answer_session.structured_output
                )
            )
        raise AssertionError(f"The test launched an executable the mediator does not script: {executable_path!r}")

    @staticmethod
    def _build_claude_event_stream(command_arguments: tuple[str, ...], scripted_claude_event_stream_session: ScriptedClaudeEventStreamSession) -> str:
        TestMediatorCodingAssistantCli._require_launched_executable(command_arguments, CLAUDE_EXECUTABLE_PATH, scripted_claude_event_stream_session)
        requested_model_name: str = command_arguments[command_arguments.index(CLAUDE_MODEL_ARGUMENT) + 1]
        return ClaudeEventStreamBuilder.build_event_stream(requested_model_name, scripted_claude_event_stream_session)

    @staticmethod
    def _require_launched_executable(
        command_arguments: tuple[str, ...], expected_executable_path: str, scripted_cli_session: ScriptedCliSession
    ) -> None:
        if command_arguments[0] != expected_executable_path:
            raise AssertionError(
                f"The test scripted a {type(scripted_cli_session).__name__} for a session that launched {command_arguments[0]!r}, "
                f"not {expected_executable_path!r}"
            )

    def _take_scripted_session(self, prompt_text: str) -> ScriptedCliSession:
        for scripted_response in self._scripted_responses:
            if all(prompt_fragment in prompt_text for prompt_fragment in scripted_response.required_prompt_fragments):
                if len(scripted_response.scripted_cli_sessions) > 1:
                    return scripted_response.scripted_cli_sessions.pop(0)
                return scripted_response.scripted_cli_sessions[0]
        unscripted_prompt_start: str = prompt_text[:120]
        raise AssertionError(f"The test did not script a session for a prompt starting: {unscripted_prompt_start!r}")
