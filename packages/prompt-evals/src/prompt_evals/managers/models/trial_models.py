from dataclasses import dataclass

from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript


@dataclass(frozen=True)
class TrialIdentity:
    variant_name: str
    case_name: str
    repetition_number: int


@dataclass(frozen=True)
class CompletedTrial:
    trial_identity: TrialIdentity
    llm_session_transcript: LlmSessionTranscript


@dataclass(frozen=True)
class ErroredTrial:
    trial_identity: TrialIdentity
    error_description: str


type TrialRecord = CompletedTrial | ErroredTrial


@dataclass(frozen=True)
class TrialAssignment:
    trial_identity: TrialIdentity
    llm_session_request: LlmSessionRequest
