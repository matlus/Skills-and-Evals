"""Why a run folder's scorecard.json cannot be compared. Each failure has its own type and one raise site.

A scorecard that is not one this app wrote is the caller's to correct (business); a file the operating system cannot
read is ours to fix (technical).
"""

from pathlib import Path
from typing import Final, final

from prompt_evals import PromptEvalsBusinessBaseException, PromptEvalsTechnicalBaseException

SCORECARD_PATH_CONTEXT_NAME: Final[str] = "ScorecardPath"
FIELD_NAME_CONTEXT_NAME: Final[str] = "FieldName"
HELD_VALUE_CONTEXT_NAME: Final[str] = "HeldValue"


@final
class ScorecardSummaryNotUtf8Exception(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, decode_error: str) -> None:
        super().__init__(
            f"{scorecard_path} is not UTF-8 text, so it is not a scorecard this app wrote: {decode_error}",
            {SCORECARD_PATH_CONTEXT_NAME: str(scorecard_path), "DecodeError": decode_error},
        )


@final
class ScorecardSummaryReadFailedException(PromptEvalsTechnicalBaseException):
    def __init__(self, scorecard_path: Path, read_error: str) -> None:
        super().__init__(
            f"{scorecard_path} exists but could not be read: {read_error}",
            {SCORECARD_PATH_CONTEXT_NAME: str(scorecard_path), "ReadError": read_error},
        )


@final
class ScorecardSummaryNotJsonException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, json_error: str) -> None:
        super().__init__(
            f"{scorecard_path} is not valid JSON: {json_error}", {SCORECARD_PATH_CONTEXT_NAME: str(scorecard_path), "JsonError": json_error}
        )


@final
class ScorecardSummaryNotObjectException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, held_type_name: str) -> None:
        super().__init__(
            f"{scorecard_path} must hold a JSON object; it holds {held_type_name}",
            {SCORECARD_PATH_CONTEXT_NAME: str(scorecard_path), "HeldType": held_type_name},
        )


def _field_context(scorecard_path: Path, field_name: str, held_value: str) -> dict[str, str | int | float | bool]:
    return {SCORECARD_PATH_CONTEXT_NAME: str(scorecard_path), FIELD_NAME_CONTEXT_NAME: field_name, HELD_VALUE_CONTEXT_NAME: held_value}


@final
class ScorecardSummaryFieldNotObjectException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be a JSON object; it holds {held_value}", _field_context(scorecard_path, field_name, held_value)
        )


@final
class ScorecardSummaryFieldNotObjectListException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be a list of JSON objects; it holds {held_value}",
            _field_context(scorecard_path, field_name, held_value),
        )


@final
class ScorecardSummaryFieldNotTextException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be a string; it holds {held_value}", _field_context(scorecard_path, field_name, held_value)
        )


@final
class ScorecardSummaryFieldNotBooleanException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be true or false; it holds {held_value}", _field_context(scorecard_path, field_name, held_value)
        )


@final
class ScorecardSummaryFieldNotCountException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be a whole number of zero or more; it holds {held_value}",
            _field_context(scorecard_path, field_name, held_value),
        )


@final
class ScorecardSummaryFieldNotSecondsException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, field_name: str, held_value: str) -> None:
        super().__init__(
            f"{scorecard_path}: {field_name} must be a finite number of seconds of zero or more; it holds {held_value}",
            _field_context(scorecard_path, field_name, held_value),
        )
