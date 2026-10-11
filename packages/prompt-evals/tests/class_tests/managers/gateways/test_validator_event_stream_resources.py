from collections.abc import Mapping
from typing import Final

import pytest
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.random_data_generator import RandomDataGenerator

from prompt_evals import (
    LlmSessionEventCountUnexpectedException,
    LlmSessionEventFieldMissingException,
    LlmSessionEventFieldTypeInvalidException,
    LlmSessionEventLineNotJsonException,
    LlmSessionEventLineNotJsonObjectException,
    LlmSessionOutputMalformedBaseException,
)
from prompt_evals.managers.gateways.claude_cli_resources.validator_claude_event_stream_resource import ValidatorClaudeEventStreamResource
from prompt_evals.managers.gateways.codex_cli_resources.validator_codex_event_stream_resource import ValidatorCodexEventStreamResource

CLAUDE_CODE_ASSISTANT_NAME: Final[str] = "Claude Code"
CODEX_ASSISTANT_NAME: Final[str] = "Codex"
UNREADABLE_OUTPUT_PHRASE: Final[str] = "produced output that could not be read"
EVENT_LINE_EXCERPT_CONTEXT_NAME: Final[str] = "EventLineExcerpt"


@pytest.mark.class_test
class TestValidatorEventStreamResources:
    @pytest.mark.parametrize(
        ("event_stream_text", "expected_exception_type", "expected_malformation_description", "expected_malformation_contextual_entries_by_name"),
        [
            (
                "this is not json\n",
                LlmSessionEventLineNotJsonException,
                "a line is not JSON: this is not json",
                {EVENT_LINE_EXCERPT_CONTEXT_NAME: "this is not json"},
            ),
            ("[1]\n", LlmSessionEventLineNotJsonObjectException, "a line is not a JSON object: [1]", {EVENT_LINE_EXCERPT_CONTEXT_NAME: "[1]"}),
            (
                "",
                LlmSessionEventCountUnexpectedException,
                "expected exactly one system init event, found 0",
                {"EventDescription": "system init", "EventCount": 0},
            ),
            ('{"type": "system", "subtype": "init"}\n', LlmSessionEventFieldMissingException, "the field 'model' is missing", {"FieldName": "model"}),
            (
                '{"type": "system", "subtype": "init", "model": 5}\n',
                LlmSessionEventFieldTypeInvalidException,
                "the field 'model' is int, not a string: 5",
                {"FieldDescription": "the field 'model'", "ExpectedType": "a string", "FieldValueExcerpt": "5"},
            ),
            (
                (
                    '{"type": "system", "subtype": "init", "model": "m"}\n'
                    '{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": [1]}]}}\n'
                ),
                LlmSessionEventFieldTypeInvalidException,
                "the input of a tool_use content block is list, not a JSON object: [1]",
                {"FieldDescription": "the input of a tool_use content block", "ExpectedType": "a JSON object", "FieldValueExcerpt": "[1]"},
            ),
        ],
        ids=["line-not-json", "line-not-object", "no-init-event", "field-missing", "field-wrong-type", "tool-input-not-object"],
    )
    def test_ParseEventStream_WhenTheClaudeStreamIsMalformed_ThenTheExceptionForThatFailureNamesClaudeCode(
        self,
        event_stream_text: str,
        expected_exception_type: type[LlmSessionOutputMalformedBaseException],
        expected_malformation_description: str,
        expected_malformation_contextual_entries_by_name: Mapping[str, object],
    ) -> None:
        # Arrange
        requested_model_name: str = f"model-{RandomDataGenerator.create_random_word()}"
        expected_message_phrases: tuple[str, ...] = (
            f"The {CLAUDE_CODE_ASSISTANT_NAME} session",
            UNREADABLE_OUTPUT_PHRASE,
            expected_malformation_description,
        )
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CLAUDE_CODE_ASSISTANT_NAME,
            "ModelName": requested_model_name,
            "MalformationDescription": expected_malformation_description,
            **expected_malformation_contextual_entries_by_name,
        }

        # Act
        with pytest.raises(LlmSessionOutputMalformedBaseException) as exception_info:
            ValidatorClaudeEventStreamResource.parse_event_stream(event_stream_text, requested_model_name)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=expected_exception_type,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )

    @pytest.mark.parametrize(
        ("event_stream_text", "expected_exception_type", "expected_malformation_description", "expected_malformation_contextual_entries_by_name"),
        [
            (
                "this is not json\n",
                LlmSessionEventLineNotJsonException,
                "a line is not JSON: this is not json",
                {EVENT_LINE_EXCERPT_CONTEXT_NAME: "this is not json"},
            ),
            ("[1]\n", LlmSessionEventLineNotJsonObjectException, "a line is not a JSON object: [1]", {EVENT_LINE_EXCERPT_CONTEXT_NAME: "[1]"}),
            (
                "",
                LlmSessionEventCountUnexpectedException,
                "expected exactly one turn.completed event, found 0",
                {"EventDescription": "turn.completed", "EventCount": 0},
            ),
            ('{"type": "item.started", "item": {}}\n', LlmSessionEventFieldMissingException, "the field 'id' is missing", {"FieldName": "id"}),
            (
                '{"type": "item.started", "item": 5}\n',
                LlmSessionEventFieldTypeInvalidException,
                "the field 'item' of a item.started event is int, not a JSON object: 5",
                {"FieldDescription": "the field 'item' of a item.started event", "ExpectedType": "a JSON object", "FieldValueExcerpt": "5"},
            ),
        ],
        ids=["line-not-json", "line-not-object", "no-turn-completed-event", "field-missing", "field-wrong-type"],
    )
    def test_ParseEventStream_WhenTheCodexStreamIsMalformed_ThenTheExceptionForThatFailureNamesCodex(
        self,
        event_stream_text: str,
        expected_exception_type: type[LlmSessionOutputMalformedBaseException],
        expected_malformation_description: str,
        expected_malformation_contextual_entries_by_name: Mapping[str, object],
    ) -> None:
        # Arrange
        requested_model_name: str = f"model-{RandomDataGenerator.create_random_word()}"
        expected_message_phrases: tuple[str, ...] = (
            f"The {CODEX_ASSISTANT_NAME} session",
            UNREADABLE_OUTPUT_PHRASE,
            expected_malformation_description,
        )
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CODEX_ASSISTANT_NAME,
            "ModelName": requested_model_name,
            "MalformationDescription": expected_malformation_description,
            **expected_malformation_contextual_entries_by_name,
        }

        # Act
        with pytest.raises(LlmSessionOutputMalformedBaseException) as exception_info:
            ValidatorCodexEventStreamResource.parse_event_stream(event_stream_text, requested_model_name)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=expected_exception_type,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )
