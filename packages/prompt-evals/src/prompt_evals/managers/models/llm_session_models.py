from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from prompt_evals.managers.models.eval_suite_models import InputFile, ToolKind
from prompt_evals.managers.models.evaluation_models import EffortLevel


class ToolCallOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    # The session ended before the tool returned; the call did not run to completion.
    UNFINISHED = "unfinished"


@dataclass(frozen=True)
class LlmSessionRequest:
    """One brand-new, isolated coding-assistant session: a prompt, the files it may see, and how to run it.

    An empty `tool_kinds` runs the session with no tools at all. A `structured_output_schema`
    (JSON Schema text) makes the session answer with JSON that matches it.
    """

    prompt_text: str
    input_files: tuple[InputFile, ...]
    model_name: str
    effort_level: EffortLevel
    tool_kinds: tuple[ToolKind, ...]
    structured_output_schema: str | None


@dataclass(frozen=True)
class ToolCall:
    """`tool_input_text` is the text the model supplied to the tool (for a shell call, the command), not a wire encoding."""

    tool_kind: ToolKind
    tool_input_text: str
    tool_call_outcome: ToolCallOutcome


@dataclass(frozen=True)
class LlmSessionTranscript:
    """What one session produced, in the domain's terms. `total_cost_usd` is None when the assistant does not report cost,
    and `duration_milliseconds` is None when a recorded session is read again and its event stream holds no duration."""

    final_text: str
    structured_output_json: str | None
    tool_calls: tuple[ToolCall, ...]
    resolved_model_name: str
    duration_milliseconds: int | None
    total_cost_usd: Decimal | None
    event_stream_text: str
