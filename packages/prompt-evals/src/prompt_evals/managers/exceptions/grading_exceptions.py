from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalBaseException


@final
class GraderResponseInvalidException(PromptEvalsTechnicalBaseException):
    def __init__(self, processor_name: str, invalidity_description: str) -> None:
        super().__init__(
            f"{processor_name} received a grader response it could not use: {invalidity_description}",
            {"ProcessorName": processor_name, "InvalidityDescription": invalidity_description},
        )
