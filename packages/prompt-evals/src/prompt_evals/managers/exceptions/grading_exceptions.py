"""Why a grader's structured response cannot be used. Each failure has its own type and one raise site.

The grader is a model we prompt and configure, so an unusable answer is ours to fix: the whole family is technical.
A rejected value is reported by its JSON-decoded Python type name ("NoneType" for null or an absent field), never by
its content.
"""

from abc import ABC
from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import ContextualDataDict, PromptEvalsTechnicalBaseException


class GraderResponseBaseException(PromptEvalsTechnicalBaseException, ABC):
    def __init__(self, processor_name: str, invalidity_description: str, invalidity_contextual_data_by_name: ContextualDataDict) -> None:
        super().__init__(
            f"{processor_name} received a grader response it could not use: {invalidity_description}",
            {"ProcessorName": processor_name, "InvalidityDescription": invalidity_description, **invalidity_contextual_data_by_name},
        )


@final
class GraderResponseMissingException(GraderResponseBaseException):
    def __init__(self, processor_name: str) -> None:
        super().__init__(processor_name, "the session returned no structured output", {})


@final
class GraderResponseNotJsonException(GraderResponseBaseException):
    def __init__(self, processor_name: str, json_error: str) -> None:
        super().__init__(processor_name, f"the structured output is not JSON: {json_error}", {})


@final
class GraderResponseNotJsonObjectException(GraderResponseBaseException):
    def __init__(self, processor_name: str, received_type_name: str) -> None:
        super().__init__(
            processor_name, f"the structured output is not a JSON object, it is {received_type_name}", {"ReceivedType": received_type_name}
        )


@final
class GraderResponseFactNotScalarException(GraderResponseBaseException):
    def __init__(self, processor_name: str, fact_name: str, received_type_name: str) -> None:
        super().__init__(
            processor_name,
            f"fact '{fact_name}' has a non-scalar value of type {received_type_name}",
            {"FactName": fact_name, "ReceivedType": received_type_name},
        )


@final
class GraderResponseVerdictFieldsInvalidException(GraderResponseBaseException):
    def __init__(self, processor_name: str, passed_type_name: str, reason_type_name: str) -> None:
        super().__init__(
            processor_name,
            f"the verdict needs a boolean 'passed' and a string 'reason', but 'passed' is {passed_type_name} and 'reason' is {reason_type_name}",
            {"PassedType": passed_type_name, "ReasonType": reason_type_name},
        )


@final
class GraderResponseDisputedAmountsNotListException(GraderResponseBaseException):
    def __init__(self, processor_name: str, received_type_name: str) -> None:
        super().__init__(
            processor_name, f"the verdict needs a list 'disputed_amounts', but it is {received_type_name}", {"ReceivedType": received_type_name}
        )


@final
class GraderResponseDisputedAmountNotObjectException(GraderResponseBaseException):
    def __init__(self, processor_name: str, received_type_name: str) -> None:
        super().__init__(
            processor_name, f"each disputed amount must be an object, but one is {received_type_name}", {"ReceivedType": received_type_name}
        )


@final
class GraderResponseDisputedAmountFieldsInvalidException(GraderResponseBaseException):
    def __init__(self, processor_name: str, description_type_name: str, answer_amount_type_name: str, reference_amount_type_name: str) -> None:
        super().__init__(
            processor_name,
            "each disputed amount needs string 'description', 'answer_amount' and 'reference_amount', but 'description' is "
            f"{description_type_name}, 'answer_amount' is {answer_amount_type_name} and 'reference_amount' is {reference_amount_type_name}",
            {
                "DescriptionType": description_type_name,
                "AnswerAmountType": answer_amount_type_name,
                "ReferenceAmountType": reference_amount_type_name,
            },
        )
