from dataclasses import dataclass


@dataclass(frozen=True)
class CodexCliSettings:
    executable_path: str
    session_timeout_seconds: float
