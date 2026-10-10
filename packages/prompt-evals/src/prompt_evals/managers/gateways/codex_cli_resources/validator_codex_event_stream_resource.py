import json
from collections.abc import Iterable, Mapping
from typing import Final, NoReturn, cast, final

from prompt_evals.managers.exceptions.llm_session_exceptions import LlmSessionOutputMalformedException
from prompt_evals.managers.gateways.codex_cli_resources.codex_event_stream_resources import (
    CodexAgentMessageResource,
    CodexCommandExecutionResource,
    CodexEventStreamResource,
    CodexFileChangeResource,
    CodexFileUpdateResource,
    CodexToolItemResource,
    CodexTurnFailureResource,
)

type JsonObject = dict[str, object]

CODEX_ASSISTANT_NAME: Final[str] = "Codex"
EVENT_TYPE_FIELD: Final[str] = "type"
EVENT_TYPE_TURN_COMPLETED: Final[str] = "turn.completed"
EVENT_TYPE_TURN_FAILED: Final[str] = "turn.failed"
EVENT_TYPE_ERROR: Final[str] = "error"
# An item is reported when it starts, possibly while it changes, and when it completes; the latest report is its state.
ITEM_EVENT_TYPES: Final[frozenset[str]] = frozenset({"item.started", "item.updated", "item.completed"})
FAILURE_EVENT_TYPES: Final[frozenset[str]] = frozenset({EVENT_TYPE_ERROR, EVENT_TYPE_TURN_FAILED})
ITEM_TYPE_AGENT_MESSAGE: Final[str] = "agent_message"
ITEM_TYPE_COMMAND_EXECUTION: Final[str] = "command_execution"
ITEM_TYPE_FILE_CHANGE: Final[str] = "file_change"
TOOL_ITEM_TYPES: Final[frozenset[str]] = frozenset({ITEM_TYPE_COMMAND_EXECUTION, ITEM_TYPE_FILE_CHANGE})


@final
class ValidatorCodexEventStreamResource:
    """Turns the CLI's newline-delimited JSON (foreign data) into typed resources, or refuses it.

    Only the fields this system reads are validated; every other event type, item type and field is ignored,
    because the CLI adds them between versions. An "error" item is a warning (for example unknown model metadata), not a failure.
    """

    @staticmethod
    def parse_event_stream(event_stream_text: str, requested_model_name: str) -> CodexEventStreamResource:
        events: list[JsonObject] = ValidatorCodexEventStreamResource._parse_events(event_stream_text, requested_model_name)
        latest_items: list[JsonObject] = ValidatorCodexEventStreamResource._collect_latest_items(events, requested_model_name)
        codex_turn_failure_resource: CodexTurnFailureResource | None = ValidatorCodexEventStreamResource._parse_turn_failure(
            events, requested_model_name
        )
        if codex_turn_failure_resource is None:
            ValidatorCodexEventStreamResource._require_single_turn_completed(events, requested_model_name)
        return CodexEventStreamResource(
            codex_agent_message_resources=ValidatorCodexEventStreamResource._parse_agent_messages(latest_items, requested_model_name),
            codex_tool_item_resources=ValidatorCodexEventStreamResource._parse_tool_items(latest_items, requested_model_name),
            codex_turn_failure_resource=codex_turn_failure_resource,
        )

    @staticmethod
    def _parse_events(event_stream_text: str, requested_model_name: str) -> list[JsonObject]:
        # One JSON event per "\n"-terminated line; blank lines carry no event. splitlines() would also break on U+2028 and
        # similar characters, which can appear unescaped inside JSON strings, and cut an event in half.
        return [
            ValidatorCodexEventStreamResource._parse_event_line(event_line, requested_model_name)
            for event_line in event_stream_text.split("\n")
            if event_line.strip()
        ]

    @staticmethod
    def _parse_event_line(event_line: str, requested_model_name: str) -> JsonObject:
        try:
            parsed_event: object = json.loads(event_line)
        except json.JSONDecodeError as json_decode_error:
            raise LlmSessionOutputMalformedException(
                CODEX_ASSISTANT_NAME, requested_model_name, f"a line is not JSON: {event_line[:200]}"
            ) from json_decode_error
        if not isinstance(parsed_event, dict):
            ValidatorCodexEventStreamResource._raise_malformed(requested_model_name, f"a line is not a JSON object: {event_line[:200]}")
        return cast(JsonObject, parsed_event)

    @staticmethod
    def _collect_latest_items(events: Iterable[JsonObject], requested_model_name: str) -> list[JsonObject]:
        # A dict keeps the position of a key's first insertion, so items stay in the order they started.
        latest_item_by_item_id: dict[str, JsonObject] = {}
        for event in events:
            if event.get(EVENT_TYPE_FIELD) in ITEM_EVENT_TYPES:
                item: JsonObject = ValidatorCodexEventStreamResource._read_object(event, "item", requested_model_name)
                latest_item_by_item_id[ValidatorCodexEventStreamResource._read_string(item, "id", requested_model_name)] = item
        return list(latest_item_by_item_id.values())

    @staticmethod
    def _parse_turn_failure(events: Iterable[JsonObject], requested_model_name: str) -> CodexTurnFailureResource | None:
        failure_events: list[JsonObject] = [event for event in events if event.get(EVENT_TYPE_FIELD) in FAILURE_EVENT_TYPES]
        if not failure_events:
            return None
        has_turn_failed_event: bool = any(failure_event.get(EVENT_TYPE_FIELD) == EVENT_TYPE_TURN_FAILED for failure_event in failure_events)
        # The CLI reports one failure as an "error" event and again in "turn.failed", so repeated messages are kept once.
        provider_messages: tuple[str, ...] = tuple(
            dict.fromkeys(
                ValidatorCodexEventStreamResource._read_provider_message(
                    ValidatorCodexEventStreamResource._read_failure_text(failure_event, requested_model_name)
                )
                for failure_event in failure_events
            )
        )
        return CodexTurnFailureResource(
            failure_kind=EVENT_TYPE_TURN_FAILED if has_turn_failed_event else EVENT_TYPE_ERROR,
            provider_messages=provider_messages,
        )

    @staticmethod
    def _read_failure_text(failure_event: Mapping[str, object], requested_model_name: str) -> str:
        if failure_event.get(EVENT_TYPE_FIELD) == EVENT_TYPE_TURN_FAILED:
            turn_error: JsonObject = ValidatorCodexEventStreamResource._read_object(failure_event, "error", requested_model_name)
            return ValidatorCodexEventStreamResource._read_string(turn_error, "message", requested_model_name)
        return ValidatorCodexEventStreamResource._read_string(failure_event, "message", requested_model_name)

    @staticmethod
    def _read_provider_message(failure_text: str) -> str:
        # A failed model request arrives as JSON text such as {"status": 400, "error": {"message": "..."}}; its message is the cause.
        try:
            parsed_failure: object = json.loads(failure_text)
        except json.JSONDecodeError:
            return failure_text
        match parsed_failure:
            case {"error": {"message": str() as provider_message}, "status": int() as provider_status}:
                return f"{provider_message} (status {provider_status})"
            case {"error": {"message": str() as provider_message}}:
                return provider_message
            case _:
                return failure_text

    @staticmethod
    def _require_single_turn_completed(events: Iterable[JsonObject], requested_model_name: str) -> None:
        turn_completed_count: int = sum(1 for event in events if event.get(EVENT_TYPE_FIELD) == EVENT_TYPE_TURN_COMPLETED)
        if turn_completed_count != 1:
            ValidatorCodexEventStreamResource._raise_malformed(
                requested_model_name, f"expected exactly one {EVENT_TYPE_TURN_COMPLETED} event, found {turn_completed_count}"
            )

    @staticmethod
    def _parse_agent_messages(latest_items: Iterable[JsonObject], requested_model_name: str) -> tuple[CodexAgentMessageResource, ...]:
        return tuple(
            CodexAgentMessageResource(
                item_id=ValidatorCodexEventStreamResource._read_string(item, "id", requested_model_name),
                message_text=ValidatorCodexEventStreamResource._read_string(item, "text", requested_model_name),
            )
            for item in latest_items
            if item.get(EVENT_TYPE_FIELD) == ITEM_TYPE_AGENT_MESSAGE
        )

    @staticmethod
    def _parse_tool_items(latest_items: Iterable[JsonObject], requested_model_name: str) -> tuple[CodexToolItemResource, ...]:
        return tuple(
            ValidatorCodexEventStreamResource._parse_tool_item(item, requested_model_name)
            for item in latest_items
            if item.get(EVENT_TYPE_FIELD) in TOOL_ITEM_TYPES
        )

    @staticmethod
    def _parse_tool_item(item: Mapping[str, object], requested_model_name: str) -> CodexToolItemResource:
        if item.get(EVENT_TYPE_FIELD) == ITEM_TYPE_COMMAND_EXECUTION:
            return ValidatorCodexEventStreamResource._parse_command_execution(item, requested_model_name)
        return ValidatorCodexEventStreamResource._parse_file_change(item, requested_model_name)

    @staticmethod
    def _parse_command_execution(item: Mapping[str, object], requested_model_name: str) -> CodexCommandExecutionResource:
        return CodexCommandExecutionResource(
            item_id=ValidatorCodexEventStreamResource._read_string(item, "id", requested_model_name),
            command=ValidatorCodexEventStreamResource._read_string(item, "command", requested_model_name),
            exit_code=ValidatorCodexEventStreamResource._read_optional_whole_number(item, "exit_code", requested_model_name),
            status=ValidatorCodexEventStreamResource._read_string(item, "status", requested_model_name),
        )

    @staticmethod
    def _parse_file_change(item: Mapping[str, object], requested_model_name: str) -> CodexFileChangeResource:
        return CodexFileChangeResource(
            item_id=ValidatorCodexEventStreamResource._read_string(item, "id", requested_model_name),
            codex_file_update_resources=tuple(
                CodexFileUpdateResource(
                    file_path=ValidatorCodexEventStreamResource._read_string(file_update, "path", requested_model_name),
                    change_kind=ValidatorCodexEventStreamResource._read_string(file_update, "kind", requested_model_name),
                )
                for file_update in ValidatorCodexEventStreamResource._read_object_list(item, "changes", requested_model_name)
            ),
            status=ValidatorCodexEventStreamResource._read_string(item, "status", requested_model_name),
        )

    @staticmethod
    def _read_optional_whole_number(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> int | None:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            return None
        # bool is a subclass of int, so a JSON true would otherwise pass as the number 1.
        if not isinstance(field_value, int) or isinstance(field_value, bool):
            ValidatorCodexEventStreamResource._raise_malformed(
                requested_model_name, f"the field '{field_name}' is not a whole number or null: {field_value!r:.200}"
            )
        return field_value

    @staticmethod
    def _read_object_list(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> list[JsonObject]:
        field_value: object = json_object.get(field_name)
        if not isinstance(field_value, list):
            ValidatorCodexEventStreamResource._raise_malformed(requested_model_name, f"the field '{field_name}' is not a list: {field_value!r:.200}")
        list_items: list[object] = cast(list[object], field_value)
        for list_item in list_items:
            if not isinstance(list_item, dict):
                ValidatorCodexEventStreamResource._raise_malformed(
                    requested_model_name, f"an entry of the field '{field_name}' is not a JSON object: {list_item!r:.200}"
                )
        return cast(list[JsonObject], list_items)

    @staticmethod
    def _read_object(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> JsonObject:
        field_value: object = json_object.get(field_name)
        if not isinstance(field_value, dict):
            ValidatorCodexEventStreamResource._raise_malformed(
                requested_model_name,
                f"the field '{field_name}' of a {json_object.get(EVENT_TYPE_FIELD)} event is not a JSON object: {field_value!r:.200}",
            )
        return cast(JsonObject, field_value)

    @staticmethod
    def _read_string(json_object: Mapping[str, object], field_name: str, requested_model_name: str) -> str:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            ValidatorCodexEventStreamResource._raise_malformed(requested_model_name, f"the field '{field_name}' is missing")
        if not isinstance(field_value, str):
            ValidatorCodexEventStreamResource._raise_malformed(
                requested_model_name, f"the field '{field_name}' is a {type(field_value).__name__}, not a string: {field_value!r:.200}"
            )
        return field_value

    @staticmethod
    def _raise_malformed(requested_model_name: str, malformation_description: str) -> NoReturn:
        raise LlmSessionOutputMalformedException(CODEX_ASSISTANT_NAME, requested_model_name, malformation_description)
