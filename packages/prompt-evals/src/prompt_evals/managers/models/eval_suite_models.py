from dataclasses import dataclass
from enum import StrEnum

from prompt_evals.managers.models.reference_ledger_models import ReferenceLedger


class ToolKind(StrEnum):
    """The tools a trial may use, named by what they do. Each gateway maps them to its assistant's own tool names."""

    SHELL = "shell"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    FIND_FILES = "find_files"
    SEARCH_FILE_CONTENTS = "search_file_contents"


@dataclass(frozen=True)
class PromptVariant:
    variant_name: str
    prompt_text: str


@dataclass(frozen=True)
class InputFile:
    file_name: str
    content: bytes


@dataclass(frozen=True)
class ExpectedFact:
    fact_name: str
    accepted_values: tuple[str, ...]


@dataclass(frozen=True)
class EvalCase:
    """`reference_ledger` is the optional entry-level reference key used to explain wrong totals; None when the case has none."""

    case_name: str
    input_files: tuple[InputFile, ...]
    expected_facts: tuple[ExpectedFact, ...]
    reference_ledger: ReferenceLedger | None


@dataclass(frozen=True)
class FactExtraction:
    instructions: str
    json_schema: str


@dataclass(frozen=True)
class AmountCheckDefinition:
    check_name: str
    description: str
    minimum_pass_rate: float
    fact_name: str


@dataclass(frozen=True)
class FactValueCheckDefinition:
    check_name: str
    description: str
    minimum_pass_rate: float
    fact_name: str


@dataclass(frozen=True)
class ToolUseCheckDefinition:
    check_name: str
    description: str
    minimum_pass_rate: float
    tool_kind: ToolKind
    tool_input_pattern: str


@dataclass(frozen=True)
class JudgeCheckDefinition:
    check_name: str
    description: str
    minimum_pass_rate: float
    rubric: str


type CheckDefinition = AmountCheckDefinition | FactValueCheckDefinition | ToolUseCheckDefinition | JudgeCheckDefinition


@dataclass(frozen=True)
class EvalSuite:
    eval_suite_name: str
    prompt_variants: tuple[PromptVariant, ...]
    eval_cases: tuple[EvalCase, ...]
    check_definitions: tuple[CheckDefinition, ...]
    fact_extraction: FactExtraction
    gated_variant_names: tuple[str, ...]
    trial_tool_kinds: tuple[ToolKind, ...]
