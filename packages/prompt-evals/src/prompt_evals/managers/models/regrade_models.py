from dataclasses import dataclass
from pathlib import Path

from prompt_evals.managers.models.evaluation_models import CodingAssistant, EffortLevel
from prompt_evals.managers.models.trial_models import TrialIdentity


@dataclass(frozen=True)
class RecordedCompletedTrial:
    """A finished trial as an earlier run saved it: the assistant's raw event stream, from which its answer and tool calls are read again.

    `answer_duration_seconds` is the answer time the run saved, or None when it saved none; the duration the event stream
    itself reports, if any, is used instead.
    """

    trial_identity: TrialIdentity
    event_stream_text: str
    answer_duration_seconds: float | None


@dataclass(frozen=True)
class RecordedErroredTrial:
    """`answer_duration_seconds` is the time the run saved for the failed session, or None when it saved none."""

    trial_identity: TrialIdentity
    error_description: str
    answer_duration_seconds: float | None


type RecordedTrial = RecordedCompletedTrial | RecordedErroredTrial


@dataclass(frozen=True)
class RegradeRequest:
    """Grade an earlier run's trials again with the eval suite's current graders and reference key; no trial runs again.

    `coding_assistant`, `model_name` and `effort_level` describe how the recorded trials ran: the assistant decides how
    their event streams are read, and all three appear on the new scorecard.
    """

    eval_suite_directory: Path
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    recorded_trials: tuple[RecordedTrial, ...]
