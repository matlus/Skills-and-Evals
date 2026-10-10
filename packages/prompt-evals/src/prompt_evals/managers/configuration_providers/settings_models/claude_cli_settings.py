from dataclasses import dataclass


@dataclass(frozen=True)
class ClaudeCliSettings:
    executable_path: str
    session_timeout_seconds: float
