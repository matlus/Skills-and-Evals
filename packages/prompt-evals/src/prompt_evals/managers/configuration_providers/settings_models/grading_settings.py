from dataclasses import dataclass

from prompt_evals.managers.models.evaluation_models import CodingAssistant, EffortLevel


@dataclass(frozen=True)
class GradingSettings:
    """Graders run in their own assistant, independent of the one under test, so grading stays constant across assistants."""

    grader_coding_assistant: CodingAssistant
    grader_model_name: str
    grader_effort_level: EffortLevel
    maximum_concurrent_gradings: int
