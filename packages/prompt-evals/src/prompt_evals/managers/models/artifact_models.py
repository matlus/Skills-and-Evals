from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from prompt_evals.managers.models.trial_models import TrialIdentity


class EvaluationArtifactType(StrEnum):
    TRIAL_EVENT_STREAM = "trial_event_stream"
    TRIAL_ANSWER = "trial_answer"
    TRIAL_ERROR = "trial_error"
    TRIAL_GRADE = "trial_grade"
    SCORECARD = "scorecard"
    SCORECARD_REPORT = "scorecard_report"

    @property
    def file_stem(self) -> str:
        match self:
            case EvaluationArtifactType.TRIAL_EVENT_STREAM:
                return "event_stream"
            case EvaluationArtifactType.TRIAL_ANSWER:
                return "answer"
            case EvaluationArtifactType.TRIAL_ERROR:
                return "error"
            case EvaluationArtifactType.TRIAL_GRADE:
                return "grade"
            case EvaluationArtifactType.SCORECARD | EvaluationArtifactType.SCORECARD_REPORT:
                return "scorecard"

    @property
    def file_extension(self) -> str:
        match self:
            case EvaluationArtifactType.TRIAL_EVENT_STREAM:
                return "jsonl"
            case EvaluationArtifactType.TRIAL_ANSWER | EvaluationArtifactType.SCORECARD_REPORT:
                return "md"
            case EvaluationArtifactType.TRIAL_ERROR:
                return "txt"
            case EvaluationArtifactType.TRIAL_GRADE | EvaluationArtifactType.SCORECARD:
                return "json"

    @property
    def content_type(self) -> str:
        match self:
            case EvaluationArtifactType.TRIAL_EVENT_STREAM:
                return "application/x-ndjson"
            case EvaluationArtifactType.TRIAL_ANSWER | EvaluationArtifactType.SCORECARD_REPORT:
                return "text/markdown"
            case EvaluationArtifactType.TRIAL_ERROR:
                return "text/plain"
            case EvaluationArtifactType.TRIAL_GRADE | EvaluationArtifactType.SCORECARD:
                return "application/json"


@dataclass(frozen=True)
class EvaluationArtifact:
    """Everything a host needs to persist one artifact blindly. The evaluation never knows where artifacts are stored:
    the host decides the location from `trial_identity` and `filename_suffix`, whose extension states the format.

    `trial_identity` is the trial the artifact came from, or None for an artifact that covers the whole evaluation
    run, such as the scorecard.
    """

    artifact_type: EvaluationArtifactType
    trial_identity: TrialIdentity | None
    content: bytes
    filename_suffix: str
    content_type: str


type EvaluationArtifactCallback = Callable[[EvaluationArtifact], None]
