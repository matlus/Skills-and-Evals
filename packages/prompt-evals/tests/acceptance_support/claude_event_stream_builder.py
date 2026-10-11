import json
from typing import Final

from acceptance_support.scripted_cli_sessions import ScriptedClaudeEventStreamSession, ScriptedClaudeToolCall

RESULT_SUBTYPE_SUCCESS: Final[str] = "success"
RESULT_SUBTYPE_ERROR: Final[str] = "error_during_execution"


class ClaudeEventStreamBuilder:
    """Builds the newline-delimited JSON a real `claude -p --output-format stream-json --verbose` run prints."""

    @staticmethod
    def build_event_stream(model_name: str, scripted_claude_event_stream_session: ScriptedClaudeEventStreamSession) -> str:
        event_lines: list[str] = [ClaudeEventStreamBuilder._serialize_event({"type": "system", "subtype": "init", "model": model_name, "tools": []})]
        tool_call_number: int
        scripted_claude_tool_call: ScriptedClaudeToolCall
        for tool_call_number, scripted_claude_tool_call in enumerate(scripted_claude_event_stream_session.scripted_claude_tool_calls, start=1):
            tool_use_id: str = f"toolu_{tool_call_number:04d}"
            event_lines.append(ClaudeEventStreamBuilder._build_tool_use_event(tool_use_id, scripted_claude_tool_call))
            event_lines.append(ClaudeEventStreamBuilder._build_tool_result_event(tool_use_id, scripted_claude_tool_call))
        event_lines.append(ClaudeEventStreamBuilder._build_result_event(scripted_claude_event_stream_session))
        return "\n".join(event_lines) + "\n"

    @staticmethod
    def _build_tool_use_event(tool_use_id: str, scripted_claude_tool_call: ScriptedClaudeToolCall) -> str:
        return ClaudeEventStreamBuilder._serialize_event(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": scripted_claude_tool_call.tool_name,
                            "input": scripted_claude_tool_call.tool_input,
                        }
                    ]
                },
            }
        )

    @staticmethod
    def _build_tool_result_event(tool_use_id: str, scripted_claude_tool_call: ScriptedClaudeToolCall) -> str:
        return ClaudeEventStreamBuilder._serialize_event(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": [{"type": "text", "text": scripted_claude_tool_call.tool_result_text}],
                            "is_error": scripted_claude_tool_call.is_error,
                        }
                    ]
                },
            }
        )

    @staticmethod
    def _build_result_event(scripted_claude_event_stream_session: ScriptedClaudeEventStreamSession) -> str:
        result_event: dict[str, object] = {
            "type": "result",
            "subtype": ClaudeEventStreamBuilder._select_result_subtype(scripted_claude_event_stream_session),
            "is_error": scripted_claude_event_stream_session.is_error,
            "result": scripted_claude_event_stream_session.final_text,
            "structured_output": scripted_claude_event_stream_session.structured_output,
            "errors": list(scripted_claude_event_stream_session.error_messages),
            "total_cost_usd": 0.0123,
        }
        # The CLI leaves duration_ms out of some results rather than writing null.
        if scripted_claude_event_stream_session.duration_milliseconds is not None:
            result_event["duration_ms"] = scripted_claude_event_stream_session.duration_milliseconds
        return ClaudeEventStreamBuilder._serialize_event(result_event)

    @staticmethod
    def _select_result_subtype(scripted_claude_event_stream_session: ScriptedClaudeEventStreamSession) -> str:
        if scripted_claude_event_stream_session.result_subtype is not None:
            return scripted_claude_event_stream_session.result_subtype
        return RESULT_SUBTYPE_ERROR if scripted_claude_event_stream_session.is_error else RESULT_SUBTYPE_SUCCESS

    @staticmethod
    def _serialize_event(event: dict[str, object]) -> str:
        # The CLI serializes with JSON.stringify, which writes non-ASCII text (including U+2028 and U+0085) unescaped.
        return json.dumps(event, ensure_ascii=False)
