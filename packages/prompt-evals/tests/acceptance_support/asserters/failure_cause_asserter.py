from dataclasses import dataclass

from prompt_evals import FailureCause


@dataclass(frozen=True)
class ExpectedFailureCause:
    occurrence_count: int
    cause_summary_phrases: tuple[str, ...]


class FailureCauseAsserter:
    """Compares the expected failure causes with the scorecard's, in order, and reports every mismatch at once."""

    @staticmethod
    def assert_expected_and_actual_are_equal(
        expected_failure_causes: tuple[ExpectedFailureCause, ...], actual_failure_causes: tuple[FailureCause, ...]
    ) -> None:
        mismatches: list[str] = []
        if len(actual_failure_causes) != len(expected_failure_causes):
            mismatches.append(
                f"failure cause count: expected {len(expected_failure_causes)}, actual {len(actual_failure_causes)}: {actual_failure_causes}"
            )
        cause_number: int
        expected_failure_cause: ExpectedFailureCause
        actual_failure_cause: FailureCause
        for cause_number, (expected_failure_cause, actual_failure_cause) in enumerate(
            zip(expected_failure_causes, actual_failure_causes, strict=False), start=1
        ):
            mismatches.extend(FailureCauseAsserter._find_cause_mismatches(cause_number, expected_failure_cause, actual_failure_cause))
        assert not mismatches, f"Failure cause mismatches ({len(mismatches)}):\n" + "\n".join(mismatches)

    @staticmethod
    def _find_cause_mismatches(cause_number: int, expected_failure_cause: ExpectedFailureCause, actual_failure_cause: FailureCause) -> list[str]:
        cause_label: str = f"failure cause {cause_number}"
        cause_mismatches: list[str] = []
        actual_occurrence_count: int = len(actual_failure_cause.occurrence_labels)
        if actual_occurrence_count != expected_failure_cause.occurrence_count:
            cause_mismatches.append(
                f"{cause_label} occurrences: expected {expected_failure_cause.occurrence_count}, "
                f"actual {actual_occurrence_count}: {actual_failure_cause.occurrence_labels}"
            )
        cause_mismatches.extend(
            f"{cause_label} summary: expected to mention {cause_summary_phrase!r}, actual {actual_failure_cause.cause_summary!r}"
            for cause_summary_phrase in expected_failure_cause.cause_summary_phrases
            if cause_summary_phrase not in actual_failure_cause.cause_summary
        )
        return cause_mismatches
