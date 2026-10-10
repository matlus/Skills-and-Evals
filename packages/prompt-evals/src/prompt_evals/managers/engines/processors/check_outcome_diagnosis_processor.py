import dataclasses
from decimal import Decimal
from typing import final

from prompt_evals.managers.engines.processors.diagnosis_processors.amount_discrepancy_diagnosis_processor import AmountDiscrepancyDiagnosisProcessor
from prompt_evals.managers.engines.processors.fact_check_processors.amount_text_processor import AmountTextProcessor
from prompt_evals.managers.models.diagnosis_models import AmountDiscrepancyDiagnosis, DiscrepancyExplanation, DisputedAmount, EntryMistakeKind
from prompt_evals.managers.models.grading_models import (
    CheckOutcome,
    CheckStatus,
    FactExtractionAttempt,
    JudgmentAttempt,
    SucceededFactExtraction,
    SucceededJudgment,
)
from prompt_evals.managers.models.reference_ledger_models import LedgerBucketTotals, ReferenceLedger


@final
class CheckOutcomeDiagnosisProcessor:
    """Adds the likely cause to a failed check whose wrong totals can be traced in the case's reference ledger.
    A passed or errored check, or a case without a ledger, is returned unchanged."""

    @staticmethod
    def diagnose_amount_check_outcome(
        check_outcome: CheckOutcome, fact_name: str, fact_extraction_attempt: FactExtractionAttempt, reference_ledger: ReferenceLedger | None
    ) -> CheckOutcome:
        match fact_extraction_attempt:
            case SucceededFactExtraction(extracted_facts=extracted_facts) if (
                check_outcome.check_status == CheckStatus.FAILED and reference_ledger is not None
            ):
                return CheckOutcomeDiagnosisProcessor._diagnose_reported_value(
                    check_outcome,
                    extracted_facts.read_reported_value(fact_name),
                    # Each amount fact names at most one bucket; a fact the ledger does not total cannot be traced.
                    reference_ledger.ledger_bucket_totals_by_fact_name.get(fact_name),
                    reference_ledger,
                )
            case _:
                return check_outcome

    @staticmethod
    def diagnose_judge_check_outcome(
        check_outcome: CheckOutcome, judgment_attempt: JudgmentAttempt, reference_ledger: ReferenceLedger | None
    ) -> CheckOutcome:
        match judgment_attempt:
            case SucceededJudgment(judge_verdict=judge_verdict) if check_outcome.check_status == CheckStatus.FAILED and reference_ledger is not None:
                # The judge only quotes the amounts it disputes; code traces them in the ledger, so the stated cause is not a model's guess.
                amount_discrepancy_diagnoses: list[AmountDiscrepancyDiagnosis] = [
                    amount_discrepancy_diagnosis
                    for disputed_amount in judge_verdict.disputed_amounts
                    for amount_discrepancy_diagnosis in CheckOutcomeDiagnosisProcessor._diagnose_disputed_amount(disputed_amount, reference_ledger)
                ]
                return dataclasses.replace(
                    check_outcome, amount_discrepancy_diagnoses=CheckOutcomeDiagnosisProcessor._remove_repeated_causes(amount_discrepancy_diagnoses)
                )
            case _:
                return check_outcome

    @staticmethod
    def _diagnose_reported_value(
        check_outcome: CheckOutcome, reported_value: str | None, ledger_bucket_totals: LedgerBucketTotals | None, reference_ledger: ReferenceLedger
    ) -> CheckOutcome:
        reported_amount: Decimal | None = None if reported_value is None else AmountTextProcessor.parse_reported_amount(reported_value)
        if reported_amount is None or ledger_bucket_totals is None:
            return check_outcome
        return dataclasses.replace(
            check_outcome,
            amount_discrepancy_diagnoses=(
                AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(reference_ledger.ledger_entries, ledger_bucket_totals, reported_amount),
            ),
        )

    @staticmethod
    def _remove_repeated_causes(amount_discrepancy_diagnoses: list[AmountDiscrepancyDiagnosis]) -> tuple[AmountDiscrepancyDiagnosis, ...]:
        # A finding that quotes both a month and the whole period carries one mistake into both totals. The month names it
        # more precisely, so it is kept and the period-wide repeat of the same entry mistakes is dropped.
        amount_discrepancy_diagnoses.sort(key=lambda amount_discrepancy_diagnosis: amount_discrepancy_diagnosis.ledger_bucket.period is None)
        kept_amount_discrepancy_diagnoses: list[AmountDiscrepancyDiagnosis] = []
        kept_entry_mistake_identities: list[frozenset[tuple[int, EntryMistakeKind]]] = []
        for amount_discrepancy_diagnosis in amount_discrepancy_diagnoses:
            entry_mistake_identities: frozenset[tuple[int, EntryMistakeKind]] = CheckOutcomeDiagnosisProcessor._collect_first_explanation_mistakes(
                amount_discrepancy_diagnosis.discrepancy_explanations
            )
            if entry_mistake_identities and entry_mistake_identities in kept_entry_mistake_identities:
                continue
            kept_amount_discrepancy_diagnoses.append(amount_discrepancy_diagnosis)
            kept_entry_mistake_identities.append(entry_mistake_identities)
        return tuple(kept_amount_discrepancy_diagnoses)

    @staticmethod
    def _collect_first_explanation_mistakes(discrepancy_explanations: tuple[DiscrepancyExplanation, ...]) -> frozenset[tuple[int, EntryMistakeKind]]:
        if not discrepancy_explanations:
            return frozenset()
        return frozenset(
            (entry_mistake.ledger_entry.line_number, entry_mistake.entry_mistake_kind) for entry_mistake in discrepancy_explanations[0].entry_mistakes
        )

    @staticmethod
    def _diagnose_disputed_amount(disputed_amount: DisputedAmount, reference_ledger: ReferenceLedger) -> tuple[AmountDiscrepancyDiagnosis, ...]:
        # The judge names the reference value it compared against; the ledger bucket with that total is what the answer got wrong.
        # A reference value that is no single bucket's total (a percentage, a sum across categories) cannot be traced.
        answer_amount: Decimal | None = AmountTextProcessor.parse_quoted_amount(disputed_amount.answer_amount_text)
        reference_amount: Decimal | None = AmountTextProcessor.parse_quoted_amount(disputed_amount.reference_amount_text)
        if answer_amount is None or reference_amount is None:
            return ()
        ledger_bucket_totals: LedgerBucketTotals | None = AmountDiscrepancyDiagnosisProcessor.find_ledger_bucket_with_reference_amount(
            reference_ledger.ledger_bucket_totals, reference_amount, disputed_amount.description
        )
        if ledger_bucket_totals is None:
            return ()
        return (AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(reference_ledger.ledger_entries, ledger_bucket_totals, answer_amount),)
