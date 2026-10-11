import json
from typing import Final

from acceptance_support.scripted_cli_sessions import (
    ScriptedCodexCommandExecution,
    ScriptedCodexEventStreamSession,
    ScriptedCodexFileChange,
    ScriptedCodexToolCall,
)

ITEM_STATUS_IN_PROGRESS: Final[str] = "in_progress"
# What Codex reports for a failed model request: the provider's HTTP status and its error, as JSON text.
FAILED_REQUEST_STATUS: Final[int] = 400
# Codex warns this way for a model it has no metadata for, which is every model name a test invents.
UNKNOWN_MODEL_WARNING: Final[str] = "Model metadata not found. Defaulting to fallback metadata; this can degrade performance."


class CodexEventStreamBuilder:
    """Builds the newline-delimited JSON a real `codex exec --json` run prints."""

    @staticmethod
    def build_event_stream(scripted_codex_event_stream_session: ScriptedCodexEventStreamSession) -> str:
        event_lines: list[str] = [
            CodexEventStreamBuilder._serialize_event({"type": "thread.started", "thread_id": "0199a213-81c0-7800-8aa1-bbab2a035a53"}),
            CodexEventStreamBuilder._serialize_event({"type": "turn.started"}),
            CodexEventStreamBuilder._build_item_event("item.completed", {"id": "item_0", "type": "error", "message": UNKNOWN_MODEL_WARNING}),
        ]
        item_number: int
        scripted_codex_tool_call: ScriptedCodexToolCall
        for item_number, scripted_codex_tool_call in enumerate(scripted_codex_event_stream_session.scripted_codex_tool_calls, start=1):
            event_lines.extend(CodexEventStreamBuilder._build_tool_item_events(f"item_{item_number}", scripted_codex_tool_call))
        final_item_id: str = f"item_{len(scripted_codex_event_stream_session.scripted_codex_tool_calls) + 1}"
        if scripted_codex_event_stream_session.is_error:
            event_lines.extend(CodexEventStreamBuilder._build_turn_failure_events(scripted_codex_event_stream_session))
        else:
            event_lines.extend(CodexEventStreamBuilder._build_turn_completion_events(final_item_id, scripted_codex_event_stream_session))
        return "\n".join(event_lines) + "\n"

    @staticmethod
    def _build_tool_item_events(item_id: str, scripted_codex_tool_call: ScriptedCodexToolCall) -> list[str]:
        match scripted_codex_tool_call:
            case ScriptedCodexCommandExecution():
                return CodexEventStreamBuilder._build_command_execution_events(item_id, scripted_codex_tool_call)
            case ScriptedCodexFileChange():
                return CodexEventStreamBuilder._build_file_change_events(item_id, scripted_codex_tool_call)

    @staticmethod
    def _build_command_execution_events(item_id: str, scripted_codex_command_execution: ScriptedCodexCommandExecution) -> list[str]:
        started_item: dict[str, object] = {
            "id": item_id,
            "type": "command_execution",
            "command": scripted_codex_command_execution.command,
            "aggregated_output": "",
            "exit_code": None,
            "status": ITEM_STATUS_IN_PROGRESS,
        }
        command_events: list[str] = [CodexEventStreamBuilder._build_item_event("item.started", started_item)]
        if scripted_codex_command_execution.execution_status != ITEM_STATUS_IN_PROGRESS:
            completed_item: dict[str, object] = started_item | {
                "aggregated_output": scripted_codex_command_execution.aggregated_output,
                "exit_code": scripted_codex_command_execution.exit_code,
                "status": scripted_codex_command_execution.execution_status,
            }
            command_events.append(CodexEventStreamBuilder._build_item_event("item.completed", completed_item))
        return command_events

    @staticmethod
    def _build_file_change_events(item_id: str, scripted_codex_file_change: ScriptedCodexFileChange) -> list[str]:
        file_change_item: dict[str, object] = {
            "id": item_id,
            "type": "file_change",
            "changes": [{"path": scripted_codex_file_change.file_path, "kind": scripted_codex_file_change.change_kind}],
            "status": scripted_codex_file_change.change_status,
        }
        item_event_type: str = "item.started" if scripted_codex_file_change.change_status == ITEM_STATUS_IN_PROGRESS else "item.completed"
        return [CodexEventStreamBuilder._build_item_event(item_event_type, file_change_item)]

    @staticmethod
    def _build_turn_completion_events(final_item_id: str, scripted_codex_event_stream_session: ScriptedCodexEventStreamSession) -> list[str]:
        # With --output-schema, Codex answers with the structured output as the text of its final message.
        final_message_text: str = (
            scripted_codex_event_stream_session.final_text
            if scripted_codex_event_stream_session.structured_output is None
            else json.dumps(scripted_codex_event_stream_session.structured_output, ensure_ascii=False)
        )
        turn_completed_event: str = CodexEventStreamBuilder._serialize_event(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 1234,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 56,
                    "reasoning_output_tokens": 7,
                },
            }
        )
        if not final_message_text:
            return [turn_completed_event]
        final_message_event: str = CodexEventStreamBuilder._build_item_event(
            "item.completed", {"id": final_item_id, "type": "agent_message", "text": final_message_text}
        )
        return [final_message_event, turn_completed_event]

    @staticmethod
    def _build_turn_failure_events(scripted_codex_event_stream_session: ScriptedCodexEventStreamSession) -> list[str]:
        provider_messages: tuple[str, ...] = scripted_codex_event_stream_session.error_messages or (scripted_codex_event_stream_session.final_text,)
        failure_texts: list[str] = [
            json.dumps({"status": FAILED_REQUEST_STATUS, "error": {"type": "invalid_request_error", "message": provider_message}})
            for provider_message in provider_messages
        ]
        error_events: list[str] = [
            CodexEventStreamBuilder._serialize_event({"type": "error", "message": failure_text}) for failure_text in failure_texts
        ]
        turn_failed_event: str = CodexEventStreamBuilder._serialize_event({"type": "turn.failed", "error": {"message": failure_texts[-1]}})
        return [*error_events, turn_failed_event]

    @staticmethod
    def _build_item_event(item_event_type: str, item: dict[str, object]) -> str:
        return CodexEventStreamBuilder._serialize_event({"type": item_event_type, "item": item})

    @staticmethod
    def _serialize_event(event: dict[str, object]) -> str:
        # The CLI serializes with serde_json, which writes non-ASCII text (including U+2028 and U+0085) unescaped.
        return json.dumps(event, ensure_ascii=False)
