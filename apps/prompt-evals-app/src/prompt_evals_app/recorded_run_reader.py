import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast, final

from prompt_evals import CodingAssistant, EffortLevel, RecordedCompletedTrial, RecordedErroredTrial, RecordedTrial, TrialIdentity
from prompt_evals_app.recorded_run_exceptions import (
    RecordedRunFileNotUtf8Exception,
    RecordedRunFileReadFailedException,
    RecordedRunScorecardMissingException,
    RecordedRunScorecardNotJsonException,
    RecordedRunScorecardNotObjectException,
    RecordedRunSettingsNotTextException,
    RecordedRunSettingUnknownException,
    RecordedRunTrialsMissingException,
    RecordedTrialAnswerDurationInvalidException,
    RecordedTrialOutcomeMissingException,
    RecordedTrialTimingNotJsonException,
    RecordedTrialTimingNotObjectException,
)

TEXT_ENCODING: Final[str] = "utf-8"
SCORECARD_FILE_NAME: Final[str] = "scorecard.json"
TRIALS_DIRECTORY_NAME: Final[str] = "trials"
EVENT_STREAM_FILE_NAME: Final[str] = "event_stream.jsonl"
ERROR_FILE_NAME: Final[str] = "error.txt"
TIMING_FILE_NAME: Final[str] = "timing.json"
ANSWER_DURATION_FIELD_NAME: Final[str] = "answer_duration_seconds"
CODING_ASSISTANT_FIELD_NAME: Final[str] = "coding_assistant"
MODEL_NAME_FIELD_NAME: Final[str] = "model_name"
EFFORT_LEVEL_FIELD_NAME: Final[str] = "effort_level"
RUN_DIRECTORY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^run-(\d+)$")

type JsonObject = dict[str, object]


@dataclass(frozen=True)
class RecordedRun:
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    recorded_trials: tuple[RecordedTrial, ...]


@dataclass(frozen=True)
class RecordedRunSettings:
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel


@final
class RecordedRunReader:
    """Reads a run directory written by ResultsDirectoryWriter back into recorded trials.

    The run's settings come from its scorecard.json. Runs written before the scorecard recorded the coding assistant
    use `fallback_coding_assistant`.
    """

    @staticmethod
    def read_recorded_run(run_directory: Path, fallback_coding_assistant: CodingAssistant) -> RecordedRun:
        scorecard_path: Path = run_directory / SCORECARD_FILE_NAME
        if not scorecard_path.is_file():
            raise RecordedRunScorecardMissingException(scorecard_path)
        recorded_run_settings: RecordedRunSettings = RecordedRunReader._parse_run_settings(
            RecordedRunReader._read_text_file(scorecard_path), scorecard_path, fallback_coding_assistant
        )
        return RecordedRun(
            coding_assistant=recorded_run_settings.coding_assistant,
            model_name=recorded_run_settings.model_name,
            effort_level=recorded_run_settings.effort_level,
            recorded_trials=RecordedRunReader._read_recorded_trials(run_directory / TRIALS_DIRECTORY_NAME),
        )

    @staticmethod
    def _parse_run_settings(scorecard_text: str, scorecard_path: Path, fallback_coding_assistant: CodingAssistant) -> RecordedRunSettings:
        try:
            scorecard_document: object = json.loads(scorecard_text)
        except json.JSONDecodeError as invalid_scorecard:
            raise RecordedRunScorecardNotJsonException(scorecard_path, str(invalid_scorecard)) from invalid_scorecard
        if not isinstance(scorecard_document, dict):
            raise RecordedRunScorecardNotObjectException(scorecard_path, type(scorecard_document).__name__)
        scorecard_object: JsonObject = cast(JsonObject, scorecard_document)
        coding_assistant_value: object = scorecard_object.get(CODING_ASSISTANT_FIELD_NAME, fallback_coding_assistant.value)
        model_name: object = scorecard_object.get(MODEL_NAME_FIELD_NAME)
        effort_level_value: object = scorecard_object.get(EFFORT_LEVEL_FIELD_NAME)
        if not isinstance(coding_assistant_value, str) or not isinstance(model_name, str) or not isinstance(effort_level_value, str):
            field_value_by_field_name: dict[str, object] = {
                CODING_ASSISTANT_FIELD_NAME: coding_assistant_value,
                MODEL_NAME_FIELD_NAME: model_name,
                EFFORT_LEVEL_FIELD_NAME: effort_level_value,
            }
            non_string_fields: list[str] = [
                f"{field_name}={field_value_by_field_name[field_name]!r}"
                for field_name in field_value_by_field_name
                if not isinstance(field_value_by_field_name[field_name], str)
            ]
            raise RecordedRunSettingsNotTextException(scorecard_path, ", ".join(non_string_fields))
        try:
            return RecordedRunSettings(
                coding_assistant=CodingAssistant(coding_assistant_value), model_name=model_name, effort_level=EffortLevel(effort_level_value)
            )
        except ValueError as unknown_value:
            known_values_description: str = (
                f"known coding_assistant values are {sorted(coding_assistant.value for coding_assistant in CodingAssistant)} "
                f"and known effort_level values are {sorted(effort_level.value for effort_level in EffortLevel)}"
            )
            raise RecordedRunSettingUnknownException(scorecard_path, str(unknown_value), known_values_description) from unknown_value

    @staticmethod
    def _read_recorded_trials(trials_directory: Path) -> tuple[RecordedTrial, ...]:
        # Layout: trials/<variant>/<case>/run-NN/ holding event_stream.jsonl, or error.txt for a trial that errored.
        recorded_trials: list[RecordedTrial] = [
            RecordedRunReader._read_recorded_trial(trial_directory, RecordedRunReader._compose_trial_identity(trial_directory, run_match))
            for trial_directory in sorted(trials_directory.glob("*/*/run-*"))
            if (run_match := RUN_DIRECTORY_PATTERN.fullmatch(trial_directory.name)) is not None and trial_directory.is_dir()
        ]
        if not recorded_trials:
            raise RecordedRunTrialsMissingException(trials_directory)
        return tuple(recorded_trials)

    @staticmethod
    def _compose_trial_identity(trial_directory: Path, run_match: re.Match[str]) -> TrialIdentity:
        return TrialIdentity(
            variant_name=trial_directory.parent.parent.name, case_name=trial_directory.parent.name, repetition_number=int(run_match.group(1))
        )

    @staticmethod
    def _read_recorded_trial(trial_directory: Path, trial_identity: TrialIdentity) -> RecordedTrial:
        event_stream_path: Path = trial_directory / EVENT_STREAM_FILE_NAME
        if event_stream_path.is_file():
            return RecordedCompletedTrial(
                trial_identity=trial_identity,
                event_stream_text=RecordedRunReader._read_text_file(event_stream_path),
                answer_duration_seconds=RecordedRunReader._read_answer_duration(trial_directory / TIMING_FILE_NAME),
            )
        error_path: Path = trial_directory / ERROR_FILE_NAME
        if error_path.is_file():
            return RecordedErroredTrial(
                trial_identity=trial_identity,
                error_description=RecordedRunReader._read_text_file(error_path),
                answer_duration_seconds=RecordedRunReader._read_answer_duration(trial_directory / TIMING_FILE_NAME),
            )
        raise RecordedTrialOutcomeMissingException(trial_directory, EVENT_STREAM_FILE_NAME, ERROR_FILE_NAME)

    @staticmethod
    def _read_answer_duration(timing_path: Path) -> float | None:
        # Runs recorded before answer times were saved have no timing.json; their answer time is unknown, not zero.
        if not timing_path.is_file():
            return None
        return RecordedRunReader._parse_answer_duration(RecordedRunReader._read_text_file(timing_path), timing_path)

    @staticmethod
    def _parse_answer_duration(timing_text: str, timing_path: Path) -> float | None:
        try:
            timing_document: object = json.loads(timing_text)
        except json.JSONDecodeError as invalid_timing:
            raise RecordedTrialTimingNotJsonException(timing_path, str(invalid_timing)) from invalid_timing
        if not isinstance(timing_document, dict):
            raise RecordedTrialTimingNotObjectException(timing_path, type(timing_document).__name__)
        return RecordedRunReader._validate_answer_duration(cast(JsonObject, timing_document).get(ANSWER_DURATION_FIELD_NAME), timing_path)

    @staticmethod
    def _validate_answer_duration(answer_duration_value: object, timing_path: Path) -> float | None:
        if answer_duration_value is None:
            return None
        answer_duration_seconds: float | None = RecordedRunReader._as_seconds(answer_duration_value)
        if answer_duration_seconds is None:
            raise RecordedTrialAnswerDurationInvalidException(timing_path, ANSWER_DURATION_FIELD_NAME, repr(answer_duration_value))
        return answer_duration_seconds

    @staticmethod
    def _as_seconds(answer_duration_value: object) -> float | None:
        """The value as a finite, non-negative number of seconds, or None when it is not one."""
        # bool is a subclass of int, so true would otherwise read as one second.
        if isinstance(answer_duration_value, bool) or not isinstance(answer_duration_value, int | float):
            return None
        try:
            answer_duration_seconds: float = float(answer_duration_value)
        except OverflowError:
            return None
        # json.loads reads NaN and Infinity; NaN fails the comparison.
        return answer_duration_seconds if 0 <= answer_duration_seconds < math.inf else None

    @staticmethod
    def _read_text_file(file_path: Path) -> str:
        try:
            return file_path.read_text(encoding=TEXT_ENCODING)
        except UnicodeDecodeError as not_utf8_text:
            raise RecordedRunFileNotUtf8Exception(file_path, str(not_utf8_text)) from not_utf8_text
        except OSError as read_failure:
            raise RecordedRunFileReadFailedException(file_path, str(read_failure)) from read_failure
