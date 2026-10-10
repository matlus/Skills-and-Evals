from dataclasses import dataclass
from typing import Final

from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import STATUS_FACT_NAME, TOTAL_FACT_NAME, SampleEvalSuite
from acceptance_support.scripted_cli_sessions import ScriptedEventStreamSession
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

FACT_EXTRACTION_PROMPT_HEADING: Final[str] = "# Fact extraction task"
JUDGMENT_PROMPT_HEADING: Final[str] = "# Grading task"


@dataclass(frozen=True)
class ScriptedDisputedAmount:
    """One amount the scripted judge disputes; the helper writes it under the judge verdict's wire keys."""

    description: str
    answer_amount_text: str
    reference_amount_text: str


def create_extraction_session(reported_total: str | None, reported_status: str) -> ScriptedEventStreamSession:
    # Graders use no tools, so the same scripted session prints correctly in whichever assistant the graders run in.
    return ScriptedEventStreamSession(structured_output={TOTAL_FACT_NAME: reported_total, STATUS_FACT_NAME: reported_status})


def create_judge_session(*, is_passed: bool, reason: str, disputed_amounts: tuple[ScriptedDisputedAmount, ...] = ()) -> ScriptedEventStreamSession:
    return ScriptedEventStreamSession(
        structured_output={
            "passed": is_passed,
            "reason": reason,
            "disputed_amounts": [
                {
                    "description": disputed_amount.description,
                    "answer_amount": disputed_amount.answer_amount_text,
                    "reference_amount": disputed_amount.reference_amount_text,
                }
                for disputed_amount in disputed_amounts
            ],
        }
    )


def script_correct_grading(test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli, sample_eval_suite: SampleEvalSuite) -> None:
    test_mediator_coding_assistant_cli.script_sessions(
        (FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(f"${sample_eval_suite.expected_total_amount}", "Over")
    )
    test_mediator_coding_assistant_cli.script_sessions(
        (JUDGMENT_PROMPT_HEADING,), create_judge_session(is_passed=True, reason=RandomDataGenerator.create_random_sentence())
    )
