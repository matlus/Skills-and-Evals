import re
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, final

from prompt_evals.managers.exceptions.eval_suite_exceptions import EvalSuiteValidationException
from prompt_evals.managers.models.eval_suite_models import (
    AmountCheckDefinition,
    CheckDefinition,
    EvalCase,
    EvalSuite,
    FactValueCheckDefinition,
    ToolUseCheckDefinition,
)
from prompt_evals.managers.models.reference_ledger_models import LedgerBucketTotals, ReferenceLedger

# Hosts use variant and case names as folder names; they must be portable and unable to escape a run folder.
# Windows strips a trailing '.', so "refund." and "refund" would share one folder; a name must end in a letter, digit, '_' or '-'.
SAFE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?$")
# Windows cannot create a folder named after a device, with or without an extension (for example "NUL" or "con.txt").
RESERVED_WINDOWS_DEVICE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.IGNORECASE)
SAFE_NAME_RULE: Final[str] = (
    "may contain only letters, digits, '.', '_' and '-', must start with a letter or digit, must not end with '.', "
    "and must not be a reserved Windows device name such as 'NUL'"
)


@final
class ValidatorEvalSuite:
    """Cross-reference rules that no single file can check on its own."""

    VARIANT_NAME_KIND: Final[str] = "variant"
    CASE_NAME_KIND: Final[str] = "case"
    CHECK_NAME_KIND: Final[str] = "check"

    @staticmethod
    def validate(eval_suite: EvalSuite, schema_fact_names: tuple[str, ...], eval_suite_directory: Path) -> None:
        definition_problems: list[str] = [
            *ValidatorEvalSuite._find_name_problems(eval_suite),
            *ValidatorEvalSuite._find_gated_variant_problems(eval_suite),
            *ValidatorEvalSuite._find_empty_expected_fact_problems(eval_suite),
            *(
                reference_ledger_problem
                for eval_case in eval_suite.eval_cases
                if eval_case.reference_ledger is not None
                for reference_ledger_problem in ValidatorEvalSuite._find_reference_ledger_problems(eval_case, eval_case.reference_ledger)
            ),
            *(
                check_problem
                for check_definition in eval_suite.check_definitions
                for check_problem in ValidatorEvalSuite._find_check_problems(check_definition, schema_fact_names, eval_suite)
            ),
        ]
        if definition_problems:
            raise EvalSuiteValidationException(eval_suite_directory, definition_problems)

    @staticmethod
    def _find_name_problems(eval_suite: EvalSuite) -> list[str]:
        variant_names: list[str] = [prompt_variant.variant_name for prompt_variant in eval_suite.prompt_variants]
        case_names: list[str] = [eval_case.case_name for eval_case in eval_suite.eval_cases]
        check_names: list[str] = [check_definition.check_name for check_definition in eval_suite.check_definitions]
        return [
            *ValidatorEvalSuite._find_duplicate_names(ValidatorEvalSuite.VARIANT_NAME_KIND, variant_names),
            *ValidatorEvalSuite._find_duplicate_names(ValidatorEvalSuite.CASE_NAME_KIND, case_names),
            *ValidatorEvalSuite._find_duplicate_names(ValidatorEvalSuite.CHECK_NAME_KIND, check_names),
            *ValidatorEvalSuite._find_unsafe_names(ValidatorEvalSuite.VARIANT_NAME_KIND, variant_names),
            *ValidatorEvalSuite._find_unsafe_names(ValidatorEvalSuite.CASE_NAME_KIND, case_names),
        ]

    @staticmethod
    def _find_gated_variant_problems(eval_suite: EvalSuite) -> list[str]:
        if not eval_suite.gated_variant_names:
            return ["gated_variant_names must name at least one variant; otherwise no run can pass or fail the gate"]
        variant_names: set[str] = {prompt_variant.variant_name for prompt_variant in eval_suite.prompt_variants}
        return [
            f"gated variant '{gated_variant_name}' is not a defined prompt variant"
            for gated_variant_name in eval_suite.gated_variant_names
            if gated_variant_name not in variant_names
        ]

    @staticmethod
    def _find_check_problems(check_definition: CheckDefinition, schema_fact_names: tuple[str, ...], eval_suite: EvalSuite) -> list[str]:
        match check_definition:
            case AmountCheckDefinition(check_name=check_name, fact_name=fact_name):
                return [
                    *ValidatorEvalSuite._find_fact_reference_problems(check_name, fact_name, schema_fact_names, eval_suite),
                    *ValidatorEvalSuite._find_non_numeric_amount_problems(check_name, fact_name, eval_suite),
                ]
            case FactValueCheckDefinition(check_name=check_name, fact_name=fact_name):
                return ValidatorEvalSuite._find_fact_reference_problems(check_name, fact_name, schema_fact_names, eval_suite)
            case ToolUseCheckDefinition(check_name=check_name, tool_input_pattern=tool_input_pattern):
                return ValidatorEvalSuite._find_pattern_problems(check_name, tool_input_pattern)
            case _:
                return []

    @staticmethod
    def _find_duplicate_names(name_kind: str, names: Iterable[str]) -> list[str]:
        # Case-insensitive: on Windows and macOS "Refund" and "refund" would share one results folder.
        duplicate_name_problems: list[str] = []
        folded_name: str
        occurrence_count: int
        for folded_name, occurrence_count in Counter(name.casefold() for name in names).items():
            if occurrence_count > 1:
                duplicate_name_problems.append(
                    f"{name_kind} name '{folded_name}' is used {occurrence_count} times (names are compared ignoring case)"
                )
        return duplicate_name_problems

    @staticmethod
    def _find_unsafe_names(name_kind: str, names: Iterable[str]) -> list[str]:
        return [
            f"{name_kind} name '{name}' {SAFE_NAME_RULE}"
            for name in names
            if not SAFE_NAME_PATTERN.fullmatch(name) or RESERVED_WINDOWS_DEVICE_NAME_PATTERN.fullmatch(name)
        ]

    @staticmethod
    def _find_empty_expected_fact_problems(eval_suite: EvalSuite) -> list[str]:
        # A fact whose accepted values are all blank can never be matched, so every check on it would fail every trial.
        return [
            f"case '{eval_case.case_name}' expects fact '{expected_fact.fact_name}' but accepts no non-blank value"
            for eval_case in eval_suite.eval_cases
            for expected_fact in eval_case.expected_facts
            if not any(accepted_value.strip() for accepted_value in expected_fact.accepted_values)
        ]

    @staticmethod
    def _find_reference_ledger_problems(eval_case: EvalCase, reference_ledger: ReferenceLedger) -> list[str]:
        reference_ledger_problems: list[str] = ValidatorEvalSuite._find_repeated_line_problems(eval_case.case_name, reference_ledger)
        fact_name: str
        ledger_bucket_totals: LedgerBucketTotals
        for fact_name, ledger_bucket_totals in reference_ledger.ledger_bucket_totals_by_fact_name.items():
            reference_ledger_problems.extend(ValidatorEvalSuite._find_amount_fact_ledger_problems(eval_case, fact_name, ledger_bucket_totals))
        return reference_ledger_problems

    @staticmethod
    def _find_repeated_line_problems(case_name: str, reference_ledger: ReferenceLedger) -> list[str]:
        repeated_line_problems: list[str] = []
        line_number: int
        occurrence_count: int
        for line_number, occurrence_count in Counter(ledger_entry.line_number for ledger_entry in reference_ledger.ledger_entries).items():
            if occurrence_count > 1:
                repeated_line_problems.append(f"case '{case_name}': the reference ledger lists line {line_number} {occurrence_count} times")
        return repeated_line_problems

    @staticmethod
    def _find_amount_fact_ledger_problems(eval_case: EvalCase, fact_name: str, ledger_bucket_totals: LedgerBucketTotals) -> list[str]:
        # The ledger and expected_facts.json are two views of one reference key; when they disagree, one of them is wrong.
        accepted_values_per_match: list[tuple[str, ...]] = [
            expected_fact.accepted_values for expected_fact in eval_case.expected_facts if expected_fact.fact_name == fact_name
        ]
        if not accepted_values_per_match:
            return [f"case '{eval_case.case_name}': the reference ledger totals fact '{fact_name}', which has no expected value"]
        accepted_amounts: set[Decimal] = ValidatorEvalSuite._read_accepted_amounts(accepted_values_per_match[0])
        ledger_amounts: set[Decimal] = ValidatorEvalSuite._read_ledger_amounts(ledger_bucket_totals)
        if accepted_amounts == ledger_amounts:
            return []
        return [
            (
                f"case '{eval_case.case_name}': fact '{fact_name}' accepts {ValidatorEvalSuite._format_amounts(accepted_amounts)}, but the "
                f"reference ledger totals it as {ValidatorEvalSuite._format_amounts(ledger_amounts)} under the key's policy and its accepted "
                "alternatives"
            )
        ]

    @staticmethod
    def _read_accepted_amounts(accepted_values: tuple[str, ...]) -> set[Decimal]:
        # A value that is not a plain number is reported by the amount check rules, not here.
        return {Decimal(accepted_value) for accepted_value in accepted_values if ValidatorEvalSuite._is_plain_finite_number(accepted_value)}

    @staticmethod
    def _read_ledger_amounts(ledger_bucket_totals: LedgerBucketTotals) -> set[Decimal]:
        return {ledger_bucket_composition.total_amount for ledger_bucket_composition in ledger_bucket_totals.ledger_bucket_compositions}

    @staticmethod
    def _format_amounts(amounts: Iterable[Decimal]) -> str:
        return " or ".join(str(amount) for amount in sorted(amounts)) or "nothing"

    @staticmethod
    def _find_fact_reference_problems(check_name: str, fact_name: str, schema_fact_names: tuple[str, ...], eval_suite: EvalSuite) -> list[str]:
        fact_reference_problems: list[str] = []
        if fact_name not in schema_fact_names:
            fact_reference_problems.append(f"check '{check_name}' uses fact '{fact_name}', which the fact extraction schema does not define")
        fact_reference_problems.extend(
            f"check '{check_name}' uses fact '{fact_name}', which case '{eval_case.case_name}' has no expected value for"
            for eval_case in eval_suite.eval_cases
            if all(expected_fact.fact_name != fact_name for expected_fact in eval_case.expected_facts)
        )
        return fact_reference_problems

    @staticmethod
    def _find_non_numeric_amount_problems(check_name: str, fact_name: str, eval_suite: EvalSuite) -> list[str]:
        return [
            f"amount check '{check_name}': case '{eval_case.case_name}' accepts '{accepted_value}' for '{fact_name}' (use plain numbers)"
            for eval_case in eval_suite.eval_cases
            for expected_fact in eval_case.expected_facts
            if expected_fact.fact_name == fact_name
            for accepted_value in expected_fact.accepted_values
            if not ValidatorEvalSuite._is_plain_finite_number(accepted_value)
        ]

    @staticmethod
    def _is_plain_finite_number(amount_text: str) -> bool:
        try:
            return Decimal(amount_text).is_finite()
        except InvalidOperation:
            return False

    @staticmethod
    def _find_pattern_problems(check_name: str, tool_input_pattern: str) -> list[str]:
        try:
            re.compile(tool_input_pattern)
        except re.error as pattern_error:
            return [f"check '{check_name}' has an invalid tool_input_pattern: {pattern_error}"]
        return []
