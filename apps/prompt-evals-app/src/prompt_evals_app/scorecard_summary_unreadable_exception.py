from typing import final

from prompt_evals import PromptEvalsBusinessBaseException


@final
class ScorecardSummaryUnreadableException(PromptEvalsBusinessBaseException):
    """A run folder's scorecard.json is not one this app wrote, so it cannot be compared."""

    def __init__(self, message: str) -> None:
        super().__init__(message, {})
