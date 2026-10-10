from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessInvocation:
    command_arguments: tuple[str, ...]
    standard_input_text: str
    working_directory: Path
    timeout_seconds: float


@dataclass(frozen=True)
class ProcessOutcome:
    exit_code: int
    standard_output_text: str
    standard_error_text: str
