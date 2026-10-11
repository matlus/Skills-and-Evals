import logging
from collections.abc import Callable
from enum import StrEnum
from typing import Final

from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.exceptions.grading_exceptions import GraderResponseBaseException
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript

# A grader that answers with unusable JSON gets one more chance; a second bad answer is a real failure.
GRADER_ATTEMPT_LIMIT: Final[int] = 2


class LifecycleEventType(StrEnum):
    """`PROGRESS` when an LLM operation starts; `COMPLETE` once its result is ready."""

    PROGRESS = "progress"
    COMPLETE = "complete"


class LlmProcessorBase:
    """Shared plumbing for grader processors: one structured-output session per attempt, with one semantic retry."""

    def __init__(
        self,
        gateway_llm: GatewayLlmProtocol,
        grading_settings: GradingSettings,
        logger: logging.Logger,
        *,
        processor_name: str,
    ) -> None:
        self._gateway_llm: GatewayLlmProtocol = gateway_llm
        self._grading_settings: GradingSettings = grading_settings
        self._logger: logging.Logger = logger
        self._processor_name: str = processor_name

    async def _request_structured_output[ParsedResponse](
        self,
        prompt_text: str,
        structured_output_schema: str,
        parse_structured_output: Callable[[str | None, str], ParsedResponse],
    ) -> ParsedResponse:
        llm_session_request: LlmSessionRequest = self._compose_grader_session_request(prompt_text, structured_output_schema)
        attempt_number: int = 1
        while True:
            self._logger.debug("%s: grader attempt %d", self._processor_name, attempt_number)
            llm_session_transcript: LlmSessionTranscript = await self._gateway_llm.run_session(llm_session_request)
            try:
                return parse_structured_output(llm_session_transcript.structured_output_json, self._processor_name)
            except GraderResponseBaseException:
                if attempt_number >= GRADER_ATTEMPT_LIMIT:
                    raise
                attempt_number += 1

    def _publish_lifecycle_event(self, lifecycle_event_type: LifecycleEventType, subject: str) -> None:
        self._logger.debug("%s %s: %s", self._processor_name, lifecycle_event_type, subject)

    def _compose_grader_session_request(self, prompt_text: str, structured_output_schema: str) -> LlmSessionRequest:
        return LlmSessionRequest(
            prompt_text=prompt_text,
            input_files=(),
            model_name=self._grading_settings.grader_model_name,
            effort_level=self._grading_settings.grader_effort_level,
            tool_kinds=(),
            structured_output_schema=structured_output_schema,
        )
