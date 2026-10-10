import json
from typing import Final

from acceptance_support.scripted_cli_sessions import ScriptedClaudeToolCall, ScriptedEventStreamSession, ScriptedToolCallItem

RESULT_SUBTYPE_SUCCESS: Final[str] = "success"
RESULT_SUBTYPE_ERROR: Final[str] = "error_during_execution"


class ClaudeEventStreamBuilder:
    """Builds the newline-delimited JSON a real `claude -p --output-format stream-json --verbose` run prints."""

    @staticmethod
    def build_event_stream(model_name: str, scripted_event_stream_session: ScriptedEventStreamSession) -> str:
        event_lines: list[str] = [ClaudeEventStreamBuilder._serialize_event({"type": "system", "subtype": "init", "model": model_name, "tools": []})]
        tool_call_number: int
        scripted_tool_call_item: ScriptedToolCallItem
        for tool_call_number, scripted_tool_call_item in enumerate(scripted_event_stream_session.scripted_tool_calls, start=1):
            scripted_tool_call: ScriptedClaudeToolCall = ClaudeEventStreamBuilder._require_claude_tool_call(scripted_tool_call_item)
            tool_use_id: str = f"toolu_{tool_call_number:04d}"
            event_lines.append(ClaudeEventStreamBuilder._build_tool_use_event(tool_use_id, scripted_tool_call))
            event_lines.append(ClaudeEventStreamBuilder._build_tool_result_event(tool_use_id, scripted_tool_call))
        event_lines.append(ClaudeEventStreamBuilder._build_result_event(scripted_event_stream_session))
        return "\n".join(event_lines) + "\n"

    @staticmethod
    def _require_claude_tool_call(scripted_tool_call_item: ScriptedToolCallItem) -> ScriptedClaudeToolCall:
        match scripted_tool_call_item:
            case ScriptedClaudeToolCall():
                return scripted_tool_call_item
            case _:
                raise AssertionError(f"The test scripted a {type(scripted_tool_call_item).__name__} for a Claude Code session")

    @staticmethod
    def _build_tool_use_event(tool_use_id: str, scripted_tool_call: ScriptedClaudeToolCall) -> str:
        return ClaudeEventStreamBuilder._serialize_event(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "tool_use", "id": tool_use_id, "name": scripted_tool_call.tool_name, "input": scripted_tool_call.tool_input}]
                },
            }
        )

    @staticmethod
    def _build_tool_result_event(tool_use_id: str, scripted_tool_call: ScriptedClaudeToolCall) -> str:
        return ClaudeEventStreamBuilder._serialize_event(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": [{"type": "text", "text": scripted_tool_call.tool_result_text}],
                            "is_error": scripted_tool_call.is_error,
                        }
                    ]
                },
            }
        )

    @staticmethod
    def _build_result_event(scripted_event_stream_session: ScriptedEventStreamSession) -> str:
        return ClaudeEventStreamBuilder._serialize_event(
            {
                "type": "result",
                "subtype": ClaudeEventStreamBuilder._select_result_subtype(scripted_event_stream_session),
                "is_error": scripted_event_stream_session.is_error,
                "result": scripted_event_stream_session.final_text,
                "structured_output": scripted_event_stream_session.structured_output,
                "errors": list(scripted_event_stream_session.error_messages),
                "duration_ms": 1234,
                "total_cost_usd": 0.0123,
            }
        )

    @staticmethod
    def _select_result_subtype(scripted_event_stream_session: ScriptedEventStreamSession) -> str:
        if scripted_event_stream_session.result_subtype is not None:
            return scripted_event_stream_session.result_subtype
        return RESULT_SUBTYPE_ERROR if scripted_event_stream_session.is_error else RESULT_SUBTYPE_SUCCESS

    @staticmethod
    def _serialize_event(event: dict[str, object]) -> str:
        # The CLI serializes with JSON.stringify, which writes non-ASCII text (including U+2028 and U+0085) unescaped.
        return json.dumps(event, ensure_ascii=False)
