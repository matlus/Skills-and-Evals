"""Why an evaluation or regrade request cannot be served. Each validation has its own type and one raise site.

Each validation collects every problem it finds and reports them together. The request is supplied by the caller, so
the whole family is business.
"""

from abc import ABC
from collections.abc import Sequence
from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsBusinessBaseException


class RequestValidationBaseException(PromptEvalsBusinessBaseException, ABC):
    def __init__(self, problem_summary: str, validation_problems: Sequence[str]) -> None:
        super().__init__(
            f"{problem_summary}: " + "; ".join(validation_problems),
            {"ValidationProblemCount": len(validation_problems)},
        )
        self._validation_problems: tuple[str, ...] = tuple(validation_problems)

    @property
    def validation_problems(self) -> tuple[str, ...]:
        return self._validation_problems


@final
class EvaluationRequestValidationException(RequestValidationBaseException):
    def __init__(self, validation_problems: Sequence[str]) -> None:
        super().__init__("The evaluation request is invalid", validation_problems)


@final
class EvaluationRequestVariantsNotInEvalSuiteException(RequestValidationBaseException):
    def __init__(self, validation_problems: Sequence[str]) -> None:
        super().__init__("The evaluation request names variants the eval suite does not define", validation_problems)


@final
class RegradeRequestValidationException(RequestValidationBaseException):
    def __init__(self, validation_problems: Sequence[str]) -> None:
        super().__init__("The regrade request is invalid", validation_problems)


@final
class RegradeRequestTrialsNotInEvalSuiteException(RequestValidationBaseException):
    def __init__(self, validation_problems: Sequence[str]) -> None:
        super().__init__("The regrade request holds recorded trials the eval suite does not define", validation_problems)
