from typing import Protocol

from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript


class GatewayLlmProtocol(Protocol):
    async def run_session(self, llm_session_request: LlmSessionRequest) -> LlmSessionTranscript: ...

    def read_recorded_session(self, event_stream_text: str, model_name: str) -> LlmSessionTranscript:
        """Raises an LlmSessionOutputMalformedBaseException leaf when event_stream_text is not a readable event stream for this assistant,
        and LlmSessionFailedException when the recorded session itself failed."""
        ...
