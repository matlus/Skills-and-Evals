from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptedClaudeToolCall:
    """A Claude Code tool call, named the way Claude Code names its tools (for example "Bash")."""

    tool_name: str
    tool_input: dict[str, object]
    tool_result_text: str
    is_error: bool = False


@dataclass(frozen=True)
class ScriptedCodexCommandExecution:
    """A Codex shell command. An execution status of "in_progress" reports only its start, as when the session ends while it runs."""

    command: str
    aggregated_output: str = ""
    exit_code: int | None = 0
    execution_status: str = "completed"


@dataclass(frozen=True)
class ScriptedCodexFileChange:
    """A Codex file edit of one file; `change_kind` is "add", "update" or "delete"."""

    file_path: str
    change_kind: str
    change_status: str = "completed"


type ScriptedCodexToolCall = ScriptedCodexCommandExecution | ScriptedCodexFileChange


@dataclass(frozen=True)
class ScriptedAnswerSession:
    """The process prints the event stream of a successful session that used no tools and answered with this, in the format
    of whichever CLI was launched. Graders use no tools, so their sessions print correctly in either assistant."""

    final_text: str = ""
    structured_output: dict[str, object] | None = None


@dataclass(frozen=True)
class ScriptedClaudeEventStreamSession:
    """The process prints the Claude Code event stream of a session with this outcome."""

    final_text: str = ""
    structured_output: dict[str, object] | None = None
    scripted_claude_tool_calls: tuple[ScriptedClaudeToolCall, ...] = ()
    is_error: bool = False
    exit_code: int = 0
    standard_error_text: str = ""
    # The result subtype the CLI reports; None reports the one that matches is_error.
    result_subtype: str | None = None
    # The causes an error lists: Claude Code's result "errors" field.
    error_messages: tuple[str, ...] = ()
    # The session duration its result event reports; None leaves duration_ms out of the result event, as the CLI sometimes does.
    duration_milliseconds: int | None = 1234


@dataclass(frozen=True)
class ScriptedCodexEventStreamSession:
    """The process prints the Codex event stream of a session with this outcome."""

    final_text: str = ""
    structured_output: dict[str, object] | None = None
    scripted_codex_tool_calls: tuple[ScriptedCodexToolCall, ...] = ()
    is_error: bool = False
    exit_code: int = 0
    standard_error_text: str = ""
    # The provider messages of Codex's failed turn.
    error_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScriptedRawOutputSession:
    """The process prints exactly this text, for example output that is not an event stream."""

    raw_standard_output_text: str
    exit_code: int = 0
    standard_error_text: str = ""


@dataclass(frozen=True)
class ScriptedTimedOutSession:
    """The process outlives the timeout it was launched with, so the process runner raises a ProcessTimedOutException."""


@dataclass(frozen=True)
class ScriptedFailedStartSession:
    """The process runner raises this exception, for example a ProcessStartFailedException for an executable that cannot
    start, or a ProcessContainmentFailedException for a process that cannot be contained."""

    raised_exception: BaseException


type ScriptedCliSession = (
    ScriptedAnswerSession
    | ScriptedClaudeEventStreamSession
    | ScriptedCodexEventStreamSession
    | ScriptedRawOutputSession
    | ScriptedTimedOutSession
    | ScriptedFailedStartSession
)
