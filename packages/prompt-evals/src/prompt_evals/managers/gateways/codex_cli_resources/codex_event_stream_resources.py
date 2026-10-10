from dataclasses import dataclass


@dataclass(frozen=True)
class CodexAgentMessageResource:
    item_id: str
    message_text: str


@dataclass(frozen=True)
class CodexCommandExecutionResource:
    """The latest state the stream reported for one shell command; `exit_code` is None while the command runs."""

    item_id: str
    command: str
    exit_code: int | None
    status: str


@dataclass(frozen=True)
class CodexFileUpdateResource:
    file_path: str
    change_kind: str


@dataclass(frozen=True)
class CodexFileChangeResource:
    item_id: str
    codex_file_update_resources: tuple[CodexFileUpdateResource, ...]
    status: str


type CodexToolItemResource = CodexCommandExecutionResource | CodexFileChangeResource


@dataclass(frozen=True)
class CodexTurnFailureResource:
    """`failure_kind` is the event that reported the failure; `provider_messages` are its readable causes, in stream order."""

    failure_kind: str
    provider_messages: tuple[str, ...]


@dataclass(frozen=True)
class CodexEventStreamResource:
    """One `codex exec --json` turn. Tool items keep the order in which they started; None means the turn did not fail."""

    codex_agent_message_resources: tuple[CodexAgentMessageResource, ...]
    codex_tool_item_resources: tuple[CodexToolItemResource, ...]
    codex_turn_failure_resource: CodexTurnFailureResource | None
