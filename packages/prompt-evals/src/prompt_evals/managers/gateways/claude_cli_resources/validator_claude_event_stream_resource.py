import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Final, NoReturn, cast, final

from prompt_evals.managers.exceptions.llm_session_exceptions import (
    LlmSessionEventCountUnexpectedException,
    LlmSessionEventFieldMissingException,
    LlmSessionEventFieldTypeInvalidException,
    LlmSessionEventLineNotJsonException,
    LlmSessionEventLineNotJsonObjectException,
)
from prompt_evals.managers.gateways.claude_cli_resources.claude_event_stream_resources import (
    ClaudeEventStreamResource,
    ClaudeResultResource,
    ClaudeToolResultResource,
    ClaudeToolUseResource,
)

type JsonObject = dict[str, object]

CLAUDE_CODE_ASSISTANT_NAME: Final[str] = "Claude Code"
EVENT_TYPE_FIELD: Final[str] = "type"
EVENT_TYPE_SYSTEM: Final[str] = "system"
EVENT_TYPE_ASSISTANT: Final[str] = "assistant"
EVENT_TYPE_USER: Final[str] = "user"
EVENT_TYPE_RESULT: Final[str] = "result"
SYSTEM_SUBTYPE_INIT: Final[str] = "init"
CONTENT_BLOCK_TOOL_USE: Final[str] = "tool_use"
CONTENT_BLOCK_TOOL_RESULT: Final[str] = "tool_result"
CONTENT_BLOCK_TEXT: Final[str] = "text"


@final
class ValidatorClaudeEventStreamResource:
    """Turns the CLI's newline-delimited JSON (foreign data) into typed resources, or refuses it.

    Only the fields this system reads are validated; every other event type and field is ignored,
    because the CLI adds event types between versions.
    """

    @staticmethod
    def parse_event_stream(event_stream_text: str, requested_model_name: str) -> ClaudeEventStreamResource:
        events: list[JsonObject] = ValidatorClaudeEventStreamResource._parse_events(event_stream_text, requested_model_name)
        return ClaudeEventStreamResource(
            model_name=ValidatorClaudeEventStreamResource._read_session_model_name(events, requested_model_name),
            claude_tool_use_resources=ValidatorClaudeEventStreamResource._parse_all_tool_uses(events, requested_model_name),
            claude_tool_result_resources=ValidatorClaudeEventStreamResource._parse_all_tool_results(events, requested_model_name),
            claude_result_resource=ValidatorClaudeEventStreamResource._parse_single_result(events, requested_model_name),
        )

    @staticmethod
    def _parse_events(event_stream_text: str, requested_model_name: str) -> list[JsonObject]:
        # One JSON event per "\n"-terminated line; blank lines carry no event. splitlines() would also break on U+2028 and
        # similar characters, which JSON.stringify leaves unescaped inside strings, and cut an event in half.
        return [
            ValidatorClaudeEventStreamResource._parse_event_line(event_line, requested_model_name)
            for event_line in event_stream_text.split("\n")
            if event_line.strip()
        ]

    @staticmethod
    def _parse_all_tool_uses(events: Iterable[JsonObject], requested_model_name: str) -> tuple[ClaudeToolUseResource, ...]:
        return tuple(
            claude_tool_use_resource
            for event in ValidatorClaudeEventStreamResource._select_events(events, EVENT_TYPE_ASSISTANT)
            for claude_tool_use_resource in ValidatorClaudeEventStreamResource._parse_tool_uses(event, requested_model_name)
        )

    @staticmethod
    def _parse_all_tool_results(events: Iterable[JsonObject], requested_model_name: str) -> tuple[ClaudeToolResultResource, ...]:
        return tuple(
            claude_tool_result_resource
            for event in ValidatorClaudeEventStreamResource._select_events(events, EVENT_TYPE_USER)
            for claude_tool_result_resource in ValidatorClaudeEventStreamResource._parse_tool_results(event, requested_model_name)
        )

    @staticmethod
    def _parse_single_result(events: Iterable[JsonObject], requested_model_name: str) -> ClaudeResultResource:
        result_event: JsonObject = ValidatorClaudeEventStreamResource._select_single_event(
            ValidatorClaudeEventStreamResource._select_events(events, EVENT_TYPE_RESULT), "result", requested_model_name
        )
        return ValidatorClaudeEventStreamResource._parse_result(result_event, requested_model_name)

    @staticmethod
    def _read_session_model_name(events: Iterable[JsonObject], requested_model_name: str) -> str:
        init_events: list[JsonObject] = [
            event
            for event in ValidatorClaudeEventStreamResource._select_events(events, EVENT_TYPE_SYSTEM)
            if event.get("subtype") == SYSTEM_SUBTYPE_INIT
        ]
        init_event: JsonObject = ValidatorClaudeEventStreamResource._select_single_event(init_events, "system init", requested_model_name)
        return ValidatorClaudeEventStreamResource._read_string(init_event, "model", requested_model_name)

    @staticmethod
    def _select_events(events: Iterable[JsonObject], event_type: str) -> list[JsonObject]:
        return [event for event in events if event.get(EVENT_TYPE_FIELD) == event_type]

    @staticmethod
    def _select_single_event(matching_events: Sequence[JsonObject], event_description: str, requested_model_name: str) -> JsonObject:
        if len(matching_events) != 1:
            raise LlmSessionEventCountUnexpectedException(CLAUDE_CODE_ASSISTANT_NAME, requested_model_name, event_description, len(matching_events))
        return matching_events[0]

    @staticmethod
    def _parse_event_line(event_line: str, requested_model_name: str) -> JsonObject:
        try:
            parsed_event: object = json.loads(event_line)
        except json.JSONDecodeError as json_decode_error:
            raise LlmSessionEventLineNotJsonException(CLAUDE_CODE_ASSISTANT_NAME, requested_model_name, event_line) from json_decode_error
        if not isinstance(parsed_event, dict):
            raise LlmSessionEventLineNotJsonObjectException(CLAUDE_CODE_ASSISTANT_NAME, requested_model_name, event_line)
        return cast(JsonObject, parsed_event)

    @staticmethod
    def _parse_tool_uses(event: Mapping[str, object], requested_model_name: str) -> list[ClaudeToolUseResource]:
        return [
            ClaudeToolUseResource(
                tool_use_id=ValidatorClaudeEventStreamResource._read_string(content_block, "id", requested_model_name),
                tool_name=ValidatorClaudeEventStreamResource._read_string(content_block, "name", requested_model_name),
                tool_input_json=ValidatorClaudeEventStreamResource._read_tool_input_json(content_block, requested_model_name),
            )
            for content_block in ValidatorClaudeEventStreamResource._read_message_content_blocks(event, requested_model_name)
            if content_block.get(EVENT_TYPE_FIELD) == CONTENT_BLOCK_TOOL_USE
        ]

    @staticmethod
    def _read_tool_input_json(tool_use_content_block: Mapping[str, object], requested_model_name: str) -> str:
        # A tool's arguments are always named fields; anything else means the stream cannot say what the call ran or touched.
        tool_input: object = tool_use_content_block.get("input", {})
        if not isinstance(tool_input, dict):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(
                requested_model_name, "the input of a tool_use content block", "a JSON object", tool_input
            )
        return json.dumps(tool_input, ensure_ascii=False)

    @staticmethod
    def _parse_tool_results(event: Mapping[str, object], requested_model_name: str) -> list[ClaudeToolResultResource]:
        return [
            ClaudeToolResultResource(
                tool_use_id=ValidatorClaudeEventStreamResource._read_string(content_block, "tool_use_id", requested_model_name),
                result_text=ValidatorClaudeEventStreamResource._read_tool_result_text(content_block.get("content")),
                is_error=content_block.get("is_error") is True,
            )
            for content_block in ValidatorClaudeEventStreamResource._read_message_content_blocks(event, requested_model_name)
            if content_block.get(EVENT_TYPE_FIELD) == CONTENT_BLOCK_TOOL_RESULT
        ]

    @staticmethod
    def _parse_result(event: Mapping[str, object], requested_model_name: str) -> ClaudeResultResource:
        structured_output: object = event.get("structured_output")
        result_text: object = event.get("result", "")
        return ClaudeResultResource(
            subtype=ValidatorClaudeEventStreamResource._read_string(event, "subtype", requested_model_name),
            is_error=event.get("is_error") is True,
            result_text=result_text if isinstance(result_text, str) else "",
            structured_output_json=None if structured_output is None else json.dumps(structured_output, ensure_ascii=False),
            duration_milliseconds=ValidatorClaudeEventStreamResource._read_optional_whole_number(event, "duration_ms", requested_model_name),
            total_cost_usd=ValidatorClaudeEventStreamResource._read_optional_decimal(event, "total_cost_usd", requested_model_name),
            error_messages=ValidatorClaudeEventStreamResource._read_error_messages(event),
        )

    # The CLI omits cost and duration from some results. An absent value stays None, never zero: a zero duration would
    # count as a measured instant run in the timing summaries, and a zero cost as a free one.
    @staticmethod
    def _read_optional_decimal(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> Decimal | None:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            return None
        # bool is a subclass of int, so a JSON true would otherwise pass as the number 1.
        if not isinstance(field_value, int | float) or isinstance(field_value, bool):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(
                requested_model_name, f"the result event's {field_name}", "a number", field_value
            )
        return Decimal(str(field_value))

    @staticmethod
    def _read_optional_whole_number(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> int | None:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            return None
        if not isinstance(field_value, int) or isinstance(field_value, bool):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(
                requested_model_name, f"the result event's {field_name}", "a whole number", field_value
            )
        return field_value

    @staticmethod
    def _read_error_messages(result_event: Mapping[str, object]) -> tuple[str, ...]:
        # Error results carry their cause in an "errors" list instead of "result"; its items are text or objects.
        error_items: object = result_event.get("errors")
        if not isinstance(error_items, list):
            return ()
        return tuple(
            error_item if isinstance(error_item, str) else json.dumps(error_item, ensure_ascii=False)
            for error_item in cast(list[object], error_items)
        )

    @staticmethod
    def _read_message_content_blocks(event: Mapping[str, object], requested_model_name: str) -> list[JsonObject]:
        message: object = event.get("message")
        if not isinstance(message, dict):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(
                requested_model_name, f"the message of a {event.get(EVENT_TYPE_FIELD)} event", "a JSON object", message
            )
        content: object = cast(JsonObject, message).get("content")
        if isinstance(content, str):
            return []
        if not isinstance(content, list):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(
                requested_model_name, f"the content of a {event.get(EVENT_TYPE_FIELD)} message", "a list or a string", content
            )
        return [cast(JsonObject, content_block) for content_block in cast(list[object], content) if isinstance(content_block, dict)]

    @staticmethod
    def _read_tool_result_text(tool_result_content: object) -> str:
        if isinstance(tool_result_content, str):
            return tool_result_content
        if not isinstance(tool_result_content, list):
            return ""
        result_texts: list[str] = []
        for content_part in cast(list[object], tool_result_content):
            if isinstance(content_part, dict):
                content_part_object: JsonObject = cast(JsonObject, content_part)
                part_text: object = content_part_object.get(CONTENT_BLOCK_TEXT)
                if content_part_object.get(EVENT_TYPE_FIELD) == CONTENT_BLOCK_TEXT and isinstance(part_text, str):
                    result_texts.append(part_text)
        return "\n".join(result_texts)

    @staticmethod
    def _read_string(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> str:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            raise LlmSessionEventFieldMissingException(CLAUDE_CODE_ASSISTANT_NAME, requested_model_name, field_name)
        if not isinstance(field_value, str):
            ValidatorClaudeEventStreamResource._raise_field_type_invalid(requested_model_name, f"the field '{field_name}'", "a string", field_value)
        return field_value

    @staticmethod
    def _raise_field_type_invalid(requested_model_name: str, field_description: str, expected_type_description: str, field_value: object) -> NoReturn:
        raise LlmSessionEventFieldTypeInvalidException(
            CLAUDE_CODE_ASSISTANT_NAME, requested_model_name, field_description, expected_type_description, field_value
        )
