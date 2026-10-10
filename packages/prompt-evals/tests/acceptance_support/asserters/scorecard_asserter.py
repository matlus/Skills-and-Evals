from dataclasses import dataclass

from prompt_evals import ScorecardRow


@dataclass(frozen=True)
class ExpectedScorecardRow:
    check_name: str
    variant_name: str
    trial_count: int
    passed_count: int
    errored_count: int
    meets_minimum_pass_rate: bool
    failure_reason_phrases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpectedScorecard:
    passes_gate: bool
    expected_scorecard_rows: tuple[ExpectedScorecardRow, ...]


@dataclass(frozen=True)
class ScorecardRowOutcome:
    """The part of a row this asserter compares; the row's identity is its (check name, variant name) key."""

    trial_count: int
    passed_count: int
    errored_count: int
    meets_minimum_pass_rate: bool
    failure_reasons: tuple[str, ...]


type ScorecardRowKey = tuple[str, str]


class ScorecardAsserter:
    """Compares the whole expected scorecard with the actual one and reports every mismatch at once."""

    @staticmethod
    def assert_expected_and_actual_are_equal(
        expected_scorecard: ExpectedScorecard, actual_passes_gate: bool, actual_scorecard_rows: tuple[ScorecardRow, ...]
    ) -> None:
        mismatches: list[str] = []
        if expected_scorecard.passes_gate != actual_passes_gate:
            mismatches.append(f"passes_gate: expected {expected_scorecard.passes_gate}, actual {actual_passes_gate}")
        actual_scorecard_row_outcome_by_row_key: dict[ScorecardRowKey, ScorecardRowOutcome] = {
            (actual_scorecard_row.check_name, actual_scorecard_row.variant_name): ScorecardAsserter._map_to_row_outcome(actual_scorecard_row)
            for actual_scorecard_row in actual_scorecard_rows
        }
        mismatches.extend(
            ScorecardAsserter._find_row_key_mismatches(
                [
                    (expected_scorecard_row.check_name, expected_scorecard_row.variant_name)
                    for expected_scorecard_row in expected_scorecard.expected_scorecard_rows
                ],
                [(actual_scorecard_row.check_name, actual_scorecard_row.variant_name) for actual_scorecard_row in actual_scorecard_rows],
            )
        )
        for expected_scorecard_row in expected_scorecard.expected_scorecard_rows:
            actual_scorecard_row_outcome: ScorecardRowOutcome | None = actual_scorecard_row_outcome_by_row_key.get(
                (expected_scorecard_row.check_name, expected_scorecard_row.variant_name)
            )
            if actual_scorecard_row_outcome is not None:
                mismatches.extend(ScorecardAsserter._find_row_mismatches(expected_scorecard_row, actual_scorecard_row_outcome))
        assert not mismatches, f"Scorecard mismatches ({len(mismatches)}):\n" + "\n".join(mismatches)

    @staticmethod
    def _map_to_row_outcome(actual_scorecard_row: ScorecardRow) -> ScorecardRowOutcome:
        return ScorecardRowOutcome(
            trial_count=actual_scorecard_row.trial_count,
            passed_count=actual_scorecard_row.passed_count,
            errored_count=actual_scorecard_row.errored_count,
            meets_minimum_pass_rate=actual_scorecard_row.meets_minimum_pass_rate,
            failure_reasons=actual_scorecard_row.failure_reasons,
        )

    @staticmethod
    def _find_row_key_mismatches(expected_row_keys: list[ScorecardRowKey], actual_row_keys: list[ScorecardRowKey]) -> list[str]:
        if expected_row_keys == actual_row_keys:
            return []
        missing_row_keys: list[ScorecardRowKey] = [row_key for row_key in expected_row_keys if row_key not in actual_row_keys]
        unexpected_row_keys: list[ScorecardRowKey] = [row_key for row_key in actual_row_keys if row_key not in expected_row_keys]
        row_key_mismatch: str = (
            f"rows (check, variant): missing {missing_row_keys}, unexpected {unexpected_row_keys}; "
            f"expected order {expected_row_keys}, actual order {actual_row_keys}"
        )
        return [row_key_mismatch]

    @staticmethod
    def _find_row_mismatches(expected_scorecard_row: ExpectedScorecardRow, actual_scorecard_row_outcome: ScorecardRowOutcome) -> list[str]:
        row_label: str = f"{expected_scorecard_row.check_name}/{expected_scorecard_row.variant_name}"
        expected_row_tally: tuple[int, int, int, bool] = (
            expected_scorecard_row.trial_count,
            expected_scorecard_row.passed_count,
            expected_scorecard_row.errored_count,
            expected_scorecard_row.meets_minimum_pass_rate,
        )
        actual_row_tally: tuple[int, int, int, bool] = (
            actual_scorecard_row_outcome.trial_count,
            actual_scorecard_row_outcome.passed_count,
            actual_scorecard_row_outcome.errored_count,
            actual_scorecard_row_outcome.meets_minimum_pass_rate,
        )
        row_mismatches: list[str] = []
        if expected_row_tally != actual_row_tally:
            row_mismatches.append(f"{row_label} (trials, passed, errored, meets minimum): expected {expected_row_tally}, actual {actual_row_tally}")
        expected_failure_reason_count: int = expected_scorecard_row.trial_count - expected_scorecard_row.passed_count
        actual_failure_reason_count: int = len(actual_scorecard_row_outcome.failure_reasons)
        if actual_failure_reason_count != expected_failure_reason_count:
            row_mismatches.append(
                f"{row_label} failure reasons (one per trial that did not pass): expected {expected_failure_reason_count}, "
                f"actual {actual_failure_reason_count}"
            )
        actual_failure_reasons: str = "\n".join(actual_scorecard_row_outcome.failure_reasons)
        row_mismatches.extend(
            f"{row_label}: failure reasons expected to mention {failure_reason_phrase!r}, actual {actual_failure_reasons!r}"
            for failure_reason_phrase in expected_scorecard_row.failure_reason_phrases
            if failure_reason_phrase not in actual_failure_reasons
        )
        return row_mismatches
