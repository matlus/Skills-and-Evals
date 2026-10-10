from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CodingAssistant(StrEnum):
    """The coding-assistant CLI a session runs in. Each member has its own gateway."""

    CLAUDE_CODE = "claude_code"
    CODEX = "codex"


class EffortLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class TrialRunDescription:
    """What the graded trials ran with, as the scorecard reports it."""

    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    repetitions: int


@dataclass(frozen=True)
class EvaluationRequest:
    """One evaluation run: every selected prompt variant x every case x `repetitions` isolated trials,
    each in `coding_assistant` with `model_name`.

    An empty `variant_names` selects every variant the eval suite defines.
    """

    eval_suite_directory: Path
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    repetitions: int
    variant_names: tuple[str, ...] = ()
