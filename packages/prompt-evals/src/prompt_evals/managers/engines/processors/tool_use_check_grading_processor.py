import re
from collections.abc import Iterable
from typing import final

from prompt_evals.managers.models.eval_suite_models import ToolKind, ToolUseCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus
from prompt_evals.managers.models.llm_session_models import ToolCall, ToolCallOutcome
from prompt_evals.managers.models.trial_models import TrialIdentity


@final
class ToolUseCheckGradingProcessor:
    """Reads the session's tool-call log: passes when at least one call to the tool, with input
    matching the pattern, completed without error."""

    @staticmethod
    def grade_tool_use_check(
        tool_use_check_definition: ToolUseCheckDefinition,
        tool_calls: tuple[ToolCall, ...],
        trial_identity: TrialIdentity,
    ) -> CheckOutcome:
        tool_calls_of_kind: list[ToolCall] = ToolUseCheckGradingProcessor._select_tool_calls_of_kind(tool_calls, tool_use_check_definition.tool_kind)
        matching_tool_calls: list[ToolCall] = ToolUseCheckGradingProcessor._select_matching_tool_calls(
            tool_calls_of_kind, tool_use_check_definition.tool_input_pattern
        )
        successful_tool_call_count: int = ToolUseCheckGradingProcessor._count_successful_tool_calls(matching_tool_calls)
        return CheckOutcome(
            check_name=tool_use_check_definition.check_name,
            trial_identity=trial_identity,
            check_status=CheckStatus.PASSED if successful_tool_call_count else CheckStatus.FAILED,
            reason=(
                f"{successful_tool_call_count} successful of {len(matching_tool_calls)} {tool_use_check_definition.tool_kind} calls matching "
                f"'{tool_use_check_definition.tool_input_pattern}' ({len(tool_calls_of_kind)} {tool_use_check_definition.tool_kind} calls in total)"
            ),
            amount_discrepancy_diagnoses=(),
        )

    @staticmethod
    def _select_tool_calls_of_kind(tool_calls: Iterable[ToolCall], tool_kind: ToolKind) -> list[ToolCall]:
        return [tool_call for tool_call in tool_calls if tool_call.tool_kind == tool_kind]

    @staticmethod
    def _count_successful_tool_calls(matching_tool_calls: Iterable[ToolCall]) -> int:
        return sum(1 for tool_call in matching_tool_calls if tool_call.tool_call_outcome == ToolCallOutcome.SUCCEEDED)

    @staticmethod
    def _select_matching_tool_calls(tool_calls_of_kind: Iterable[ToolCall], tool_input_pattern: str) -> list[ToolCall]:
        compiled_tool_input_pattern: re.Pattern[str] = re.compile(tool_input_pattern, re.IGNORECASE)
        return [tool_call for tool_call in tool_calls_of_kind if compiled_tool_input_pattern.search(tool_call.tool_input_text)]
