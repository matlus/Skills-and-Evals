from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ClaudeToolUseResource:
    tool_use_id: str
    tool_name: str
    tool_input_json: str


@dataclass(frozen=True)
class ClaudeToolResultResource:
    tool_use_id: str
    result_text: str
    is_error: bool


@dataclass(frozen=True)
class ClaudeResultResource:
    subtype: str
    is_error: bool
    result_text: str
    structured_output_json: str | None
    duration_milliseconds: int | None
    total_cost_usd: Decimal | None
    error_messages: tuple[str, ...]


@dataclass(frozen=True)
class ClaudeEventStreamResource:
    model_name: str
    claude_tool_use_resources: tuple[ClaudeToolUseResource, ...]
    claude_tool_result_resources: tuple[ClaudeToolResultResource, ...]
    claude_result_resource: ClaudeResultResource
