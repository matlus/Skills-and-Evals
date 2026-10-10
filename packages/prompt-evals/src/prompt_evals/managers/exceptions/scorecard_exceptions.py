from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsBusinessExceptionBase


@final
class ScorecardValidationException(PromptEvalsBusinessExceptionBase):
    def __init__(self, validation_problems: list[str]) -> None:
        super().__init__(
            "The scorecard cannot be rendered: " + "; ".join(validation_problems),
            {"ValidationProblemCount": len(validation_problems)},
        )
        self._validation_problems: tuple[str, ...] = tuple(validation_problems)

    @property
    def validation_problems(self) -> tuple[str, ...]:
        return self._validation_problems
