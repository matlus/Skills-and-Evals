from dataclasses import dataclass

from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript


@dataclass(frozen=True)
class TrialIdentity:
    variant_name: str
    case_name: str
    repetition_number: int


@dataclass(frozen=True)
class CompletedTrial:
    """`answer_duration_seconds` is how long the session took to produce the answer, before any grading started;
    None only for a recorded trial whose run saved no duration."""

    trial_identity: TrialIdentity
    llm_session_transcript: LlmSessionTranscript
    answer_duration_seconds: float | None


@dataclass(frozen=True)
class ErroredTrial:
    """`answer_duration_seconds` is how long the session ran before it failed; None only for a recorded trial whose run saved no duration."""

    trial_identity: TrialIdentity
    error_description: str
    answer_duration_seconds: float | None


type TrialRecord = CompletedTrial | ErroredTrial


@dataclass(frozen=True)
class TrialAssignment:
    trial_identity: TrialIdentity
    llm_session_request: LlmSessionRequest
