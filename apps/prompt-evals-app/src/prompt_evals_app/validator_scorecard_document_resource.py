import json
import math
from pathlib import Path
from typing import Final, cast, final

from prompt_evals_app.scorecard_document_resources import (
    DurationRangeResource,
    ScorecardDocumentResource,
    ScorecardRowResource,
    VariantTimingResource,
)
from prompt_evals_app.scorecard_summary_unreadable_error import ScorecardSummaryUnreadableError

type JsonObject = dict[str, object]

CODING_ASSISTANT_FIELD: Final[str] = "coding_assistant"
MODEL_NAME_FIELD: Final[str] = "model_name"
EFFORT_LEVEL_FIELD: Final[str] = "effort_level"
PASSES_GATE_FIELD: Final[str] = "passes_gate"
SCORECARD_ROWS_FIELD: Final[str] = "scorecard_rows"
SCORECARD_TIMING_FIELD: Final[str] = "scorecard_timing"
VARIANT_TIMINGS_FIELD: Final[str] = "variant_timings"
CHECK_NAME_FIELD: Final[str] = "check_name"
VARIANT_NAME_FIELD: Final[str] = "variant_name"
TRIAL_COUNT_FIELD: Final[str] = "trial_count"
PASSED_COUNT_FIELD: Final[str] = "passed_count"
ERRORED_COUNT_FIELD: Final[str] = "errored_count"
IS_GATED_FIELD: Final[str] = "is_gated"
MINIMUM_MET_FIELD: Final[str] = "meets_minimum_pass_rate"
ANSWER_DURATION_SUMMARY_FIELD: Final[str] = "answer_duration_summary"
GRADING_DURATION_SUMMARY_FIELD: Final[str] = "grading_duration_summary"
TOTAL_DURATION_SUMMARY_FIELD: Final[str] = "total_duration_summary"
MEDIAN_SECONDS_FIELD: Final[str] = "median_seconds"
MINIMUM_SECONDS_FIELD: Final[str] = "minimum_seconds"
MAXIMUM_SECONDS_FIELD: Final[str] = "maximum_seconds"
MEASURED_TRIAL_COUNT_FIELD: Final[str] = "measured_trial_count"
# Scorecards written before the assistant was recorded all came from Claude Code runs.
LEGACY_CODING_ASSISTANT: Final[str] = "claude_code"


@final
class ValidatorScorecardDocumentResource:
    """Turns a scorecard.json (foreign data on disk) into typed resources, or refuses it naming the file, field and value.

    Only the fields the comparison reads are validated; every other field is ignored.
    """

    @staticmethod
    def parse_scorecard_document(scorecard_text: str, scorecard_path: Path) -> ScorecardDocumentResource:
        scorecard_object: JsonObject = ValidatorScorecardDocumentResource._parse_json_object(scorecard_text, scorecard_path)
        return ScorecardDocumentResource(
            coding_assistant=ValidatorScorecardDocumentResource._read_string(
                scorecard_object, CODING_ASSISTANT_FIELD, scorecard_path, LEGACY_CODING_ASSISTANT
            ),
            model_name=ValidatorScorecardDocumentResource._read_string(scorecard_object, MODEL_NAME_FIELD, scorecard_path),
            effort_level=ValidatorScorecardDocumentResource._read_string(scorecard_object, EFFORT_LEVEL_FIELD, scorecard_path),
            passes_gate=ValidatorScorecardDocumentResource._read_bool(scorecard_object, PASSES_GATE_FIELD, scorecard_path),
            scorecard_rows=tuple(
                ValidatorScorecardDocumentResource._parse_scorecard_row(scorecard_row, scorecard_path)
                for scorecard_row in ValidatorScorecardDocumentResource._read_object_list(scorecard_object, SCORECARD_ROWS_FIELD, scorecard_path)
            ),
            variant_timings=ValidatorScorecardDocumentResource._parse_variant_timings(scorecard_object, scorecard_path),
        )

    @staticmethod
    def _parse_json_object(scorecard_text: str, scorecard_path: Path) -> JsonObject:
        try:
            scorecard_document: object = json.loads(scorecard_text)
        except json.JSONDecodeError as invalid_scorecard:
            raise ScorecardSummaryUnreadableError(f"{scorecard_path} is not valid JSON: {invalid_scorecard}") from invalid_scorecard
        if not isinstance(scorecard_document, dict):
            raise ScorecardSummaryUnreadableError(f"{scorecard_path} must hold a JSON object; it holds {type(scorecard_document).__name__}")
        return cast(JsonObject, scorecard_document)

    @staticmethod
    def _parse_scorecard_row(scorecard_row: JsonObject, scorecard_path: Path) -> ScorecardRowResource:
        return ScorecardRowResource(
            check_name=ValidatorScorecardDocumentResource._read_string(scorecard_row, CHECK_NAME_FIELD, scorecard_path),
            variant_name=ValidatorScorecardDocumentResource._read_string(scorecard_row, VARIANT_NAME_FIELD, scorecard_path),
            trial_count=ValidatorScorecardDocumentResource._read_count(scorecard_row, TRIAL_COUNT_FIELD, scorecard_path),
            passed_count=ValidatorScorecardDocumentResource._read_count(scorecard_row, PASSED_COUNT_FIELD, scorecard_path),
            errored_count=ValidatorScorecardDocumentResource._read_count(scorecard_row, ERRORED_COUNT_FIELD, scorecard_path),
            is_gated=ValidatorScorecardDocumentResource._read_bool(scorecard_row, IS_GATED_FIELD, scorecard_path),
            meets_minimum_pass_rate=ValidatorScorecardDocumentResource._read_bool(scorecard_row, MINIMUM_MET_FIELD, scorecard_path),
        )

    @staticmethod
    def _parse_variant_timings(scorecard_object: JsonObject, scorecard_path: Path) -> tuple[VariantTimingResource, ...]:
        # Scorecards written before timing was recorded have no scorecard_timing; their times show as not recorded.
        if scorecard_object.get(SCORECARD_TIMING_FIELD) is None:
            return ()
        scorecard_timing: JsonObject = ValidatorScorecardDocumentResource._read_object(scorecard_object, SCORECARD_TIMING_FIELD, scorecard_path)
        return tuple(
            ValidatorScorecardDocumentResource._parse_variant_timing(variant_timing, scorecard_path)
            for variant_timing in ValidatorScorecardDocumentResource._read_object_list(scorecard_timing, VARIANT_TIMINGS_FIELD, scorecard_path)
        )

    @staticmethod
    def _parse_variant_timing(variant_timing: JsonObject, scorecard_path: Path) -> VariantTimingResource:
        return VariantTimingResource(
            variant_name=ValidatorScorecardDocumentResource._read_string(variant_timing, VARIANT_NAME_FIELD, scorecard_path),
            answer_duration_range=ValidatorScorecardDocumentResource._parse_duration_range(
                variant_timing, ANSWER_DURATION_SUMMARY_FIELD, scorecard_path
            ),
            grading_duration_range=ValidatorScorecardDocumentResource._parse_duration_range(
                variant_timing, GRADING_DURATION_SUMMARY_FIELD, scorecard_path
            ),
            total_duration_range=ValidatorScorecardDocumentResource._parse_duration_range(
                variant_timing, TOTAL_DURATION_SUMMARY_FIELD, scorecard_path
            ),
        )

    @staticmethod
    def _parse_duration_range(variant_timing: JsonObject, summary_field: str, scorecard_path: Path) -> DurationRangeResource | None:
        if variant_timing.get(summary_field) is None:
            return None
        duration_summary: JsonObject = ValidatorScorecardDocumentResource._read_object(variant_timing, summary_field, scorecard_path)
        return DurationRangeResource(
            median_seconds=ValidatorScorecardDocumentResource._read_seconds(duration_summary, MEDIAN_SECONDS_FIELD, scorecard_path),
            minimum_seconds=ValidatorScorecardDocumentResource._read_seconds(duration_summary, MINIMUM_SECONDS_FIELD, scorecard_path),
            maximum_seconds=ValidatorScorecardDocumentResource._read_seconds(duration_summary, MAXIMUM_SECONDS_FIELD, scorecard_path),
            measured_trial_count=ValidatorScorecardDocumentResource._read_count(duration_summary, MEASURED_TRIAL_COUNT_FIELD, scorecard_path),
        )

    @staticmethod
    def _read_object(json_object: JsonObject, field_name: str, scorecard_path: Path) -> JsonObject:
        field_value: object = json_object.get(field_name)
        if not isinstance(field_value, dict):
            raise ScorecardSummaryUnreadableError(f"{scorecard_path}: {field_name} must be a JSON object; it holds {field_value!r}")
        return cast(JsonObject, field_value)

    @staticmethod
    def _read_object_list(json_object: JsonObject, field_name: str, scorecard_path: Path) -> list[JsonObject]:
        field_value: object = json_object.get(field_name)
        if not isinstance(field_value, list) or not all(isinstance(list_item, dict) for list_item in cast(list[object], field_value)):
            raise ScorecardSummaryUnreadableError(f"{scorecard_path}: {field_name} must be a list of JSON objects; it holds {field_value!r}")
        return cast(list[JsonObject], field_value)

    @staticmethod
    def _read_string(json_object: JsonObject, field_name: str, scorecard_path: Path, default_value: str | None = None) -> str:
        field_value: object = json_object.get(field_name, default_value)
        if not isinstance(field_value, str):
            raise ScorecardSummaryUnreadableError(f"{scorecard_path}: {field_name} must be a string; it holds {field_value!r}")
        return field_value

    @staticmethod
    def _read_bool(json_object: JsonObject, field_name: str, scorecard_path: Path) -> bool:
        field_value: object = json_object.get(field_name)
        if not isinstance(field_value, bool):
            raise ScorecardSummaryUnreadableError(f"{scorecard_path}: {field_name} must be true or false; it holds {field_value!r}")
        return field_value

    @staticmethod
    def _read_count(json_object: JsonObject, field_name: str, scorecard_path: Path) -> int:
        field_value: object = json_object.get(field_name)
        # bool is a subclass of int, so true would otherwise read as a count of one.
        if isinstance(field_value, bool) or not isinstance(field_value, int) or field_value < 0:
            raise ScorecardSummaryUnreadableError(f"{scorecard_path}: {field_name} must be a whole number of zero or more; it holds {field_value!r}")
        return field_value

    @staticmethod
    def _read_seconds(json_object: JsonObject, field_name: str, scorecard_path: Path) -> float:
        field_value: object = json_object.get(field_name)
        unreadable_message: str = f"{scorecard_path}: {field_name} must be a finite number of seconds of zero or more; it holds {field_value!r}"
        if isinstance(field_value, bool) or not isinstance(field_value, int | float):
            raise ScorecardSummaryUnreadableError(unreadable_message)
        try:
            seconds: float = float(field_value)
        except OverflowError as too_large_value:
            raise ScorecardSummaryUnreadableError(unreadable_message) from too_large_value
        # json.loads reads NaN and Infinity; NaN fails the comparison.
        if not 0 <= seconds < math.inf:
            raise ScorecardSummaryUnreadableError(unreadable_message)
        return seconds
