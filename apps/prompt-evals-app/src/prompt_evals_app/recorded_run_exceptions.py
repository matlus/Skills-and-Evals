"""Why a run folder cannot be regraded. Each failure has its own type and one raise site.

A folder that is not a run this app wrote is the caller's to correct (business); a file the operating system cannot read
is ours to fix (technical).
"""

from pathlib import Path
from typing import Final, final

from prompt_evals import PromptEvalsBusinessBaseException, PromptEvalsTechnicalBaseException

FILE_PATH_CONTEXT_NAME: Final[str] = "FilePath"


@final
class RecordedRunScorecardMissingException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path) -> None:
        super().__init__(f"{scorecard_path} does not exist, so the folder is not a run this app wrote", {FILE_PATH_CONTEXT_NAME: str(scorecard_path)})


@final
class RecordedRunScorecardNotJsonException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, json_error: str) -> None:
        super().__init__(f"{scorecard_path} is not valid JSON: {json_error}", {FILE_PATH_CONTEXT_NAME: str(scorecard_path), "JsonError": json_error})


@final
class RecordedRunScorecardNotObjectException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, held_type_name: str) -> None:
        super().__init__(
            f"{scorecard_path} must hold a JSON object; it holds {held_type_name}",
            {FILE_PATH_CONTEXT_NAME: str(scorecard_path), "HeldType": held_type_name},
        )


@final
class RecordedRunSettingsNotTextException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, non_text_fields: str) -> None:
        super().__init__(
            f"{scorecard_path} must hold a string coding_assistant, model_name and effort_level; these are not strings: {non_text_fields}",
            {FILE_PATH_CONTEXT_NAME: str(scorecard_path), "NonTextFields": non_text_fields},
        )


@final
class RecordedRunSettingUnknownException(PromptEvalsBusinessBaseException):
    def __init__(self, scorecard_path: Path, unknown_value_description: str, known_values_description: str) -> None:
        super().__init__(
            f"{scorecard_path}: {unknown_value_description}; {known_values_description}",
            {FILE_PATH_CONTEXT_NAME: str(scorecard_path), "UnknownValue": unknown_value_description},
        )


@final
class RecordedRunTrialsMissingException(PromptEvalsBusinessBaseException):
    def __init__(self, trials_directory: Path) -> None:
        super().__init__(f"{trials_directory} holds no trials/<variant>/<case>/run-NN folders", {"TrialsDirectory": str(trials_directory)})


@final
class RecordedTrialOutcomeMissingException(PromptEvalsBusinessBaseException):
    def __init__(self, trial_directory: Path, event_stream_file_name: str, error_file_name: str) -> None:
        super().__init__(f"{trial_directory} holds neither {event_stream_file_name} nor {error_file_name}", {"TrialDirectory": str(trial_directory)})


@final
class RecordedTrialTimingNotJsonException(PromptEvalsBusinessBaseException):
    def __init__(self, timing_path: Path, json_error: str) -> None:
        super().__init__(f"{timing_path} is not valid JSON: {json_error}", {FILE_PATH_CONTEXT_NAME: str(timing_path), "JsonError": json_error})


@final
class RecordedTrialTimingNotObjectException(PromptEvalsBusinessBaseException):
    def __init__(self, timing_path: Path, held_type_name: str) -> None:
        super().__init__(
            f"{timing_path} must hold a JSON object; it holds {held_type_name}",
            {FILE_PATH_CONTEXT_NAME: str(timing_path), "HeldType": held_type_name},
        )


@final
class RecordedTrialAnswerDurationInvalidException(PromptEvalsBusinessBaseException):
    def __init__(self, timing_path: Path, answer_duration_field_name: str, held_value: str) -> None:
        super().__init__(
            f"{timing_path} must hold a finite number of seconds of zero or more, or null, for {answer_duration_field_name}; it holds {held_value}",
            {FILE_PATH_CONTEXT_NAME: str(timing_path), "HeldValue": held_value},
        )


@final
class RecordedRunFileNotUtf8Exception(PromptEvalsBusinessBaseException):
    def __init__(self, file_path: Path, decode_error: str) -> None:
        super().__init__(
            f"{file_path} is not UTF-8 text, so it is not a file this app wrote: {decode_error}",
            {FILE_PATH_CONTEXT_NAME: str(file_path), "DecodeError": decode_error},
        )


@final
class RecordedRunFileReadFailedException(PromptEvalsTechnicalBaseException):
    def __init__(self, file_path: Path, read_error: str) -> None:
        super().__init__(f"{file_path} exists but could not be read: {read_error}", {FILE_PATH_CONTEXT_NAME: str(file_path), "ReadError": read_error})
