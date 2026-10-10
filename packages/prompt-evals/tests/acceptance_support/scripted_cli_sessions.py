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
    """A Codex shell command. A status of "in_progress" reports only its start, as when the session ends while it runs."""

    command: str
    aggregated_output: str = ""
    exit_code: int | None = 0
    status: str = "completed"


@dataclass(frozen=True)
class ScriptedCodexFileChange:
    """A Codex file edit of one file; `change_kind` is "add", "update" or "delete"."""

    file_path: str
    change_kind: str
    status: str = "completed"


type ScriptedToolCallItem = ScriptedClaudeToolCall | ScriptedCodexCommandExecution | ScriptedCodexFileChange


@dataclass(frozen=True)
class ScriptedEventStreamSession:
    """The process prints the event stream of a session with this outcome, in the format of the CLI that was launched.

    Tool calls are written in the launched assistant's own terms, so a session that uses tools suits one assistant only.
    """

    final_text: str = ""
    structured_output: dict[str, object] | None = None
    scripted_tool_calls: tuple[ScriptedToolCallItem, ...] = ()
    is_error: bool = False
    exit_code: int = 0
    standard_error_text: str = ""
    # Claude Code only: the result subtype the CLI reports; None reports the one that matches is_error.
    result_subtype: str | None = None
    # The causes an error lists: Claude Code's result "errors" field, or the provider messages of Codex's failed turn.
    error_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScriptedRawOutputSession:
    """The process prints exactly this text, for example output that is not an event stream."""

    raw_standard_output_text: str
    exit_code: int = 0
    standard_error_text: str = ""


@dataclass(frozen=True)
class ScriptedFailedStartSession:
    """Running the process raises this exception, for example a timeout or an executable that cannot start."""

    raised_exception: BaseException


type ScriptedCliSession = ScriptedEventStreamSession | ScriptedRawOutputSession | ScriptedFailedStartSession
