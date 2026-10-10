import logging
from typing import Final, final

from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.engines.llm_processors.grader_response_resources.validator_grader_response_resource import ValidatorGraderResponseResource
from prompt_evals.managers.engines.llm_processors.llm_processor_base import LifecycleEventType, LlmProcessorBase
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.models.eval_suite_models import FactExtraction
from prompt_evals.managers.models.grading_models import ExtractedFacts

FACT_EXTRACTION_TASK_HEADING: Final[str] = "# Fact extraction task"


@final
class LlmProcessorAnswerFactsExtraction(LlmProcessorBase):
    """Reads a free-form answer and reports the facts the eval suite's schema asks for, so that code,
    not a model, decides whether each fact is right."""

    def __init__(self, gateway_llm: GatewayLlmProtocol, grading_settings: GradingSettings, logger: logging.Logger) -> None:
        super().__init__(gateway_llm, grading_settings, logger, processor_name="LlmProcessorAnswerFactsExtraction")

    async def extract_answer_facts(self, fact_extraction: FactExtraction, answer_text: str) -> ExtractedFacts:
        prompt_text: str = f"{FACT_EXTRACTION_TASK_HEADING}\n\n{fact_extraction.instructions.strip()}\n\n<answer>\n{answer_text}\n</answer>\n"
        self._publish_lifecycle_event(LifecycleEventType.PROGRESS, "extracting the facts the answer reports")
        extracted_facts: ExtractedFacts = await self._request_structured_output(
            prompt_text, fact_extraction.json_schema, ValidatorGraderResponseResource.parse_extracted_facts
        )
        self._publish_lifecycle_event(LifecycleEventType.COMPLETE, f"extracted {len(extracted_facts.extracted_facts)} facts")
        return extracted_facts
