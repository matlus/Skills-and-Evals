from typing import Final

import pytest
from acceptance_support.random_data_generator import RandomDataGenerator

from prompt_evals.managers.engines.processors.tool_use_check_grading_processor import ToolUseCheckGradingProcessor
from prompt_evals.managers.models.eval_suite_models import ToolKind, ToolUseCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus
from prompt_evals.managers.models.llm_session_models import ToolCall, ToolCallOutcome
from prompt_evals.managers.models.trial_models import TrialIdentity

CHECKED_TOOL_KIND: Final[ToolKind] = ToolKind.SHELL
PYTHON_COMMAND_PATTERN: Final[str] = "\\bpython"


def create_tool_use_check_definition() -> ToolUseCheckDefinition:
    return ToolUseCheckDefinition(
        check_name=RandomDataGenerator.create_random_word(),
        description=RandomDataGenerator.create_random_sentence(),
        minimum_pass_rate=0.8,
        tool_kind=CHECKED_TOOL_KIND,
        tool_input_pattern=PYTHON_COMMAND_PATTERN,
    )


def create_bash_call(command: str, tool_call_outcome: ToolCallOutcome) -> ToolCall:
    return ToolCall(tool_kind=CHECKED_TOOL_KIND, tool_input_text=command, tool_call_outcome=tool_call_outcome)


def create_write_call(content: str) -> ToolCall:
    return ToolCall(tool_kind=ToolKind.WRITE_FILE, tool_input_text=content, tool_call_outcome=ToolCallOutcome.SUCCEEDED)


@pytest.mark.class_test
class TestToolUseCheckGradingProcessor:
    @pytest.mark.parametrize(
        ("tool_calls", "expected_check_status", "expected_successful_count", "expected_matching_count", "expected_named_count"),
        [
            ((create_bash_call("python totals.py", ToolCallOutcome.SUCCEEDED),), CheckStatus.PASSED, 1, 1, 1),
            ((create_bash_call("cd /tmp && Python -c 'print(1)'", ToolCallOutcome.SUCCEEDED),), CheckStatus.PASSED, 1, 1, 1),
            ((create_bash_call("python totals.py", ToolCallOutcome.FAILED),), CheckStatus.FAILED, 0, 1, 1),
            ((create_bash_call("python totals.py", ToolCallOutcome.UNFINISHED),), CheckStatus.FAILED, 0, 1, 1),
            ((create_bash_call("cat personal_expenses.txt", ToolCallOutcome.SUCCEEDED),), CheckStatus.FAILED, 0, 0, 1),
            ((create_write_call("python"),), CheckStatus.FAILED, 0, 0, 0),
            ((), CheckStatus.FAILED, 0, 0, 0),
            (
                (
                    create_bash_call("python totals.py", ToolCallOutcome.FAILED),
                    create_bash_call("python totals.py", ToolCallOutcome.SUCCEEDED),
                    create_write_call("x"),
                ),
                CheckStatus.PASSED,
                1,
                2,
                2,
            ),
            (
                (
                    create_bash_call("ls", ToolCallOutcome.SUCCEEDED),
                    create_bash_call("cat notes.txt", ToolCallOutcome.SUCCEEDED),
                    create_bash_call("python a.py", ToolCallOutcome.SUCCEEDED),
                ),
                CheckStatus.PASSED,
                1,
                1,
                3,
            ),
            (
                (create_bash_call("python totals.py", ToolCallOutcome.FAILED), create_bash_call("ls", ToolCallOutcome.SUCCEEDED)),
                CheckStatus.FAILED,
                0,
                1,
                2,
            ),
            ((create_bash_call("cat > an.py <<'EOF'\nprint(1)\nEOF\npython an.py", ToolCallOutcome.SUCCEEDED),), CheckStatus.PASSED, 1, 1, 1),
        ],
        ids=[
            "python-ran",
            "python-case-insensitive",
            "python-errored",
            "python-unfinished",
            "other-command",
            "other-tool",
            "no-calls",
            "retry-succeeded-second",
            "python-ran-last",
            "only-unrelated-call-succeeded",
            "python-after-a-heredoc-newline",
        ],
    )
    def test_GradeToolUseCheck_WhenTheLogHasTheseToolCalls_ThenOnlyASuccessfulMatchingCallPasses(
        self,
        tool_calls: tuple[ToolCall, ...],
        expected_check_status: CheckStatus,
        expected_successful_count: int,
        expected_matching_count: int,
        expected_named_count: int,
    ) -> None:
        # Arrange
        trial_identity: TrialIdentity = TrialIdentity(
            variant_name=RandomDataGenerator.create_random_word(), case_name=RandomDataGenerator.create_random_word(), repetition_number=1
        )
        expected_reason: str = (
            f"{expected_successful_count} successful of {expected_matching_count} {CHECKED_TOOL_KIND} calls matching "
            f"'{PYTHON_COMMAND_PATTERN}' ({expected_named_count} {CHECKED_TOOL_KIND} calls in total)"
        )

        # Act
        actual_check_outcome: CheckOutcome = ToolUseCheckGradingProcessor.grade_tool_use_check(
            create_tool_use_check_definition(), tool_calls, trial_identity
        )

        # Assert
        assert (actual_check_outcome.check_status, actual_check_outcome.reason) == (expected_check_status, expected_reason), (
            f"expected {expected_check_status}: {expected_reason!r}; actual {actual_check_outcome.check_status}: {actual_check_outcome.reason!r}"
        )
