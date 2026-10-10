from dataclasses import dataclass

from prompt_evals import CodingAssistant, EffortLevel


@dataclass(frozen=True)
class PromptEvalOptions:
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    repetitions: int
