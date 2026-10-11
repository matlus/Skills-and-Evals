import json
from typing import cast, final

from prompt_evals.managers.exceptions.grading_exceptions import (
    GraderResponseDisputedAmountFieldsInvalidException,
    GraderResponseDisputedAmountNotObjectException,
    GraderResponseDisputedAmountsNotListException,
    GraderResponseFactNotScalarException,
    GraderResponseMissingException,
    GraderResponseNotJsonException,
    GraderResponseNotJsonObjectException,
    GraderResponseVerdictFieldsInvalidException,
)
from prompt_evals.managers.models.diagnosis_models import DisputedAmount
from prompt_evals.managers.models.grading_models import ExtractedFact, ExtractedFacts, JudgeVerdict

type JsonObject = dict[str, object]


@final
class ValidatorGraderResponseResource:
    """Grader models answer with structured output (JSON the CLI validated against our schema).
    It is still foreign data, so it is checked again before it becomes a domain model."""

    @staticmethod
    def parse_extracted_facts(structured_output_json: str | None, processor_name: str) -> ExtractedFacts:
        structured_output: JsonObject = ValidatorGraderResponseResource._parse_json_object(structured_output_json, processor_name)
        extracted_facts: list[ExtractedFact] = []
        fact_name: str
        fact_value: object
        for fact_name, fact_value in structured_output.items():
            extracted_facts.append(
                ExtractedFact(
                    fact_name=fact_name, reported_value=ValidatorGraderResponseResource._normalize_fact_value(fact_name, fact_value, processor_name)
                )
            )
        return ExtractedFacts(extracted_facts=tuple(extracted_facts))

    @staticmethod
    def parse_judge_verdict(structured_output_json: str | None, processor_name: str) -> JudgeVerdict:
        structured_output: JsonObject = ValidatorGraderResponseResource._parse_json_object(structured_output_json, processor_name)
        is_passed: object = structured_output.get("passed")
        reason: object = structured_output.get("reason")
        if not isinstance(is_passed, bool) or not isinstance(reason, str):
            raise GraderResponseVerdictFieldsInvalidException(processor_name, type(is_passed).__name__, type(reason).__name__)
        return JudgeVerdict(
            is_passed=is_passed,
            reason=reason,
            disputed_amounts=ValidatorGraderResponseResource._parse_disputed_amounts(structured_output.get("disputed_amounts"), processor_name),
        )

    @staticmethod
    def _parse_disputed_amounts(disputed_amounts_value: object, processor_name: str) -> tuple[DisputedAmount, ...]:
        if not isinstance(disputed_amounts_value, list):
            raise GraderResponseDisputedAmountsNotListException(processor_name, type(disputed_amounts_value).__name__)
        return tuple(
            ValidatorGraderResponseResource._parse_disputed_amount(disputed_amount_value, processor_name)
            for disputed_amount_value in cast(list[object], disputed_amounts_value)
        )

    @staticmethod
    def _parse_disputed_amount(disputed_amount_value: object, processor_name: str) -> DisputedAmount:
        if not isinstance(disputed_amount_value, dict):
            raise GraderResponseDisputedAmountNotObjectException(processor_name, type(disputed_amount_value).__name__)
        disputed_amount_object: JsonObject = cast(JsonObject, disputed_amount_value)
        description: object = disputed_amount_object.get("description")
        answer_amount: object = disputed_amount_object.get("answer_amount")
        reference_amount: object = disputed_amount_object.get("reference_amount")
        if not isinstance(description, str) or not isinstance(answer_amount, str) or not isinstance(reference_amount, str):
            raise GraderResponseDisputedAmountFieldsInvalidException(
                processor_name, type(description).__name__, type(answer_amount).__name__, type(reference_amount).__name__
            )
        return DisputedAmount(description=description, answer_amount_text=answer_amount, reference_amount_text=reference_amount)

    @staticmethod
    def _normalize_fact_value(fact_name: str, fact_value: object, processor_name: str) -> str | None:
        match fact_value:
            case None:
                return None
            case bool():
                return "true" if fact_value else "false"
            case str() | int() | float():
                return str(fact_value)
            case _:
                raise GraderResponseFactNotScalarException(processor_name, fact_name, type(fact_value).__name__)

    @staticmethod
    def _parse_json_object(structured_output_json: str | None, processor_name: str) -> JsonObject:
        if structured_output_json is None:
            raise GraderResponseMissingException(processor_name)
        try:
            structured_output: object = json.loads(structured_output_json)
        except json.JSONDecodeError as json_decode_error:
            raise GraderResponseNotJsonException(processor_name, str(json_decode_error)) from json_decode_error
        if not isinstance(structured_output, dict):
            raise GraderResponseNotJsonObjectException(processor_name, type(structured_output).__name__)
        return cast(JsonObject, structured_output)
