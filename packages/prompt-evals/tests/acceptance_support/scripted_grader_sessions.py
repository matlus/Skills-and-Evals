from dataclasses import dataclass
from typing import Final

from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import STATUS_FACT_NAME, TOTAL_FACT_NAME, SampleEvalSuite
from acceptance_support.scripted_cli_sessions import ScriptedAnswerSession
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

FACT_EXTRACTION_PROMPT_HEADING: Final[str] = "# Fact extraction task"
JUDGMENT_PROMPT_HEADING: Final[str] = "# Grading task"


@dataclass(frozen=True)
class ScriptedDisputedAmount:
    """One amount the scripted judge disputes; the helper writes it under the judge verdict's wire keys."""

    description: str
    answer_amount_text: str
    reference_amount_text: str


def create_judge_verdict_schema_document() -> dict[str, object]:
    """The JSON schema every judgment session must answer through, as the grader's CLI receives it."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["passed", "reason", "disputed_amounts"],
        "properties": {
            "passed": {"type": "boolean"},
            "reason": {"type": "string"},
            "disputed_amounts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["description", "answer_amount", "reference_amount"],
                    "properties": {
                        "description": {"type": "string"},
                        "answer_amount": {"type": "string"},
                        "reference_amount": {"type": "string"},
                    },
                },
            },
        },
    }


def create_extraction_session(reported_total: str, reported_status: str) -> ScriptedAnswerSession:
    return ScriptedAnswerSession(structured_output={TOTAL_FACT_NAME: reported_total, STATUS_FACT_NAME: reported_status})


def create_judge_session(*, is_passed: bool, reason: str, disputed_amounts: tuple[ScriptedDisputedAmount, ...] = ()) -> ScriptedAnswerSession:
    return ScriptedAnswerSession(
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
