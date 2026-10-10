from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from prompt_evals.managers.models.eval_suite_models import ToolKind


class GraderKindResource(StrEnum):
    AMOUNT = "amount"
    FACT_VALUE = "fact_value"
    TOOL_USE = "tool_use"
    JUDGE = "judge"


@dataclass(frozen=True)
class CheckHeaderResource:
    """The fields every check shares, read once before the grader-specific fields."""

    check_name: str
    description: str
    minimum_pass_rate: float
    check_location: str


@dataclass(frozen=True)
class PromptVariantResource:
    variant_name: str
    prompt_file: str


@dataclass(frozen=True)
class CaseResource:
    case_name: str
    inputs_directory: str
    expected_facts_file: str
    reference_ledger_file: str | None


@dataclass(frozen=True)
class LedgerEntryResource:
    line_number: int
    source_text: str
    period: str
    amount: Decimal
    category: str
    alternative_categories: tuple[str, ...]
    policy_name: str | None
    is_counted: bool
    note: str | None


@dataclass(frozen=True)
class AmountFactLedgerBucketResource:
    fact_name: str
    category: str
    period: str | None


@dataclass(frozen=True)
class ReferenceLedgerResource:
    ledger_entry_resources: tuple[LedgerEntryResource, ...]
    amount_fact_ledger_bucket_resources: tuple[AmountFactLedgerBucketResource, ...]


@dataclass(frozen=True)
class FactExtractionResource:
    instructions_file: str
    json_schema_file: str


@dataclass(frozen=True)
class AmountCheckResource:
    check_name: str
    description: str
    minimum_pass_rate: float
    fact_name: str


@dataclass(frozen=True)
class FactValueCheckResource:
    check_name: str
    description: str
    minimum_pass_rate: float
    fact_name: str


@dataclass(frozen=True)
class ToolUseCheckResource:
    check_name: str
    description: str
    minimum_pass_rate: float
    tool_kind: ToolKind
    tool_input_pattern: str


@dataclass(frozen=True)
class JudgeCheckResource:
    check_name: str
    description: str
    minimum_pass_rate: float
    rubric_file: str


type CheckResource = AmountCheckResource | FactValueCheckResource | ToolUseCheckResource | JudgeCheckResource


@dataclass(frozen=True)
class EvalSuiteResource:
    eval_suite_name: str
    prompt_variant_resources: tuple[PromptVariantResource, ...]
    gated_variant_names: tuple[str, ...]
    trial_tool_kinds: tuple[ToolKind, ...]
    case_resources: tuple[CaseResource, ...]
    fact_extraction_resource: FactExtractionResource
    check_resources: tuple[CheckResource, ...]
