import json
import math
import re
from pathlib import Path
from typing import Final

import pytest

from prompt_evals import (
    CodingAssistant,
    EffortLevel,
    PromptEvalsBusinessBaseException,
    PromptEvalsTechnicalBaseException,
    RecordedCompletedTrial,
    TrialIdentity,
)
from prompt_evals_app.recorded_run_exceptions import (
    RecordedRunFileNotUtf8Exception,
    RecordedRunFileReadFailedException,
    RecordedRunScorecardMissingException,
    RecordedRunSettingsNotTextException,
    RecordedRunSettingUnknownException,
    RecordedTrialAnswerDurationInvalidException,
)
from prompt_evals_app.recorded_run_reader import RecordedRun, RecordedRunReader

INVALID_UTF8_BYTES: Final[bytes] = b"\xff\xfe\xfa"
TRIAL_DIRECTORY_PARTS: Final[tuple[str, ...]] = ("trials", "standard", "refund", "run-07")


def write_run_directory(run_directory: Path, scorecard_object: dict[str, object]) -> Path:
    (run_directory / "scorecard.json").write_text(json.dumps(scorecard_object), encoding="utf-8")
    trial_directory: Path = run_directory.joinpath(*TRIAL_DIRECTORY_PARTS)
    trial_directory.mkdir(parents=True)
    (trial_directory / "event_stream.jsonl").write_text("{}\n", encoding="utf-8")
    return trial_directory


def create_valid_scorecard_object() -> dict[str, object]:
    return {"coding_assistant": CodingAssistant.CLAUDE_CODE.value, "model_name": "sonnet", "effort_level": EffortLevel.LOW.value}


class TestRecordedRunReader:
    def test_ReadRecordedRun_WhenRunDirectoryIsValid_ThenTrialIdentityComesFromTheFolderLayout(self, tmp_path: Path) -> None:
        # Arrange
        trial_directory: Path = write_run_directory(tmp_path, create_valid_scorecard_object())
        (trial_directory.parent / "notes").mkdir()
        expected_trial_identity: TrialIdentity = TrialIdentity(variant_name="standard", case_name="refund", repetition_number=7)

        # Act
        actual_recorded_run: RecordedRun = RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_trial_identities: list[TrialIdentity] = [recorded_trial.trial_identity for recorded_trial in actual_recorded_run.recorded_trials]
        assert actual_trial_identities == [expected_trial_identity], (
            f"expected only the run-07 trial {expected_trial_identity}; actual {actual_trial_identities}"
        )
        assert isinstance(actual_recorded_run.recorded_trials[0], RecordedCompletedTrial), (
            f"expected a completed trial; actual {actual_recorded_run.recorded_trials[0]!r}"
        )

    def test_ReadRecordedRun_WhenEventStreamIsNotUtf8_ThenRunIsUnreadable(self, tmp_path: Path) -> None:
        # Arrange
        trial_directory: Path = write_run_directory(tmp_path, create_valid_scorecard_object())
        (trial_directory / "event_stream.jsonl").write_bytes(INVALID_UTF8_BYTES)

        # Act / Assert
        with pytest.raises(RecordedRunFileNotUtf8Exception, match=re.escape("event_stream.jsonl is not UTF-8 text")):
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

    def test_ReadRecordedRun_WhenScorecardIsNotUtf8_ThenRunIsUnreadable(self, tmp_path: Path) -> None:
        # Arrange
        write_run_directory(tmp_path, create_valid_scorecard_object())
        (tmp_path / "scorecard.json").write_bytes(INVALID_UTF8_BYTES)

        # Act / Assert
        with pytest.raises(RecordedRunFileNotUtf8Exception, match=re.escape("scorecard.json is not UTF-8 text")):
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

    def test_ReadRecordedRun_WhenEffortLevelIsNotAString_ThenMessageNamesOnlyThatField(self, tmp_path: Path) -> None:
        # Arrange
        scorecard_object: dict[str, object] = create_valid_scorecard_object()
        scorecard_object["effort_level"] = 3
        write_run_directory(tmp_path, scorecard_object)

        # Act
        with pytest.raises(RecordedRunSettingsNotTextException) as raised_error:
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_message: str = str(raised_error.value)
        actual_named_fields: list[str] = [
            field_name for field_name in ("coding_assistant", "model_name", "effort_level") if f"{field_name}=" in actual_message
        ]
        assert actual_named_fields == ["effort_level"], f"expected the message to name only effort_level; actual {actual_message!r}"
        assert "effort_level=3" in actual_message, f"expected the message to show the rejected value 3; actual {actual_message!r}"

    def test_ReadRecordedRun_WhenEffortLevelIsUnknown_ThenMessageListsKnownEffortLevels(self, tmp_path: Path) -> None:
        # Arrange
        scorecard_object: dict[str, object] = create_valid_scorecard_object()
        scorecard_object["effort_level"] = "turbo"
        write_run_directory(tmp_path, scorecard_object)

        # Act
        with pytest.raises(RecordedRunSettingUnknownException) as raised_error:
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_message: str = str(raised_error.value)
        missing_effort_levels: list[str] = [effort_level.value for effort_level in EffortLevel if f"'{effort_level.value}'" not in actual_message]
        assert "turbo" in actual_message, f"expected the message to name the rejected value 'turbo'; actual {actual_message!r}"
        assert not missing_effort_levels, (
            f"expected the message to list every known effort level; missing {missing_effort_levels} in {actual_message!r}"
        )

    def test_ReadRecordedRun_WhenTheTrialSavedAnAnswerTime_ThenTheRecordedTrialCarriesIt(self, tmp_path: Path) -> None:
        # Arrange
        trial_directory: Path = write_run_directory(tmp_path, create_valid_scorecard_object())
        expected_answer_duration_seconds: float = 93.25
        (trial_directory / "timing.json").write_text(json.dumps({"answer_duration_seconds": expected_answer_duration_seconds}), encoding="utf-8")

        # Act
        actual_recorded_run: RecordedRun = RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_answer_duration_seconds: float | None = actual_recorded_run.recorded_trials[0].answer_duration_seconds
        assert actual_answer_duration_seconds == expected_answer_duration_seconds, (
            f"expected {expected_answer_duration_seconds}s from timing.json; actual {actual_answer_duration_seconds}"
        )

    def test_ReadRecordedRun_WhenTheTrialSavedNoTimingFile_ThenItsAnswerTimeIsUnknown(self, tmp_path: Path) -> None:
        # Arrange
        write_run_directory(tmp_path, create_valid_scorecard_object())

        # Act
        actual_recorded_run: RecordedRun = RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_answer_duration_seconds: float | None = actual_recorded_run.recorded_trials[0].answer_duration_seconds
        assert actual_answer_duration_seconds is None, f"expected no answer time without timing.json; actual {actual_answer_duration_seconds}"

    @pytest.mark.parametrize("invalid_answer_duration", [-1, True, "12", math.nan, math.inf, 10**400])
    def test_ReadRecordedRun_WhenTheSavedAnswerTimeIsNotASecondsCount_ThenRunIsUnreadable(
        self, tmp_path: Path, invalid_answer_duration: object
    ) -> None:
        # Arrange
        trial_directory: Path = write_run_directory(tmp_path, create_valid_scorecard_object())
        (trial_directory / "timing.json").write_text(json.dumps({"answer_duration_seconds": invalid_answer_duration}), encoding="utf-8")

        # Act / Assert
        with pytest.raises(
            RecordedTrialAnswerDurationInvalidException,
            match=re.escape("must hold a finite number of seconds of zero or more, or null, for answer_duration_seconds"),
        ):
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

    def test_ReadRecordedRun_WhenTheFolderHasNoScorecard_ThenTheCallerIsToldItIsNotARunThisAppWrote(self, tmp_path: Path) -> None:
        # Arrange
        write_run_directory(tmp_path, create_valid_scorecard_object())
        (tmp_path / "scorecard.json").unlink()
        expected_is_business: bool = True

        # Act
        with pytest.raises(RecordedRunScorecardMissingException, match=re.escape("scorecard.json does not exist")) as raised_error:
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_is_business: bool = isinstance(raised_error.value, PromptEvalsBusinessBaseException)
        assert actual_is_business == expected_is_business, "a folder that is not a run is the caller's to correct, so it must be a business exception"

    def test_ReadRecordedRun_WhenTheOperatingSystemCannotReadAFile_ThenItIsATechnicalFailure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        trial_directory: Path = write_run_directory(tmp_path, create_valid_scorecard_object())
        event_stream_path: Path = trial_directory / "event_stream.jsonl"
        expected_read_error: str = "access is denied"
        expected_is_technical: bool = True
        original_read_text = Path.read_text

        def read_text_denied_for_event_stream(file_path: Path, *arguments: object, **keyword_arguments: object) -> str:
            if file_path == event_stream_path:
                raise PermissionError(expected_read_error)
            return original_read_text(file_path, *arguments, **keyword_arguments)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", read_text_denied_for_event_stream)

        # Act
        with pytest.raises(RecordedRunFileReadFailedException, match=re.escape(expected_read_error)) as raised_error:
            RecordedRunReader.read_recorded_run(tmp_path, CodingAssistant.CLAUDE_CODE)

        # Assert
        actual_is_technical: bool = isinstance(raised_error.value, PromptEvalsTechnicalBaseException)
        assert actual_is_technical == expected_is_technical, "a file the operating system cannot read is ours to fix, so it must be technical"
