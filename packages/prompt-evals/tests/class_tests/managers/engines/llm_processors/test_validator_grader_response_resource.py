from collections.abc import Mapping
from typing import Final

import pytest
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.random_data_generator import RandomDataGenerator

from prompt_evals import (
    GraderResponseBaseException,
    GraderResponseDisputedAmountFieldsInvalidException,
    GraderResponseDisputedAmountNotObjectException,
    GraderResponseDisputedAmountsNotListException,
    GraderResponseFactNotScalarException,
    GraderResponseMissingException,
    GraderResponseNotJsonException,
    GraderResponseNotJsonObjectException,
    GraderResponseVerdictFieldsInvalidException,
)
from prompt_evals.managers.engines.llm_processors.grader_response_resources.validator_grader_response_resource import (
    ValidatorGraderResponseResource,
)

UNUSABLE_RESPONSE_PHRASE: Final[str] = "received a grader response it could not use"
# The message phrases already pin the description's text; the entry itself must also be captured.
INVALIDITY_DESCRIPTION_CONTEXT_NAME: Final[str] = "InvalidityDescription"


@pytest.mark.class_test
class TestValidatorGraderResponseResource:
    @pytest.mark.parametrize(
        ("structured_output_json", "expected_exception_type", "expected_invalidity_phrase", "expected_invalidity_contextual_entries_by_name"),
        [
            (None, GraderResponseMissingException, "the session returned no structured output", {}),
            ("{", GraderResponseNotJsonException, "the structured output is not JSON", {}),
            ("[1, 2]", GraderResponseNotJsonObjectException, "the structured output is not a JSON object, it is list", {"ReceivedType": "list"}),
            (
                '{"total": {"amount": 1}}',
                GraderResponseFactNotScalarException,
                "fact 'total' has a non-scalar value of type dict",
                {"FactName": "total", "ReceivedType": "dict"},
            ),
        ],
        ids=["no-structured-output", "not-json", "not-json-object", "fact-not-scalar"],
    )
    def test_ParseExtractedFacts_WhenTheGraderResponseIsUnusable_ThenTheExceptionForThatFailureNamesTheProcessorAndWhatWasReceived(
        self,
        structured_output_json: str | None,
        expected_exception_type: type[GraderResponseBaseException],
        expected_invalidity_phrase: str,
        expected_invalidity_contextual_entries_by_name: Mapping[str, object],
    ) -> None:
        # Arrange
        processor_name: str = f"processor-{RandomDataGenerator.create_random_word()}"
        expected_message_phrases: tuple[str, ...] = (processor_name, UNUSABLE_RESPONSE_PHRASE, expected_invalidity_phrase)
        expected_contextual_entries_by_name: dict[str, object] = {"ProcessorName": processor_name, **expected_invalidity_contextual_entries_by_name}

        # Act
        with pytest.raises(GraderResponseBaseException) as exception_info:
            ValidatorGraderResponseResource.parse_extracted_facts(structured_output_json, processor_name)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=expected_exception_type,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            expected_contextual_entry_names=(INVALIDITY_DESCRIPTION_CONTEXT_NAME,),
        )

    @pytest.mark.parametrize(
        ("structured_output_json", "expected_exception_type", "expected_invalidity_phrase", "expected_invalidity_contextual_entries_by_name"),
        [
            ("[]", GraderResponseNotJsonObjectException, "the structured output is not a JSON object, it is list", {"ReceivedType": "list"}),
            (
                '{"passed": "yes", "reason": "looks right"}',
                GraderResponseVerdictFieldsInvalidException,
                "the verdict needs a boolean 'passed' and a string 'reason', but 'passed' is str and 'reason' is str",
                {"PassedType": "str", "ReasonType": "str"},
            ),
            (
                '{"passed": true, "reason": "looks right"}',
                GraderResponseDisputedAmountsNotListException,
                "the verdict needs a list 'disputed_amounts', but it is NoneType",
                {"ReceivedType": "NoneType"},
            ),
            (
                '{"passed": true, "reason": "looks right", "disputed_amounts": {}}',
                GraderResponseDisputedAmountsNotListException,
                "the verdict needs a list 'disputed_amounts', but it is dict",
                {"ReceivedType": "dict"},
            ),
            (
                '{"passed": false, "reason": "totals differ", "disputed_amounts": ["total"]}',
                GraderResponseDisputedAmountNotObjectException,
                "each disputed amount must be an object, but one is str",
                {"ReceivedType": "str"},
            ),
            (
                '{"passed": false, "reason": "totals differ", "disputed_amounts": [{"description": "total", "answer_amount": 12.5}]}',
                GraderResponseDisputedAmountFieldsInvalidException,
                "'description' is str, 'answer_amount' is float and 'reference_amount' is NoneType",
                {"DescriptionType": "str", "AnswerAmountType": "float", "ReferenceAmountType": "NoneType"},
            ),
        ],
        ids=[
            "not-json-object",
            "verdict-fields-invalid",
            "disputed-amounts-absent",
            "disputed-amounts-not-list",
            "disputed-amount-not-object",
            "disputed-amount-fields-invalid",
        ],
    )
    def test_ParseJudgeVerdict_WhenTheGraderResponseIsUnusable_ThenTheExceptionForThatFailureNamesTheProcessorAndWhatWasReceived(
        self,
        structured_output_json: str,
        expected_exception_type: type[GraderResponseBaseException],
        expected_invalidity_phrase: str,
        expected_invalidity_contextual_entries_by_name: Mapping[str, object],
    ) -> None:
        # Arrange
        processor_name: str = f"processor-{RandomDataGenerator.create_random_word()}"
        expected_message_phrases: tuple[str, ...] = (processor_name, UNUSABLE_RESPONSE_PHRASE, expected_invalidity_phrase)
        expected_contextual_entries_by_name: dict[str, object] = {"ProcessorName": processor_name, **expected_invalidity_contextual_entries_by_name}

        # Act
        with pytest.raises(GraderResponseBaseException) as exception_info:
            ValidatorGraderResponseResource.parse_judge_verdict(structured_output_json, processor_name)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=expected_exception_type,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            expected_contextual_entry_names=(INVALIDITY_DESCRIPTION_CONTEXT_NAME,),
        )
