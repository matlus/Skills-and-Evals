import json
import logging
from typing import Final, final

from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.engines.llm_processors.grader_response_resources.validator_grader_response_resource import ValidatorGraderResponseResource
from prompt_evals.managers.engines.llm_processors.llm_processor_base import LifecycleEventType, LlmProcessorBase
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.models.grading_models import JudgeVerdict

JUDGMENT_TASK_HEADING: Final[str] = "# Grading task"
JUDGMENT_INSTRUCTIONS: Final[str] = (
    "You are grading one answer that an AI assistant gave to a user. Apply the rubric exactly as written and judge only "
    "what the answer says. Give a one- or two-sentence reason that names the specific evidence you relied on.\n\n"
    "If the answer fails because an amount it states contradicts a reference value given in the rubric, list each such "
    "amount in disputed_amounts: what it measures, the amount exactly as the answer states it, and the reference value it "
    "contradicts exactly as the rubric states it. Leave disputed_amounts empty when the answer passes, and do not list an "
    "amount that only disagrees with the answer's own tables."
)
JUDGE_VERDICT_SCHEMA: Final[str] = json.dumps(
    {
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
    },
    separators=(",", ":"),
)


@final
class LlmProcessorRubricJudgment(LlmProcessorBase):
    """LLM-as-judge: a separate model session decides pass or fail against a written rubric."""

    def __init__(self, gateway_llm: GatewayLlmProtocol, grading_settings: GradingSettings, logger: logging.Logger) -> None:
        super().__init__(gateway_llm, grading_settings, logger, processor_name="LlmProcessorRubricJudgment")

    async def judge_answer(self, rubric: str, answer_text: str) -> JudgeVerdict:
        prompt_text: str = (
            f"{JUDGMENT_TASK_HEADING}\n\n{JUDGMENT_INSTRUCTIONS}\n\n<rubric>\n{rubric.strip()}\n</rubric>\n\n<answer>\n{answer_text}\n</answer>\n"
        )
        self._publish_lifecycle_event(LifecycleEventType.PROGRESS, "judging the answer against the rubric")
        judge_verdict: JudgeVerdict = await self._request_structured_output(
            prompt_text, JUDGE_VERDICT_SCHEMA, ValidatorGraderResponseResource.parse_judge_verdict
        )
        self._publish_lifecycle_event(LifecycleEventType.COMPLETE, f"the answer {'passed' if judge_verdict.is_passed else 'failed'} the rubric")
        return judge_verdict
