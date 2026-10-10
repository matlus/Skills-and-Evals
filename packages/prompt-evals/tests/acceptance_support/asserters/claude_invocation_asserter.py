from dataclasses import dataclass

from acceptance_support.test_mediator_coding_assistant_cli import CapturedCliInvocation


@dataclass(frozen=True)
class ExpectedClaudeInvocation:
    invocation_count: int
    model_name: str
    effort_level: str
    tool_names_argument: str
    sandbox_file_names: tuple[str, ...]
    has_structured_output_schema: bool
    allowed_tools_argument: str | None


# --verbose is required for stream-json to include every turn, so it is checked with the isolation flags.
REQUIRED_FLAGS: tuple[str, ...] = ("--restricted", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence", "--verbose")
JSON_SCHEMA_ARGUMENT: str = "--json-schema"


class ClaudeInvocationAsserter:
    """Checks that every captured `claude -p` invocation ran isolated, with the expected model, effort, tools, and sandbox contents."""

    @staticmethod
    def assert_expected_and_actual_are_equal(
        expected_claude_invocation: ExpectedClaudeInvocation,
        actual_claude_invocations: tuple[CapturedCliInvocation, ...],
    ) -> None:
        mismatches: list[str] = []
        if len(actual_claude_invocations) != expected_claude_invocation.invocation_count:
            mismatches.append(f"invocation count: expected {expected_claude_invocation.invocation_count}, actual {len(actual_claude_invocations)}")
        invocation_number: int
        actual_claude_invocation: CapturedCliInvocation
        for invocation_number, actual_claude_invocation in enumerate(actual_claude_invocations, start=1):
            mismatches.extend(
                ClaudeInvocationAsserter._find_invocation_mismatches(
                    f"invocation {invocation_number}", expected_claude_invocation, actual_claude_invocation
                )
            )
        assert not mismatches, f"Claude invocation mismatches ({len(mismatches)}):\n" + "\n".join(mismatches)

    @staticmethod
    def _find_invocation_mismatches(
        invocation_label: str, expected_claude_invocation: ExpectedClaudeInvocation, actual_claude_invocation: CapturedCliInvocation
    ) -> list[str]:
        command_arguments: tuple[str, ...] = actual_claude_invocation.command_arguments
        expected_argument_value_by_argument_name: dict[str, str | None] = {
            "--model": expected_claude_invocation.model_name,
            "--effort": expected_claude_invocation.effort_level,
            "--tools": expected_claude_invocation.tool_names_argument,
            "--permission-mode": "dontAsk",
            "--output-format": "stream-json",
            # Under dontAsk, a tool that is available but not pre-approved is denied on every call.
            "--allowedTools": expected_claude_invocation.allowed_tools_argument,
        }
        invocation_mismatches: list[str] = []
        argument_name: str
        expected_argument_value: str | None
        for argument_name, expected_argument_value in expected_argument_value_by_argument_name.items():
            actual_argument_value: str | None = ClaudeInvocationAsserter._read_argument(command_arguments, argument_name)
            if actual_argument_value != expected_argument_value:
                invocation_mismatches.append(
                    f"{invocation_label}: {argument_name} expected {expected_argument_value!r}, actual {actual_argument_value!r}"
                )
        invocation_mismatches.extend(
            f"{invocation_label}: missing required flag {required_flag}" for required_flag in REQUIRED_FLAGS if required_flag not in command_arguments
        )
        actual_has_structured_output_schema: bool = JSON_SCHEMA_ARGUMENT in command_arguments
        if actual_has_structured_output_schema != expected_claude_invocation.has_structured_output_schema:
            invocation_mismatches.append(
                f"{invocation_label}: {JSON_SCHEMA_ARGUMENT} present expected {expected_claude_invocation.has_structured_output_schema}, "
                f"actual {actual_has_structured_output_schema}"
            )
        if actual_claude_invocation.sandbox_file_names != expected_claude_invocation.sandbox_file_names:
            invocation_mismatches.append(
                f"{invocation_label}: sandbox files expected {expected_claude_invocation.sandbox_file_names}, "
                f"actual {actual_claude_invocation.sandbox_file_names}"
            )
        return invocation_mismatches

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
