import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from acceptance_support.test_mediator_coding_assistant_cli import CapturedCliInvocation


@dataclass(frozen=True)
class ExpectedCodexInvocation:
    """`sandbox_mode` is the expected --sandbox value (None: no --sandbox); `approves_commands` expects --approve-for-me.
    `output_schema_document` is the JSON the --output-schema file is expected to hold (None: no schema file)."""

    invocation_count: int
    model_name: str
    effort_level: str
    sandbox_mode: str | None
    approves_commands: bool
    sandbox_file_names: tuple[str, ...]
    output_schema_document: dict[str, object] | None


EXEC_SUBCOMMAND: Final[str] = "exec"
# --json is required for the event stream the gateway reads, so it is checked with the isolation flags.
REQUIRED_FLAGS: Final[tuple[str, ...]] = ("--json", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check")
APPROVE_FOR_ME_FLAG: Final[str] = "--approve-for-me"
OUTPUT_SCHEMA_ARGUMENT: Final[str] = "--output-schema"
WORKING_DIRECTORY_ARGUMENT: Final[str] = "-C"
PROMPT_FROM_STANDARD_INPUT_ARGUMENT: Final[str] = "-"


class CodexInvocationAsserter:
    """Checks that every captured `codex exec` invocation ran isolated, with the expected model, effort, sandbox, and schema file."""

    @staticmethod
    def assert_expected_and_actual_are_equal(
        expected_codex_invocation: ExpectedCodexInvocation,
        actual_codex_invocations: tuple[CapturedCliInvocation, ...],
    ) -> None:
        mismatches: list[str] = []
        if len(actual_codex_invocations) != expected_codex_invocation.invocation_count:
            mismatches.append(f"invocation count: expected {expected_codex_invocation.invocation_count}, actual {len(actual_codex_invocations)}")
        invocation_number: int
        actual_codex_invocation: CapturedCliInvocation
        for invocation_number, actual_codex_invocation in enumerate(actual_codex_invocations, start=1):
            mismatches.extend(
                CodexInvocationAsserter._find_invocation_mismatches(
                    f"invocation {invocation_number}", expected_codex_invocation, actual_codex_invocation
                )
            )
        mismatch_lines: str = "\n".join(mismatches)
        assert not mismatches, f"Codex invocation mismatches ({len(mismatches)}):\n{mismatch_lines}"

    @staticmethod
    def _find_invocation_mismatches(
        invocation_label: str, expected_codex_invocation: ExpectedCodexInvocation, actual_codex_invocation: CapturedCliInvocation
    ) -> list[str]:
        invocation_mismatches: list[str] = []
        invocation_mismatches.extend(CodexInvocationAsserter._find_command_shape_mismatches(invocation_label, actual_codex_invocation))
        invocation_mismatches.extend(
            CodexInvocationAsserter._find_argument_value_mismatches(invocation_label, expected_codex_invocation, actual_codex_invocation)
        )
        invocation_mismatches.extend(
            CodexInvocationAsserter._find_sandbox_mismatches(invocation_label, expected_codex_invocation, actual_codex_invocation)
        )
        return invocation_mismatches

    @staticmethod
    def _find_command_shape_mismatches(invocation_label: str, actual_codex_invocation: CapturedCliInvocation) -> list[str]:
        command_arguments: tuple[str, ...] = actual_codex_invocation.command_arguments
        command_shape_mismatches: list[str] = [
            f"{invocation_label}: missing required flag {required_flag}" for required_flag in REQUIRED_FLAGS if required_flag not in command_arguments
        ]
        if command_arguments[1:2] != (EXEC_SUBCOMMAND,):
            command_shape_mismatches.append(f"{invocation_label}: expected the {EXEC_SUBCOMMAND!r} subcommand, actual {command_arguments[1:2]}")
        # The prompt travels on standard input, which `codex exec` reads only when the prompt argument is "-".
        if command_arguments[-1:] != (PROMPT_FROM_STANDARD_INPUT_ARGUMENT,):
            command_shape_mismatches.append(f"{invocation_label}: expected the prompt argument '-' last, actual {command_arguments[-1:]}")
        return command_shape_mismatches

    @staticmethod
    def _find_argument_value_mismatches(
        invocation_label: str, expected_codex_invocation: ExpectedCodexInvocation, actual_codex_invocation: CapturedCliInvocation
    ) -> list[str]:
        expected_argument_value_by_argument_name: dict[str, str | None] = {
            "-m": expected_codex_invocation.model_name,
            "-c": f'model_reasoning_effort="{expected_codex_invocation.effort_level}"',
            # The session's working root is the sandbox the gateway filled with the case inputs.
            WORKING_DIRECTORY_ARGUMENT: str(actual_codex_invocation.working_directory),
            "--sandbox": expected_codex_invocation.sandbox_mode,
        }
        argument_value_mismatches: list[str] = []
        argument_name: str
        expected_argument_value: str | None
        for argument_name, expected_argument_value in expected_argument_value_by_argument_name.items():
            actual_argument_value: str | None = CodexInvocationAsserter._read_argument(actual_codex_invocation.command_arguments, argument_name)
            if actual_argument_value != expected_argument_value:
                argument_value_mismatches.append(
                    f"{invocation_label}: {argument_name} expected {expected_argument_value!r}, actual {actual_argument_value!r}"
                )
        expected_approves_commands: bool = expected_codex_invocation.approves_commands
        actual_approves_commands: bool = APPROVE_FOR_ME_FLAG in actual_codex_invocation.command_arguments
        if actual_approves_commands != expected_approves_commands:
            argument_value_mismatches.append(
                f"{invocation_label}: {APPROVE_FOR_ME_FLAG} present expected {expected_approves_commands}, actual {actual_approves_commands}"
            )
        return argument_value_mismatches

    @staticmethod
    def _find_sandbox_mismatches(
        invocation_label: str, expected_codex_invocation: ExpectedCodexInvocation, actual_codex_invocation: CapturedCliInvocation
    ) -> list[str]:
        sandbox_mismatches: list[str] = []
        expected_sandbox_file_names: tuple[str, ...] = expected_codex_invocation.sandbox_file_names
        actual_sandbox_file_names: tuple[str, ...] = actual_codex_invocation.sandbox_file_names
        if actual_sandbox_file_names != expected_sandbox_file_names:
            sandbox_mismatches.append(f"{invocation_label}: sandbox files expected {expected_sandbox_file_names}, actual {actual_sandbox_file_names}")
        expected_output_schema_document: dict[str, object] | None = expected_codex_invocation.output_schema_document
        actual_output_schema_document: object = (
            None if actual_codex_invocation.output_schema_text is None else json.loads(actual_codex_invocation.output_schema_text)
        )
        if actual_output_schema_document != expected_output_schema_document:
            sandbox_mismatches.append(
                f"{invocation_label}: output schema expected {expected_output_schema_document!r}, actual {actual_output_schema_document!r}"
            )
        output_schema_argument: str | None = CodexInvocationAsserter._read_argument(actual_codex_invocation.command_arguments, OUTPUT_SCHEMA_ARGUMENT)
        # A schema file inside the sandbox would let the session read, or rewrite, what its answer is checked against.
        if output_schema_argument is not None and Path(output_schema_argument).is_relative_to(actual_codex_invocation.working_directory):
            sandbox_mismatches.append(f"{invocation_label}: the output schema file {output_schema_argument!r} is inside the sandbox")
        return sandbox_mismatches

    @staticmethod
    def _read_argument(command_arguments: tuple[str, ...], argument_name: str) -> str | None:
        # The CLI honours the last occurrence of a repeated flag, so a repeat would make the first value misleading.
        argument_positions: list[int] = [position for position, command_argument in enumerate(command_arguments) if command_argument == argument_name]
        if not argument_positions:
            return None
        if len(argument_positions) > 1:
            return f"<{argument_name} given {len(argument_positions)} times>"
        value_position: int = argument_positions[0] + 1
        if value_position >= len(command_arguments):
            return f"<{argument_name} given without a value>"
        return command_arguments[value_position]
