"""The expense-analysis eval in one plain file: no library, no layers. Read it top to bottom.

    Arrange  read and validate the eval suite folder (prompts, input files, expected facts, checks, rubrics) into typed records
    Act      run each prompt N times, each in a brand-new isolated `claude -p` session
    Assert   gather each answer's grader verdicts (fact extraction and rubric judges, each in its own session),
             grade the run with plain comparisons, turn the grades into pass rates,
             and require the gated prompt to meet each minimum

Every check grade is passed, failed or errored. Errored means a session failed, so the check could not be judged:
a failed trial session errors every check of that run, a failed fact extraction errors only that run's amount and
fact_value checks, and a failed judge session errors only its own check. An errored check is not a pass, and the
scorecard counts and lists it apart from the failed checks, so a crashed session never reads as a weak prompt.

A failed check also says why, when it can: if the case has a reference ledger (every input line with the reference
key's category), a wrong total is traced to the few entries that make the difference, such as "counted line 16
'June 4: Steam, 47.58', which the reference puts in Entertainment". Nobody has to reconcile the input data by hand.

It evaluates exactly what the PWI library (packages/prompt-evals) evaluates, because both read evals/expense_analysis.
Run it with:  uv run pytest evals/minimal -s --eval-repetitions 3
"""

import contextlib
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Collection, Container, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from itertools import combinations
from pathlib import Path
from typing import Final, cast

import pytest

EVAL_SUITE_DIRECTORY: Final[Path] = Path(__file__).resolve().parents[1] / "expense_analysis"
# The PWI library writes to results/pwi/<eval suite>; this file's runs stay apart in results/minimal/<eval suite>.
RESULTS_DIRECTORY: Final[Path] = Path(__file__).resolve().parents[2] / "results" / "minimal" / "expense_analysis"
EVAL_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
TEXT_ENCODING: Final[str] = "utf-8"
SESSION_TIMEOUT_SECONDS: Final[int] = 900
SESSION_KILL_WAIT_SECONDS: Final[int] = 10
STDERR_TAIL_LENGTH: Final[int] = 500
GRADER_MODEL: Final[str] = "sonnet"
GRADER_EFFORT: Final[str] = "low"
RUN_IDENTITY_RANDOM_BYTES: Final[int] = 3
AMOUNT_TOLERANCE: Final[float] = 0.01
TOOL_INPUT_PATTERN_FLAGS: Final[re.RegexFlag] = re.IGNORECASE
JUDGE_VERDICT_SCHEMA: Final[str] = json.dumps(
    {
        "type": "object",
        "required": ["passed", "reason", "disputed_amounts"],
        "properties": {
            "passed": {"type": "boolean"},
            "reason": {"type": "string"},
            "disputed_amounts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["description", "answer_amount", "reference_amount"],
                    "properties": {
                        "description": {"type": "string"},
                        "answer_amount": {"type": "string"},
                        "reference_amount": {"type": "string"},
                    },
                },
            },
        },
    }
)
# Tracing a wrong total: the fewest entry mistakes that add up to the difference. Beyond two mistakes, only plausible ones
# (a likely duplicate, an entry an accepted policy could move, a reference entry left out) are tried, because among dozens
# of entries three arbitrary amounts add up to almost any difference by coincidence.
MAXIMUM_TRACED_MISTAKES: Final[int] = 3
ANY_ENTRY_MISTAKE_LIMIT: Final[int] = 2
AMOUNT_TEXT_PATTERN: Final[re.Pattern[str]] = re.compile(r"-?\s*\$?\s*\d[\d,]*(?:\.\d+)?")


# ----------------------------------------------------------------------------------------------------------
# Foreign JSON: eval suite files, the CLI's event stream and grader output are checked field by field
# before any value reaches a typed record, so a bad document fails once, naming the offending field.
# ----------------------------------------------------------------------------------------------------------


type JsonObject = Mapping[str, object]


class InvalidJsonException(Exception):
    """A JSON document is not valid JSON, or lacks a field the eval needs, or holds a value of the wrong type."""


def parse_json_object(json_text: str, location: str) -> JsonObject:
    try:
        parsed_json: object = json.loads(json_text)
    except json.JSONDecodeError as decode_failure:
        raise InvalidJsonException(f"{location}: not valid JSON ({decode_failure})") from decode_failure
    return as_json_object(parsed_json, location)


def as_json_object(json_value: object, location: str) -> JsonObject:
    if not isinstance(json_value, dict):
        raise InvalidJsonException(f"{location}: expected a JSON object, found {type(json_value).__name__}")
    # json.loads only builds dictionaries with string keys, so the cast states a fact rather than a hope.
    return cast("JsonObject", json_value)


def as_object_list(json_value: object, location: str) -> tuple[JsonObject, ...]:
    if not isinstance(json_value, list):
        raise InvalidJsonException(f"{location}: expected a JSON list, found {type(json_value).__name__}")
    return tuple(as_json_object(list_item, location) for list_item in cast("list[object]", json_value))


def read_field(json_object: JsonObject, field_name: str, location: str) -> object:
    if field_name not in json_object:
        raise InvalidJsonException(f"{location}: the '{field_name}' field is missing")
    return json_object[field_name]


def read_string(json_object: JsonObject, field_name: str, location: str) -> str:
    field_value: object = read_field(json_object, field_name, location)
    if not isinstance(field_value, str):
        raise InvalidJsonException(f"{location}: '{field_name}' must be a string")
    return field_value


def read_bool(json_object: JsonObject, field_name: str, location: str) -> bool:
    field_value: object = read_field(json_object, field_name, location)
    if not isinstance(field_value, bool):
        raise InvalidJsonException(f"{location}: '{field_name}' must be true or false")
    return field_value


def read_object(json_object: JsonObject, field_name: str, location: str) -> JsonObject:
    return as_json_object(read_field(json_object, field_name, location), f"{location} '{field_name}'")


def read_text(json_object: JsonObject, field_name: str, location: str) -> str:
    # A grader session that returns structured output need not write a result text, so absent means no text.
    return "" if json_object.get(field_name) is None else read_string(json_object, field_name, location)


def read_optional_object(json_object: JsonObject, field_name: str, location: str) -> JsonObject | None:
    field_value: object = json_object.get(field_name)
    return None if field_value is None else as_json_object(field_value, f"{location} '{field_name}'")


def read_optional_string(json_object: JsonObject, field_name: str, location: str) -> str | None:
    return None if json_object.get(field_name) is None else read_string(json_object, field_name, location)


def read_object_list(json_object: JsonObject, field_name: str, location: str) -> tuple[JsonObject, ...]:
    return as_object_list(read_field(json_object, field_name, location), f"{location} '{field_name}'")


def read_string_list(json_object: JsonObject, field_name: str, location: str) -> tuple[str, ...]:
    field_value: object = read_field(json_object, field_name, location)
    if not isinstance(field_value, list) or not all(isinstance(list_item, str) for list_item in cast("list[object]", field_value)):
        raise InvalidJsonException(f"{location}: '{field_name}' must be a list of strings")
    return tuple(cast("list[str]", field_value))


def read_pass_rate(json_object: JsonObject, field_name: str, location: str) -> float:
    field_value: object = read_field(json_object, field_name, location)
    # bool is a subclass of int in Python, so true would otherwise pass as 1. NaN fails the range test.
    if isinstance(field_value, bool) or not isinstance(field_value, int | float) or not 0 <= field_value <= 1:
        raise InvalidJsonException(f"{location}: '{field_name}' must be a number from 0 to 1")
    return float(field_value)


# ----------------------------------------------------------------------------------------------------------
# Arrange: the eval suite folder as typed records
# ----------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckDefinition:
    check_name: str
    description: str
    minimum_pass_rate: float


@dataclass(frozen=True)
class AmountCheck(CheckDefinition):
    fact_name: str


@dataclass(frozen=True)
class FactValueCheck(CheckDefinition):
    fact_name: str


@dataclass(frozen=True)
class ToolUseCheck(CheckDefinition):
    tool_name: str
    tool_input_pattern: str


@dataclass(frozen=True)
class JudgeCheck(CheckDefinition):
    rubric_text: str


type EvalSuiteCheck = AmountCheck | FactValueCheck | ToolUseCheck | JudgeCheck


@dataclass(frozen=True)
class PromptVariant:
    variant_name: str
    prompt_text: str


@dataclass(frozen=True)
class FactExtraction:
    instructions: str
    json_schema: str
    required_fact_names: tuple[str, ...]


@dataclass(frozen=True)
class LedgerEntry:
    """One input line as the reference key reads it. `policy_name` names the accepted alternative that may move it
    to one of `alternative_categories`; an entry that is not counted (a likely duplicate) is in no reference total."""

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
class LedgerBucket:
    """One category in one period, or in every period when `period` is None."""

    category: str
    period: str | None


@dataclass(frozen=True)
class ReferenceLedger:
    ledger_entries: tuple[LedgerEntry, ...]
    ledger_bucket_by_fact_name: Mapping[str, LedgerBucket]


@dataclass(frozen=True)
class EvalSuite:
    eval_suite_name: str
    prompt_variants: tuple[PromptVariant, ...]
    gated_variant_names: tuple[str, ...]
    trial_tool_names: tuple[str, ...]
    content_by_input_file_name: Mapping[str, bytes]
    expected_fact_values_by_fact_name: Mapping[str, tuple[str, ...]]
    reference_ledger: ReferenceLedger | None
    fact_extraction: FactExtraction
    checks: tuple[EvalSuiteCheck, ...]


# eval_suite.json as written: validated, but the files it points to are not read yet.


@dataclass(frozen=True)
class PromptVariantResource:
    variant_name: str
    prompt_file: str


@dataclass(frozen=True)
class JudgeCheckResource(CheckDefinition):
    rubric_file: str


type CheckResource = AmountCheck | FactValueCheck | ToolUseCheck | JudgeCheckResource


@dataclass(frozen=True)
class EvalSuiteResource:
    eval_suite_name: str
    prompt_variant_resources: tuple[PromptVariantResource, ...]
    gated_variant_names: tuple[str, ...]
    trial_tool_names: tuple[str, ...]
    inputs_directory: str
    expected_facts_file: str
    reference_ledger_file: str | None
    fact_extraction_instructions_file: str
    fact_extraction_schema_file: str
    check_resources: tuple[CheckResource, ...]


CLAUDE_CODE_ASSISTANT: Final[str] = "claude_code"
# eval_suite.json names tools by what they do; Claude Code has its own name for each.
CLAUDE_TOOL_NAME_BY_TOOL_KIND: Final[Mapping[str, str]] = {
    "shell": "Bash",
    "read_file": "Read",
    "write_file": "Write",
    "edit_file": "Edit",
    "find_files": "Glob",
    "search_file_contents": "Grep",
}


def load_eval_suite(eval_suite_directory: Path) -> EvalSuite:
    eval_suite_resource: EvalSuiteResource = validate_eval_suite_definition(
        (eval_suite_directory / EVAL_SUITE_DEFINITION_FILE_NAME).read_text(encoding=TEXT_ENCODING)
    )
    eval_suite: EvalSuite = read_eval_suite_files(eval_suite_resource, eval_suite_directory)
    validate_eval_suite_references(
        eval_suite.prompt_variants,
        eval_suite.checks,
        eval_suite.gated_variant_names,
        eval_suite.expected_fact_values_by_fact_name,
        eval_suite.fact_extraction.required_fact_names,
    )
    return eval_suite


def validate_eval_suite_definition(eval_suite_definition_text: str) -> EvalSuiteResource:
    """The one place eval_suite.json is indexed. Only the first case is evaluated."""
    eval_suite_object: JsonObject = parse_json_object(eval_suite_definition_text, EVAL_SUITE_DEFINITION_FILE_NAME)
    case_objects: tuple[JsonObject, ...] = read_object_list(eval_suite_object, "cases", EVAL_SUITE_DEFINITION_FILE_NAME)
    if not case_objects:
        raise InvalidJsonException(f"{EVAL_SUITE_DEFINITION_FILE_NAME}: 'cases' must list at least one case")
    case_location: str = f"{EVAL_SUITE_DEFINITION_FILE_NAME} first case"
    fact_extraction_object: JsonObject = read_object(eval_suite_object, "fact_extraction", EVAL_SUITE_DEFINITION_FILE_NAME)
    fact_extraction_location: str = f"{EVAL_SUITE_DEFINITION_FILE_NAME} fact_extraction"
    prompt_variant_location: str = f"{EVAL_SUITE_DEFINITION_FILE_NAME} prompt variant"
    return EvalSuiteResource(
        eval_suite_name=read_string(eval_suite_object, "eval_suite_name", EVAL_SUITE_DEFINITION_FILE_NAME),
        prompt_variant_resources=tuple(
            PromptVariantResource(
                variant_name=read_string(variant_object, "variant_name", prompt_variant_location),
                prompt_file=read_string(variant_object, "prompt_file", prompt_variant_location),
            )
            for variant_object in read_object_list(eval_suite_object, "prompt_variants", EVAL_SUITE_DEFINITION_FILE_NAME)
        ),
        gated_variant_names=read_string_list(eval_suite_object, "gated_variant_names", EVAL_SUITE_DEFINITION_FILE_NAME),
        trial_tool_names=tuple(
            to_claude_tool_name(tool_kind, EVAL_SUITE_DEFINITION_FILE_NAME)
            for tool_kind in read_string_list(eval_suite_object, "trial_tool_kinds", EVAL_SUITE_DEFINITION_FILE_NAME)
        ),
        inputs_directory=read_string(case_objects[0], "inputs_directory", case_location),
        expected_facts_file=read_string(case_objects[0], "expected_facts_file", case_location),
        reference_ledger_file=None
        if case_objects[0].get("reference_ledger_file") is None
        else read_string(case_objects[0], "reference_ledger_file", case_location),
        fact_extraction_instructions_file=read_string(fact_extraction_object, "instructions_file", fact_extraction_location),
        fact_extraction_schema_file=read_string(fact_extraction_object, "json_schema_file", fact_extraction_location),
        check_resources=tuple(
            validate_check(check_object) for check_object in read_object_list(eval_suite_object, "checks", EVAL_SUITE_DEFINITION_FILE_NAME)
        ),
    )


def validate_check(check_object: JsonObject) -> CheckResource:
    check_name: str = read_string(check_object, "check_name", f"{EVAL_SUITE_DEFINITION_FILE_NAME} check")
    check_location: str = f"{EVAL_SUITE_DEFINITION_FILE_NAME} check '{check_name}'"
    description: str = read_string(check_object, "description", check_location)
    minimum_pass_rate: float = read_pass_rate(check_object, "minimum_pass_rate", check_location)
    match read_string(check_object, "grader", check_location):
        case "amount":
            return AmountCheck(check_name, description, minimum_pass_rate, fact_name=read_string(check_object, "fact_name", check_location))
        case "fact_value":
            return FactValueCheck(check_name, description, minimum_pass_rate, fact_name=read_string(check_object, "fact_name", check_location))
        case "tool_use":
            return ToolUseCheck(
                check_name,
                description,
                minimum_pass_rate,
                tool_name=to_claude_tool_name(read_string(check_object, "tool_kind", check_location), check_location),
                tool_input_pattern=read_string(check_object, "tool_input_pattern", check_location),
            )
        case "judge":
            return JudgeCheckResource(
                check_name, description, minimum_pass_rate, rubric_file=read_string(check_object, "rubric_file", check_location)
            )
        case unknown_grader:
            unknown_grader_message: str = (
                f"{check_location}: 'grader' names an unknown grader: {unknown_grader}; "
                "known graders are ['amount', 'fact_value', 'judge', 'tool_use']"
            )
            raise InvalidJsonException(unknown_grader_message)


def to_claude_tool_name(tool_kind: str, location: str) -> str:
    claude_tool_name: str | None = CLAUDE_TOOL_NAME_BY_TOOL_KIND.get(tool_kind)
    if claude_tool_name is None:
        raise InvalidJsonException(f"{location}: unknown tool kind '{tool_kind}'; known kinds are {sorted(CLAUDE_TOOL_NAME_BY_TOOL_KIND)}")
    return claude_tool_name


def read_eval_suite_files(eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path) -> EvalSuite:
    expected_facts_text: str = (eval_suite_directory / eval_suite_resource.expected_facts_file).read_text(encoding=TEXT_ENCODING)
    schema_object: JsonObject = parse_json_object(
        (eval_suite_directory / eval_suite_resource.fact_extraction_schema_file).read_text(encoding=TEXT_ENCODING),
        eval_suite_resource.fact_extraction_schema_file,
    )
    return EvalSuite(
        eval_suite_name=eval_suite_resource.eval_suite_name,
        prompt_variants=tuple(
            PromptVariant(
                variant_name=prompt_variant_resource.variant_name,
                prompt_text=(eval_suite_directory / prompt_variant_resource.prompt_file).read_text(encoding=TEXT_ENCODING).rstrip(),
            )
            for prompt_variant_resource in eval_suite_resource.prompt_variant_resources
        ),
        gated_variant_names=eval_suite_resource.gated_variant_names,
        trial_tool_names=eval_suite_resource.trial_tool_names,
        content_by_input_file_name={
            path.name: path.read_bytes() for path in sorted((eval_suite_directory / eval_suite_resource.inputs_directory).iterdir())
        },
        expected_fact_values_by_fact_name=validate_expected_facts(expected_facts_text, eval_suite_resource.expected_facts_file),
        reference_ledger=None
        if eval_suite_resource.reference_ledger_file is None
        else validate_reference_ledger(
            (eval_suite_directory / eval_suite_resource.reference_ledger_file).read_text(encoding=TEXT_ENCODING),
            eval_suite_resource.reference_ledger_file,
        ),
        fact_extraction=FactExtraction(
            instructions=(eval_suite_directory / eval_suite_resource.fact_extraction_instructions_file).read_text(encoding=TEXT_ENCODING),
            json_schema=json.dumps(schema_object),
            required_fact_names=read_string_list(schema_object, "required", eval_suite_resource.fact_extraction_schema_file),
        ),
        checks=tuple(load_check(check_resource, eval_suite_directory) for check_resource in eval_suite_resource.check_resources),
    )


def validate_expected_facts(expected_facts_text: str, expected_facts_file: str) -> dict[str, tuple[str, ...]]:
    expected_facts_object: JsonObject = read_object(
        parse_json_object(expected_facts_text, expected_facts_file), "expected_facts", expected_facts_file
    )
    return {fact_name: read_string_list(expected_facts_object, fact_name, expected_facts_file) for fact_name in expected_facts_object}


def validate_reference_ledger(reference_ledger_text: str, reference_ledger_file: str) -> ReferenceLedger:
    """The ledger as typed records. The library also proves it agrees with the expected facts; this file trusts that."""
    reference_ledger_object: JsonObject = parse_json_object(reference_ledger_text, reference_ledger_file)
    amount_facts_object: JsonObject = read_object(reference_ledger_object, "amount_facts", reference_ledger_file)
    return ReferenceLedger(
        ledger_entries=tuple(
            validate_ledger_entry(entry_object, f"{reference_ledger_file} entry {entry_number}")
            for entry_number, entry_object in enumerate(read_object_list(reference_ledger_object, "entries", reference_ledger_file), start=1)
        ),
        ledger_bucket_by_fact_name={
            fact_name: LedgerBucket(
                category=read_string(read_object(amount_facts_object, fact_name, reference_ledger_file), "category", fact_name),
                period=read_optional_string(read_object(amount_facts_object, fact_name, reference_ledger_file), "period", fact_name),
            )
            for fact_name in amount_facts_object
        },
    )


def validate_ledger_entry(entry_object: JsonObject, entry_location: str) -> LedgerEntry:
    line_number: object = read_field(entry_object, "line_number", entry_location)
    if not isinstance(line_number, int) or isinstance(line_number, bool):
        raise InvalidJsonException(f"{entry_location}: 'line_number' must be a whole number")
    amount_text: str = read_string(entry_object, "amount", entry_location)
    try:
        amount: Decimal = Decimal(amount_text)
    except InvalidOperation as invalid_amount:
        raise InvalidJsonException(f"{entry_location}: 'amount' '{amount_text}' is not a number") from invalid_amount
    alternative_categories: tuple[str, ...] = read_string_list(entry_object, "alternative_categories", entry_location)
    policy_name: str | None = read_optional_string(entry_object, "policy_name", entry_location)
    if bool(alternative_categories) != (policy_name is not None):
        policy_mismatch_message: str = (
            f"{entry_location}: needs a 'policy_name' exactly when it lists 'alternative_categories'; "
            f"policy_name is {policy_name!r}, alternative_categories is {list(alternative_categories)}"
        )
        raise InvalidJsonException(policy_mismatch_message)
    return LedgerEntry(
        line_number=line_number,
        source_text=read_string(entry_object, "source_text", entry_location),
        period=read_string(entry_object, "period", entry_location),
        amount=amount,
        category=read_string(entry_object, "category", entry_location),
        alternative_categories=alternative_categories,
        policy_name=policy_name,
        is_counted=read_bool(entry_object, "is_counted", entry_location),
        note=read_optional_string(entry_object, "note", entry_location),
    )


def load_check(check_resource: CheckResource, eval_suite_directory: Path) -> EvalSuiteCheck:
    match check_resource:
        case JudgeCheckResource():
            rubric_text: str = (eval_suite_directory / check_resource.rubric_file).read_text(encoding=TEXT_ENCODING)
            return JudgeCheck(check_resource.check_name, check_resource.description, check_resource.minimum_pass_rate, rubric_text=rubric_text)
        case AmountCheck() | FactValueCheck() | ToolUseCheck():
            return check_resource


def validate_eval_suite_references(
    prompt_variants: Sequence[PromptVariant],
    checks: Sequence[EvalSuiteCheck],
    gated_variant_names: Collection[str],
    expected_fact_values_by_fact_name: Mapping[str, Sequence[str]],
    required_fact_names: Sequence[str],
) -> None:
    """Fail once, before any paid session starts, listing every reference in the eval suite that does not resolve.

    Each of these defects would otherwise surface only after trial and grader sessions had run, or would fail
    a check on every run and so blame the prompt for an eval suite error.
    """
    variant_names: list[str] = [prompt_variant.variant_name for prompt_variant in prompt_variants]
    reference_problems: list[str] = [
        *find_duplicate_names("variant_name", variant_names),
        *find_duplicate_names("check_name", [check.check_name for check in checks]),
        *find_gated_variant_problems(gated_variant_names, variant_names),
        *(
            check_problem
            for check in checks
            for check_problem in find_check_reference_problems(check, expected_fact_values_by_fact_name, required_fact_names)
        ),
    ]
    if reference_problems:
        problem_lines: str = "\n".join(f"  - {reference_problem}" for reference_problem in reference_problems)
        raise InvalidJsonException(
            f"{EVAL_SUITE_DEFINITION_FILE_NAME}: the eval suite has {len(reference_problems)} broken references:\n{problem_lines}"
        )


def find_duplicate_names(field_name: str, declared_names: Iterable[str]) -> list[str]:
    # Grades are keyed by check name and run folders by variant name, so a repeated name would overwrite or collide.
    return [
        f"'{field_name}' '{declared_name}' is used {use_count} times" for declared_name, use_count in Counter(declared_names).items() if use_count > 1
    ]


def find_gated_variant_problems(gated_variant_names: Collection[str], variant_names: Container[str]) -> list[str]:
    # With no gated variant, or one the eval suite does not define, the gate would pass without checking anything.
    if not gated_variant_names:
        return ["'gated_variant_names' must name at least one prompt variant"]
    return [
        f"'gated_variant_names' names '{gated_variant_name}', which is not a defined prompt variant"
        for gated_variant_name in gated_variant_names
        if gated_variant_name not in variant_names
    ]


def find_check_reference_problems(
    check: EvalSuiteCheck, expected_fact_values_by_fact_name: Mapping[str, Sequence[str]], required_fact_names: Container[str]
) -> list[str]:
    match check:
        case AmountCheck() | FactValueCheck():
            return find_fact_check_problems(check, expected_fact_values_by_fact_name, required_fact_names)
        case ToolUseCheck():
            return find_tool_input_pattern_problems(check)
        case JudgeCheck():
            return []


def find_fact_check_problems(
    fact_check: AmountCheck | FactValueCheck, expected_fact_values_by_fact_name: Mapping[str, Sequence[str]], required_fact_names: Container[str]
) -> list[str]:
    fact_name_location: str = f"check '{fact_check.check_name}' 'fact_name'"
    fact_check_problems: list[str] = []
    # The extraction session fills only the schema's facts, so a fact outside it would fail the check on every run.
    if fact_check.fact_name not in required_fact_names:
        fact_check_problems.append(f"{fact_name_location}: '{fact_check.fact_name}' is not a required fact of the fact extraction schema")
    expected_fact_values: Sequence[str] | None = expected_fact_values_by_fact_name.get(fact_check.fact_name)
    if expected_fact_values is None:
        fact_check_problems.append(f"{fact_name_location}: '{fact_check.fact_name}' has no expected values in the expected facts file")
    elif isinstance(fact_check, AmountCheck):
        fact_check_problems.extend(
            f"{fact_name_location}: the expected amount '{expected_amount}' of '{fact_check.fact_name}' is not a number"
            for expected_amount in expected_fact_values
            if not is_number_text(expected_amount)
        )
    return fact_check_problems


def is_number_text(amount_text: str) -> bool:
    try:
        float(amount_text)
    except ValueError:
        return False
    return True


def find_tool_input_pattern_problems(tool_use_check: ToolUseCheck) -> list[str]:
    try:
        re.compile(tool_use_check.tool_input_pattern, TOOL_INPUT_PATTERN_FLAGS)
    except re.error as pattern_error:
        return [f"check '{tool_use_check.check_name}' 'tool_input_pattern': not a valid regular expression ({pattern_error})"]
    return []


def create_run_directory(model: str, effort: str) -> Path:
    # The random suffix keeps two runs started in the same second with the same model and effort out of one folder.
    run_identity: str = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{model}-{effort}-{secrets.token_hex(RUN_IDENTITY_RANDOM_BYTES)}"
    run_directory: Path = RESULTS_DIRECTORY / run_identity.replace(":", "-").replace("/", "-")
    run_directory.mkdir(parents=True)
    return run_directory


# ----------------------------------------------------------------------------------------------------------
# Act: one isolated `claude -p` session
# ----------------------------------------------------------------------------------------------------------


class SessionFailedException(Exception):
    """The session could not start, did not finish, ended in error, or wrote output that cannot be read."""


@dataclass(frozen=True)
class SessionRequest:
    prompt: str
    model: str
    effort: str
    content_by_file_name: Mapping[str, bytes]
    tools: tuple[str, ...]
    json_schema: str | None  # None lets the session answer in free text


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    tool_input: str
    is_error: bool


@dataclass(frozen=True)
class Session:
    answer: str
    structured_output: JsonObject | None
    tool_calls: tuple[ToolCall, ...]
    event_stream: str


EVENT_STREAM_LOCATION: Final[str] = "the event stream"
TOOL_USE_LOCATION: Final[str] = "a tool_use block in the event stream"
TOOL_RESULT_LOCATION: Final[str] = "a tool_result block in the event stream"
RESULT_EVENT_LOCATION: Final[str] = "the result event"
# POSIX starts the CLI as the head of a new process group through start_new_session (ignored on Windows);
# Windows uses this creation flag instead, and Popen rejects any creation flag elsewhere.
NEW_PROCESS_GROUP_CREATION_FLAGS: Final[int] = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0


def run_claude(session_request: SessionRequest) -> Session:
    """Start a fresh Claude Code session in an empty temp folder that holds only the given files, and read its event stream."""
    command: list[str] = build_claude_command(session_request)
    with tempfile.TemporaryDirectory(prefix="minimal-eval-", ignore_cleanup_errors=True) as sandbox_directory:
        write_sandbox_files(session_request.content_by_file_name, Path(sandbox_directory))
        event_stream: str = run_session_process(command, session_request.prompt, sandbox_directory)
    return parse_event_stream(event_stream)


def build_claude_command(session_request: SessionRequest) -> list[str]:
    command: list[str] = [
        "claude", "-p",
        "--model", session_request.model,
        "--effort", session_request.effort,
        "--restricted",               # ignore the user's settings, plugins and hooks; confine file tools to the folder
        "--strict-mcp-config",        # no MCP servers
        "--disable-slash-commands",   # no skills
        "--no-session-persistence",   # keep eval sessions out of the user's history
        "--permission-mode", "dontAsk",
        "--tools", ",".join(session_request.tools),
        "--output-format", "stream-json", "--verbose",  # one JSON event per line, including every tool call
    ]  # fmt: skip
    # Under the dontAsk permission mode the CLI denies every call to a tool that is available but not pre-approved,
    # so the same tool list must be repeated as --allowedTools.
    if session_request.tools:
        command += ["--allowedTools", ",".join(session_request.tools)]
    if session_request.json_schema:
        command += ["--json-schema", session_request.json_schema]
    return command


def write_sandbox_files(content_by_file_name: Mapping[str, bytes], sandbox_directory: Path) -> None:
    file_name: str
    content: bytes
    for file_name, content in content_by_file_name.items():
        (sandbox_directory / file_name).write_bytes(content)


def run_session_process(command: Sequence[str], prompt: str, sandbox_directory: str) -> str:
    """Run the CLI in its own process group and return its stdout; every way the run can go wrong is a SessionFailedException.

    subprocess.run(timeout=...) would kill only the CLI. The tool commands the session started would keep running,
    and on Windows the final read would then wait, with no time limit, for each of them to close the stdout it inherited.
    """
    try:
        process: subprocess.Popen[bytes] = subprocess.Popen(  # noqa: S603 - the command is built from fixed flags and eval suite data
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=sandbox_directory,
            start_new_session=True,
            creationflags=NEW_PROCESS_GROUP_CREATION_FLAGS,
        )
    except OSError as start_failure:
        raise SessionFailedException(f"claude could not be started: {start_failure}") from start_failure
    stdout_bytes: bytes
    stderr_bytes: bytes
    try:
        stdout_bytes, stderr_bytes = process.communicate(prompt.encode(TEXT_ENCODING), timeout=SESSION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as timeout:
        raise SessionFailedException(f"claude did not finish within {SESSION_TIMEOUT_SECONDS} seconds") from timeout
    finally:
        # Reached on a timeout, and on Ctrl+C, which no longer reaches a CLI that runs in its own process group.
        if process.returncode is None:
            stop_process_tree(process)
    if process.returncode != 0:
        stderr_tail: str = stderr_bytes.decode(TEXT_ENCODING, errors="replace")[-STDERR_TAIL_LENGTH:]
        raise SessionFailedException(f"claude exited with {process.returncode}: {stderr_tail}")
    try:
        return stdout_bytes.decode(TEXT_ENCODING)
    except UnicodeDecodeError as decode_failure:
        raise SessionFailedException(f"claude wrote output that is not UTF-8: {decode_failure}") from decode_failure


def stop_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Kill the CLI together with every process it started, then collect its exit without ever waiting long."""
    if sys.platform == "win32":
        # taskkill /T finds the tool commands through their parent, so it has to run while the CLI is still alive.
        taskkill_command: list[str] = ["taskkill", "/T", "/F", "/PID", str(process.pid)]
        subprocess.run(taskkill_command, capture_output=True, check=False)  # noqa: S603 - a fixed Windows system command
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    # A process that escaped the kill (one that left the group, for example) can still hold the pipes open.
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.communicate(timeout=SESSION_KILL_WAIT_SECONDS)


def parse_event_stream(event_stream: str) -> Session:
    try:
        return read_session_events(event_stream)
    except InvalidJsonException as malformation:
        # A garbled or truncated stream (a non-JSON line, an event of an unexpected shape) is a failed session like any other.
        raise SessionFailedException(f"the event stream could not be read: {malformation}") from malformation


def read_session_events(event_stream: str) -> Session:
    # Split on "\n" only. str.splitlines() also splits on U+2028, U+2029 and U+0085, which the CLI's JSON.stringify
    # leaves unescaped inside strings, so one such character in an answer or tool output would cut its event in two.
    events: list[JsonObject] = [parse_json_object(event_line, EVENT_STREAM_LOCATION) for event_line in event_stream.split("\n") if event_line.strip()]
    content_blocks: list[JsonObject] = [content_block for event in events for content_block in read_content_blocks(event)]
    # A tool call whose result never arrived did not succeed, so it counts as errored.
    is_error_by_tool_use_id: dict[str, bool] = {
        read_string(content_block, "tool_use_id", TOOL_RESULT_LOCATION): content_block.get("is_error") is True
        for content_block in content_blocks
        if content_block.get("type") == "tool_result"
    }
    result_event: JsonObject | None = next((event for event in events if event.get("type") == "result"), None)
    if result_event is None:
        raise SessionFailedException("the event stream ended without a result event")
    if read_bool(result_event, "is_error", RESULT_EVENT_LOCATION):
        raise SessionFailedException(f"the session ended in error: {read_string(result_event, 'subtype', RESULT_EVENT_LOCATION)}")
    return Session(
        answer=read_text(result_event, "result", RESULT_EVENT_LOCATION),
        structured_output=read_optional_object(result_event, "structured_output", RESULT_EVENT_LOCATION),
        tool_calls=tuple(
            read_tool_call(content_block, is_error_by_tool_use_id) for content_block in content_blocks if content_block.get("type") == "tool_use"
        ),
        event_stream=event_stream,
    )


def read_content_blocks(event: JsonObject) -> tuple[JsonObject, ...]:
    """Assistant and user events carry a message whose content is a list of blocks; other events carry none."""
    message: object = event.get("message")
    if message is None:
        return ()
    message_content: object = as_json_object(message, f"{EVENT_STREAM_LOCATION} message").get("content")
    if message_content is None or isinstance(message_content, str):
        return ()
    return as_object_list(message_content, f"{EVENT_STREAM_LOCATION} message content")


def read_tool_call(tool_use_block: JsonObject, is_error_by_tool_use_id: Mapping[str, bool]) -> ToolCall:
    tool_input_object: JsonObject = read_object(tool_use_block, "input", TOOL_USE_LOCATION)
    return ToolCall(
        tool_name=read_string(tool_use_block, "name", TOOL_USE_LOCATION),
        # Keep the text the model typed. JSON-encoding it would turn each newline into a backslash and an "n",
        # hiding the word boundary before a command on the next line (for example "python an.py").
        tool_input="\n".join(str(input_value) for input_value in tool_input_object.values()),
        is_error=is_error_by_tool_use_id.get(read_string(tool_use_block, "id", TOOL_USE_LOCATION), True),
    )


# ----------------------------------------------------------------------------------------------------------
# Assert, part 1a: gather the grader sessions' verdicts on one answer
# ----------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ExtractedFacts:
    # None means the answer never states the fact. Other values are text, so true reads "true" and 8 reads "8".
    reported_value_by_fact_name: Mapping[str, str | None]


@dataclass(frozen=True)
class DisputedAmount:
    """An amount the judge rejected because it contradicts a reference value in the rubric, quoted as the judge read both."""

    description: str
    answer_amount: str
    reference_amount: str


@dataclass(frozen=True)
class JudgeVerdict:
    passed: bool
    reason: str
    disputed_amounts: tuple[DisputedAmount, ...]


EXTRACTED_FACTS_LOCATION: Final[str] = "the extracted facts"
JUDGE_VERDICT_LOCATION: Final[str] = "the judge verdict"


def extract_facts(answer: str, fact_extraction: FactExtraction) -> ExtractedFacts:
    """A separate tool-less session reads the answer and fills the schema. It only extracts; code decides right or wrong."""
    prompt: str = f"# Fact extraction task\n\n{fact_extraction.instructions}\n\n<answer>\n{answer}\n</answer>\n"
    structured_output: JsonObject | None = run_claude(
        SessionRequest(prompt, GRADER_MODEL, GRADER_EFFORT, content_by_file_name={}, tools=(), json_schema=fact_extraction.json_schema)
    ).structured_output
    # No answer from the extractor is a grading failure, not evidence that the prompt's answer lacked the facts.
    if structured_output is None:
        raise SessionFailedException("the fact extraction session returned no structured output")
    try:
        return ExtractedFacts(reported_value_by_fact_name=read_reported_values(structured_output, fact_extraction.required_fact_names))
    except InvalidJsonException as malformation:
        raise SessionFailedException(f"the fact extraction session returned facts that do not fit the schema: {malformation}") from malformation


def read_reported_values(structured_output: JsonObject, required_fact_names: Sequence[str]) -> dict[str, str | None]:
    missing_fact_names: list[str] = [fact_name for fact_name in required_fact_names if fact_name not in structured_output]
    if missing_fact_names:
        raise InvalidJsonException(f"{EXTRACTED_FACTS_LOCATION}: the required facts {missing_fact_names} are missing")
    return {fact_name: as_fact_text(structured_output[fact_name], fact_name) for fact_name in structured_output}


def as_fact_text(reported_value: object, fact_name: str) -> str | None:
    if reported_value is None or isinstance(reported_value, str):
        return reported_value
    if not isinstance(reported_value, bool | int | float):
        raise InvalidJsonException(f"{EXTRACTED_FACTS_LOCATION}: '{fact_name}' must be a string, number, true, false or null")
    return json.dumps(reported_value)


def judge(rubric_text: str, answer: str) -> JudgeVerdict:
    """LLM-as-judge: a separate session applies a written rubric and returns pass/fail with a reason."""
    prompt: str = (
        "# Grading task\n\nApply the rubric exactly as written to the answer. Give a one- or two-sentence reason.\n\n"
        "If the answer fails because an amount it states contradicts a reference value in the rubric, list each such amount in "
        "disputed_amounts: what it measures, the amount as the answer states it, and the reference value as the rubric states it. "
        "Leave disputed_amounts empty when the answer passes, and do not list an amount that only disagrees with the answer's own tables.\n\n"
        f"<rubric>\n{rubric_text}\n</rubric>\n\n<answer>\n{answer}\n</answer>\n"
    )
    verdict: JsonObject | None = run_claude(
        SessionRequest(prompt, GRADER_MODEL, GRADER_EFFORT, content_by_file_name={}, tools=(), json_schema=JUDGE_VERDICT_SCHEMA)
    ).structured_output
    # A judge that gives no verdict has not judged; treating that as "failed" would blame the prompt for the grader.
    if verdict is None:
        raise SessionFailedException("the judge session returned no pass/fail verdict")
    try:
        return JudgeVerdict(
            passed=read_bool(verdict, "passed", JUDGE_VERDICT_LOCATION),
            reason=read_string(verdict, "reason", JUDGE_VERDICT_LOCATION),
            disputed_amounts=tuple(
                DisputedAmount(
                    description=read_string(disputed_amount_object, "description", JUDGE_VERDICT_LOCATION),
                    answer_amount=read_string(disputed_amount_object, "answer_amount", JUDGE_VERDICT_LOCATION),
                    reference_amount=read_string(disputed_amount_object, "reference_amount", JUDGE_VERDICT_LOCATION),
                )
                for disputed_amount_object in read_object_list(verdict, "disputed_amounts", JUDGE_VERDICT_LOCATION)
            ),
        )
    except InvalidJsonException as malformation:
        raise SessionFailedException(f"the judge session returned an unreadable verdict: {malformation}") from malformation


@dataclass(frozen=True)
class CompletedFactExtraction:
    extracted_facts: ExtractedFacts


@dataclass(frozen=True)
class ErroredFactExtraction:
    failure_description: str


type FactExtractionAttempt = CompletedFactExtraction | ErroredFactExtraction


@dataclass(frozen=True)
class CompletedJudgment:
    judge_verdict: JudgeVerdict


@dataclass(frozen=True)
class ErroredJudgment:
    failure_description: str


type JudgmentAttempt = CompletedJudgment | ErroredJudgment


def attempt_fact_extraction(answer: str, fact_extraction: FactExtraction) -> FactExtractionAttempt:
    try:
        extracted_facts: ExtractedFacts = extract_facts(answer, fact_extraction)
    except SessionFailedException as grader_failure:
        return ErroredFactExtraction(failure_description=str(grader_failure))
    return CompletedFactExtraction(extracted_facts=extracted_facts)


def attempt_judgment(rubric_text: str, answer: str) -> JudgmentAttempt:
    try:
        judge_verdict: JudgeVerdict = judge(rubric_text, answer)
    except SessionFailedException as grader_failure:
        return ErroredJudgment(failure_description=str(grader_failure))
    return CompletedJudgment(judge_verdict=judge_verdict)


# ----------------------------------------------------------------------------------------------------------
# Assert, part 1b: grade one run against every check (plain comparisons of supplied values, no sessions, no files)
# ----------------------------------------------------------------------------------------------------------


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"  # a session failed, so the check could not be judged; not a pass, but not evidence against the prompt


@dataclass(frozen=True)
class CheckGrade:
    """`causes` trace a failed check's wrong totals in the reference ledger: a short `summary` that reads the same in every
    run with the same mistake, and a `description` with the amounts. Empty when nothing could be traced."""

    check_status: CheckStatus
    reason: str
    causes: tuple[TracedCause, ...] = ()


@dataclass(frozen=True)
class RunEvidence:
    """What one run produced for grading: the trial's tool calls and what the grader sessions reported about its answer."""

    tool_calls: tuple[ToolCall, ...]
    fact_extraction_attempt: FactExtractionAttempt
    judgment_attempt_by_check_name: Mapping[str, JudgmentAttempt]


@dataclass(frozen=True)
class TrialGradeDocument:
    """The grade.json written beside each trial's answer: what the extractor read from the answer, and every check grade."""

    reported_value_by_fact_name: Mapping[str, str | None] | None  # None when the fact extraction session failed
    check_grade_by_check_name: Mapping[str, CheckGrade]


def to_check_status(*, passed: bool) -> CheckStatus:
    return CheckStatus.PASSED if passed else CheckStatus.FAILED


def is_amount_accepted(actual_amount: str | None, expected_amounts: Iterable[str]) -> bool:
    if actual_amount is None:
        return False
    try:
        amount: float = float(actual_amount.replace("$", "").replace(",", ""))
    except ValueError:
        return False
    return any(abs(amount - float(expected_amount)) <= AMOUNT_TOLERANCE for expected_amount in expected_amounts)


def grade_run(
    checks: Sequence[EvalSuiteCheck],
    expected_fact_values_by_fact_name: Mapping[str, Sequence[str]],
    reference_ledger: ReferenceLedger | None,
    run_evidence: RunEvidence,
) -> dict[str, CheckGrade]:
    check_grade_by_check_name: dict[str, CheckGrade] = {}
    for check in checks:
        match check:
            case AmountCheck() | FactValueCheck():
                check_grade_by_check_name[check.check_name] = grade_fact_check(
                    check, run_evidence.fact_extraction_attempt, expected_fact_values_by_fact_name[check.fact_name]
                )
            case ToolUseCheck():
                check_grade_by_check_name[check.check_name] = grade_tool_use_check(check, run_evidence.tool_calls)
            case JudgeCheck():
                check_grade_by_check_name[check.check_name] = grade_judge_check(check, run_evidence.judgment_attempt_by_check_name[check.check_name])
        check_grade_by_check_name[check.check_name] = add_traced_causes(
            check, check_grade_by_check_name[check.check_name], run_evidence, reference_ledger
        )
    return check_grade_by_check_name


def grade_fact_check(
    fact_check: AmountCheck | FactValueCheck, fact_extraction_attempt: FactExtractionAttempt, expected_fact_values: Sequence[str]
) -> CheckGrade:
    if isinstance(fact_extraction_attempt, ErroredFactExtraction):
        return CheckGrade(CheckStatus.ERRORED, f"fact extraction failed: {fact_extraction_attempt.failure_description}")
    actual_fact_value: str | None = fact_extraction_attempt.extracted_facts.reported_value_by_fact_name.get(fact_check.fact_name)
    match fact_check:
        case AmountCheck():
            return CheckGrade(
                to_check_status(passed=is_amount_accepted(actual_fact_value, expected_fact_values)),
                f"{fact_check.description} Expected {' or '.join(expected_fact_values)} (within {AMOUNT_TOLERANCE}); reported {actual_fact_value}",
            )
        case FactValueCheck():
            return CheckGrade(
                to_check_status(
                    passed=actual_fact_value is not None
                    and actual_fact_value.lower() in [expected_fact_value.lower() for expected_fact_value in expected_fact_values]
                ),
                f"{fact_check.description} Expected {' or '.join(expected_fact_values)} (any case); reported {actual_fact_value}",
            )


def grade_tool_use_check(tool_use_check: ToolUseCheck, tool_calls: Sequence[ToolCall]) -> CheckGrade:
    matching_tool_calls: list[ToolCall] = [
        tool_call
        for tool_call in tool_calls
        if tool_call.tool_name == tool_use_check.tool_name
        and re.search(tool_use_check.tool_input_pattern, tool_call.tool_input, TOOL_INPUT_PATTERN_FLAGS)
    ]
    errored_tool_call_count: int = sum(1 for tool_call in matching_tool_calls if tool_call.is_error)
    reason: str = (
        f"{tool_use_check.description} Expected at least one successful {tool_use_check.tool_name} call matching "
        f"'{tool_use_check.tool_input_pattern}'; found {len(matching_tool_calls)} matching calls, {errored_tool_call_count} of them errored"
    )
    return CheckGrade(to_check_status(passed=errored_tool_call_count < len(matching_tool_calls)), reason)


def grade_judge_check(judge_check: JudgeCheck, judgment_attempt: JudgmentAttempt) -> CheckGrade:
    match judgment_attempt:
        case ErroredJudgment():
            return CheckGrade(CheckStatus.ERRORED, f"the judge did not return a verdict: {judgment_attempt.failure_description}")
        case CompletedJudgment():
            return CheckGrade(
                to_check_status(passed=judgment_attempt.judge_verdict.passed),
                f"{judge_check.description} The judge said: {judgment_attempt.judge_verdict.reason}",
            )


def add_traced_causes(
    check: EvalSuiteCheck, check_grade: CheckGrade, run_evidence: RunEvidence, reference_ledger: ReferenceLedger | None
) -> CheckGrade:
    """A failed amount check is traced from the extracted amount; a failed judge check from each amount the judge disputed."""
    if check_grade.check_status != CheckStatus.FAILED or reference_ledger is None:
        return check_grade
    causes: list[TracedCause] = []
    match check:
        case AmountCheck():
            reported_amount: Decimal | None = (
                parse_quoted_amount(run_evidence.fact_extraction_attempt.extracted_facts.reported_value_by_fact_name.get(check.fact_name) or "")
                if isinstance(run_evidence.fact_extraction_attempt, CompletedFactExtraction)
                else None
            )
            ledger_bucket: LedgerBucket | None = reference_ledger.ledger_bucket_by_fact_name.get(check.fact_name)
            if reported_amount is not None and ledger_bucket is not None:
                causes.append(trace_wrong_total(reference_ledger, ledger_bucket, reported_amount))
        case JudgeCheck():
            judgment_attempt: JudgmentAttempt = run_evidence.judgment_attempt_by_check_name[check.check_name]
            if isinstance(judgment_attempt, CompletedJudgment):
                causes.extend(trace_disputed_amounts(reference_ledger, judgment_attempt.judge_verdict.disputed_amounts))
        case FactValueCheck() | ToolUseCheck():
            pass
    return CheckGrade(check_grade.check_status, check_grade.reason, tuple(causes))


def create_errored_grades(checks: Sequence[EvalSuiteCheck], error_description: str) -> dict[str, CheckGrade]:
    return {check.check_name: CheckGrade(CheckStatus.ERRORED, error_description) for check in checks}


def build_trial_grade_document(
    fact_extraction_attempt: FactExtractionAttempt, check_grade_by_check_name: Mapping[str, CheckGrade]
) -> TrialGradeDocument:
    # dataclasses.asdict expands records nested only inside real dicts, so both mappings are copied into dicts.
    reported_value_by_fact_name: dict[str, str | None] | None = (
        dict(fact_extraction_attempt.extracted_facts.reported_value_by_fact_name)
        if isinstance(fact_extraction_attempt, CompletedFactExtraction)
        else None
    )
    return TrialGradeDocument(reported_value_by_fact_name=reported_value_by_fact_name, check_grade_by_check_name=dict(check_grade_by_check_name))


# ----------------------------------------------------------------------------------------------------------
# Assert, part 1c: trace a wrong total to the ledger entries that make the difference
# ----------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EntryMistake:
    """One entry handled unlike the reference: "left out", "counted in" or "sign reversed", and how much that moved the total."""

    ledger_entry: LedgerEntry
    mistake: str
    amount_effect: Decimal
    is_plausible: bool


@dataclass(frozen=True)
class TracedCause:
    summary: str
    description: str


def compose_bucket(reference_ledger: ReferenceLedger, ledger_bucket: LedgerBucket) -> list[tuple[tuple[str, ...], list[LedgerEntry]]]:
    """The bucket's entries under the key's own policy first, then under every combination of the accepted policies that touch it."""
    entries_in_scope: list[LedgerEntry] = [
        ledger_entry
        for ledger_entry in reference_ledger.ledger_entries
        if ledger_entry.is_counted and ledger_bucket.period in (None, ledger_entry.period)
    ]
    policy_names: list[str] = list(
        dict.fromkeys(
            ledger_entry.policy_name
            for ledger_entry in entries_in_scope
            if ledger_entry.policy_name and ledger_bucket.category in (ledger_entry.category, *ledger_entry.alternative_categories)
        )
    )
    return [
        (
            applied_policy_names,
            [
                ledger_entry
                for ledger_entry in entries_in_scope
                if decide_category(ledger_entry, applied_policy_names, ledger_bucket.category) == ledger_bucket.category
            ],
        )
        for policy_count in range(len(policy_names) + 1)
        for applied_policy_names in combinations(policy_names, policy_count)
    ]


def decide_category(ledger_entry: LedgerEntry, applied_policy_names: Sequence[str], bucket_category: str) -> str:
    if ledger_entry.policy_name not in applied_policy_names:
        return ledger_entry.category
    return bucket_category if bucket_category in ledger_entry.alternative_categories else ledger_entry.alternative_categories[0]


def list_possible_mistakes(
    reference_ledger: ReferenceLedger, ledger_bucket: LedgerBucket, member_entries: Sequence[LedgerEntry]
) -> list[EntryMistake]:
    member_lines: set[int] = {member_entry.line_number for member_entry in member_entries}
    possible_mistakes: list[EntryMistake] = [
        EntryMistake(member_entry, "left out", -member_entry.amount, is_plausible=True) for member_entry in member_entries
    ]
    possible_mistakes.extend(
        EntryMistake(member_entry, "sign reversed", -2 * member_entry.amount, is_plausible=True)
        for member_entry in member_entries
        if member_entry.amount < 0
    )
    for ledger_entry in reference_ledger.ledger_entries:
        is_in_period: bool = ledger_bucket.period in (None, ledger_entry.period)
        if ledger_entry.line_number in member_lines or not (is_in_period or ledger_entry.category == ledger_bucket.category):
            continue
        # A likely duplicate or an entry an accepted policy could move here is a recognizable slip; anything else may fit by chance.
        is_plausible: bool = is_in_period and (not ledger_entry.is_counted or ledger_bucket.category in ledger_entry.alternative_categories)
        possible_mistakes.append(EntryMistake(ledger_entry, "counted in", ledger_entry.amount, is_plausible=is_plausible))
    return possible_mistakes


def find_fewest_mistakes(possible_mistakes: Sequence[EntryMistake], difference: Decimal, *, is_whole_period: bool) -> list[tuple[EntryMistake, ...]]:
    any_entry_limit: int = 1 if is_whole_period else ANY_ENTRY_MISTAKE_LIMIT
    for mistake_count in range(1, MAXIMUM_TRACED_MISTAKES + 1):
        searched_mistakes: list[EntryMistake] = (
            list(possible_mistakes) if mistake_count <= any_entry_limit else [mistake for mistake in possible_mistakes if mistake.is_plausible]
        )
        fits: list[tuple[EntryMistake, ...]] = [
            mistake_combination
            for mistake_combination in combinations(searched_mistakes, mistake_count)
            if len({mistake.ledger_entry.line_number for mistake in mistake_combination}) == mistake_count
            and abs(sum((mistake.amount_effect for mistake in mistake_combination), Decimal(0)) - difference) <= Decimal(str(AMOUNT_TOLERANCE))
        ]
        if fits:
            return sorted(
                fits, key=lambda fit: (sum(1 for mistake in fit if not mistake.is_plausible), [mistake.ledger_entry.line_number for mistake in fit])
            )
    return []


def trace_wrong_total(reference_ledger: ReferenceLedger, ledger_bucket: LedgerBucket, reported_amount: Decimal) -> TracedCause:
    """Apply the accepted policies that bring the reference closest, then find the fewest entry mistakes that make up the rest."""
    compositions: list[tuple[tuple[str, ...], list[LedgerEntry]]] = compose_bucket(reference_ledger, ledger_bucket)
    best_explained_composition: tuple[tuple[str, ...], Decimal, list[tuple[EntryMistake, ...]]] | None = None
    applied_policy_names: tuple[str, ...]
    member_entries: list[LedgerEntry]
    for applied_policy_names, member_entries in compositions:
        reference_amount: Decimal = sum((member_entry.amount for member_entry in member_entries), Decimal(0))
        difference: Decimal = reported_amount - reference_amount
        if abs(difference) <= Decimal(str(AMOUNT_TOLERANCE)):
            best_explained_composition = (applied_policy_names, reference_amount, [()])
            break
        fits: list[tuple[EntryMistake, ...]] = find_fewest_mistakes(
            list_possible_mistakes(reference_ledger, ledger_bucket, member_entries), difference, is_whole_period=ledger_bucket.period is None
        )
        if fits and (best_explained_composition is None or len(fits[0]) < len(best_explained_composition[2][0])):
            best_explained_composition = (applied_policy_names, reference_amount, fits)
    bucket_label: str = f"{ledger_bucket.category} {ledger_bucket.period or 'all periods'}"
    if best_explained_composition is None:
        own_total: Decimal = sum((member_entry.amount for member_entry in compositions[0][1]), Decimal(0))
        return TracedCause(
            summary=f"{bucket_label}: no combination of up to {MAXIMUM_TRACED_MISTAKES} entries explains the difference",
            description=(
                f"{bucket_label}: reported {reported_amount}, reference {own_total}; no combination of up to "
                f"{MAXIMUM_TRACED_MISTAKES} entries explains the difference (a broader categorization difference or an arithmetic error)."
            ),
        )
    applied_policy_names, reference_amount, fits = best_explained_composition
    policy_clause: str = f" (under the accepted policy {', '.join(applied_policy_names)})" if applied_policy_names else ""
    if not fits[0]:
        return TracedCause(
            summary=f"{bucket_label}: matches the reference{policy_clause}",
            description=f"{bucket_label}: reported {reported_amount} matches the reference{policy_clause}.",
        )
    mistakes_text: str = " and ".join(describe_mistake(entry_mistake, ledger_bucket) for entry_mistake in fits[0])
    others_clause: str = f" (or one of {len(fits) - 1} other equally simple combinations)" if len(fits) > 1 else ""
    return TracedCause(
        summary=f"{bucket_label}{policy_clause}: {mistakes_text}{others_clause}",
        description=(
            f"{bucket_label}: reported {reported_amount}, reference {reference_amount}{policy_clause}, a difference of "
            f"{reported_amount - reference_amount:+}. Explained by: {mistakes_text}{others_clause}."
        ),
    )


def describe_mistake(entry_mistake: EntryMistake, ledger_bucket: LedgerBucket) -> str:
    ledger_entry: LedgerEntry = entry_mistake.ledger_entry
    entry_text: str = f'line {ledger_entry.line_number} "{" ".join(ledger_entry.source_text.split())}" ({entry_mistake.amount_effect:+})'
    if entry_mistake.mistake != "counted in":
        return f"{entry_mistake.mistake}: {entry_text}"
    if not ledger_entry.is_counted:
        return f"counted in: {entry_text}, which the reference does not count ({ledger_entry.note})"
    if ledger_bucket.period not in (None, ledger_entry.period):
        return f"counted in: {entry_text}, which the reference puts in {ledger_entry.period}"
    return f"counted in: {entry_text}, which the reference puts in {ledger_entry.category}"


def trace_disputed_amounts(reference_ledger: ReferenceLedger, disputed_amounts: Sequence[DisputedAmount]) -> list[TracedCause]:
    """The judge quotes the reference value it compared with; the one ledger bucket with that total is what the answer got wrong."""
    traced_causes: list[TracedCause] = []
    for disputed_amount in disputed_amounts:
        answer_amount: Decimal | None = parse_quoted_amount(disputed_amount.answer_amount)
        ledger_bucket: LedgerBucket | None = find_bucket_with_total(reference_ledger, disputed_amount.reference_amount, disputed_amount.description)
        if answer_amount is not None and ledger_bucket is not None:
            traced_cause: TracedCause = trace_wrong_total(reference_ledger, ledger_bucket, answer_amount)
            if traced_cause.summary not in [kept_cause.summary for kept_cause in traced_causes]:
                traced_causes.append(traced_cause)
    return traced_causes


def find_bucket_with_total(reference_ledger: ReferenceLedger, reference_amount_text: str, description: str) -> LedgerBucket | None:
    """None unless exactly one bucket (or one set of entries) has the quoted total; a guessed bucket would trace a coincidence."""
    reference_amount: Decimal | None = parse_quoted_amount(reference_amount_text)
    if reference_amount is None:
        return None
    categories: list[str] = list(dict.fromkeys(ledger_entry.category for ledger_entry in reference_ledger.ledger_entries))
    periods: list[str | None] = [*sorted({ledger_entry.period for ledger_entry in reference_ledger.ledger_entries}), None]
    bucket_by_member_lines: dict[frozenset[int], LedgerBucket] = {}
    for period in periods:
        for category in categories:
            ledger_bucket: LedgerBucket = LedgerBucket(category, period)
            member_entries: list[LedgerEntry]
            for _, member_entries in compose_bucket(reference_ledger, ledger_bucket):
                total: Decimal = sum((member_entry.amount for member_entry in member_entries), Decimal(0))
                # "about $2,996" matches a total that rounds to it; an empty bucket's zero matches too much to mean anything.
                is_match: bool = (
                    total.quantize(Decimal(1), rounding=ROUND_HALF_UP) == reference_amount
                    if "." not in reference_amount_text
                    else abs(total - reference_amount) <= Decimal(str(AMOUNT_TOLERANCE))
                )
                if member_entries and is_match:
                    bucket_by_member_lines.setdefault(frozenset(member_entry.line_number for member_entry in member_entries), ledger_bucket)
    matching_buckets: list[LedgerBucket] = list(dict.fromkeys(bucket_by_member_lines.values()))
    if len(matching_buckets) > 1:
        matching_buckets = [ledger_bucket for ledger_bucket in matching_buckets if ledger_bucket.category.lower() in description.lower()]
    return matching_buckets[0] if len(matching_buckets) == 1 else None


def parse_quoted_amount(amount_text: str) -> Decimal | None:
    amount_match: re.Match[str] | None = AMOUNT_TEXT_PATTERN.search(amount_text)
    if amount_match is None:
        return None
    try:
        return Decimal(re.sub(r"[\s$,]", "", amount_match.group()))
    except InvalidOperation:
        return None


# ----------------------------------------------------------------------------------------------------------
# Assert, part 2: pass rates per check per prompt variant
# ----------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RunGrade:
    variant_name: str
    run_number: int
    check_grade_by_check_name: Mapping[str, CheckGrade]


@dataclass(frozen=True)
class ScorecardRow:
    check_name: str
    variant_name: str
    minimum_pass_rate: float
    run_count: int
    passed_count: int
    errored_count: int
    is_gated: bool

    @property
    def pass_rate(self) -> float:
        # An errored check is not a pass, so it stays in the denominator, as in the library's scorecard.
        return self.passed_count / self.run_count if self.run_count else 0.0

    @property
    def meets_minimum_pass_rate(self) -> bool:
        return self.pass_rate >= self.minimum_pass_rate


def build_scorecard_rows(
    checks: Sequence[EvalSuiteCheck], variant_names: Sequence[str], gated_variant_names: Sequence[str], run_grades: Sequence[RunGrade]
) -> list[ScorecardRow]:
    """One row per check per prompt variant, check by check, with the variants in eval suite order inside every check."""
    scorecard_rows: list[ScorecardRow] = []
    for check in checks:
        for variant_name in variant_names:
            check_statuses: list[CheckStatus] = [
                run_grade.check_grade_by_check_name[check.check_name].check_status
                for run_grade in run_grades
                if run_grade.variant_name == variant_name
            ]
            scorecard_rows.append(
                ScorecardRow(
                    check_name=check.check_name,
                    variant_name=variant_name,
                    minimum_pass_rate=check.minimum_pass_rate,
                    run_count=len(check_statuses),
                    passed_count=check_statuses.count(CheckStatus.PASSED),
                    errored_count=check_statuses.count(CheckStatus.ERRORED),
                    is_gated=variant_name in gated_variant_names,
                )
            )
    return scorecard_rows


def render_scorecard_report(scorecard_rows: Sequence[ScorecardRow], run_grades: Sequence[RunGrade]) -> str:
    # Dictionaries keep insertion order, so the checks stay in eval suite order.
    scorecard_rows_by_check_name: dict[str, list[ScorecardRow]] = {}
    for scorecard_row in scorecard_rows:
        scorecard_rows_by_check_name.setdefault(scorecard_row.check_name, []).append(scorecard_row)
    scorecard_rows_per_check: list[list[ScorecardRow]] = list(scorecard_rows_by_check_name.values())
    variant_names: list[str] = [scorecard_row.variant_name for scorecard_row in scorecard_rows_per_check[0]] if scorecard_rows_per_check else []
    table_lines: list[str] = [f"| check | minimum | {' | '.join(variant_names)} |", "|---|---|" + "---|" * len(variant_names)]
    table_lines.extend(render_table_line(check_scorecard_rows) for check_scorecard_rows in scorecard_rows_per_check)
    failed_check_lines: list[str] = list_check_grades(run_grades, CheckStatus.FAILED)
    errored_check_lines: list[str] = list_check_grades(run_grades, CheckStatus.ERRORED)
    errored_checks_heading: str = f"Checks that errored ({len(errored_check_lines)}); each counts as not passed and is not listed above:"
    failure_cause_lines: list[str] = list_failure_causes(run_grades)
    report_lines: list[str] = [
        *table_lines,
        "",
        f"Failure causes traced in the reference ledger ({len(failure_cause_lines)}); one cause in several runs is a systematic mistake:",
        *failure_cause_lines,
        "",
        f"Checks that did not pass ({len(failed_check_lines)}):",
        *failed_check_lines,
        "",
        errored_checks_heading,
        *errored_check_lines,
    ]
    return "\n".join(report_lines) + "\n"


def list_check_grades(run_grades: Sequence[RunGrade], check_status: CheckStatus) -> list[str]:
    return [
        f"{run_grade.variant_name} run {run_grade.run_number} / {check_name}: {check_grade.reason}"
        + "".join(f" Likely cause: {traced_cause.description}" for traced_cause in check_grade.causes)
        for run_grade in run_grades
        for check_name, check_grade in run_grade.check_grade_by_check_name.items()
        if check_grade.check_status == check_status
    ]


def list_failure_causes(run_grades: Sequence[RunGrade]) -> list[str]:
    # The summary has no amounts, so one mistake made in several runs is listed once with every run that made it.
    occurrences_by_summary: dict[str, list[str]] = {}
    for run_grade in run_grades:
        for check_name, check_grade in run_grade.check_grade_by_check_name.items():
            for traced_cause in check_grade.causes:
                occurrences_by_summary.setdefault(traced_cause.summary, []).append(
                    f"{run_grade.variant_name} run {run_grade.run_number} / {check_name}"
                )
    return [
        f"- {summary} · {len(occurrences)} checks: {'; '.join(occurrences)}"
        for summary, occurrences in sorted(occurrences_by_summary.items(), key=lambda summary_and_occurrences: -len(summary_and_occurrences[1]))
    ]


def render_table_line(check_scorecard_rows: Sequence[ScorecardRow]) -> str:
    cells: list[str] = [render_scorecard_cell(scorecard_row) for scorecard_row in check_scorecard_rows]
    return f"| {check_scorecard_rows[0].check_name} | {check_scorecard_rows[0].minimum_pass_rate:.0%} | {' | '.join(cells)} |"


def render_scorecard_cell(scorecard_row: ScorecardRow) -> str:
    cell_text: str = f"{scorecard_row.passed_count}/{scorecard_row.run_count} ({scorecard_row.pass_rate:.0%})"
    return f"{cell_text}, {scorecard_row.errored_count} errored" if scorecard_row.errored_count else cell_text


def describe_row_below_minimum(scorecard_row: ScorecardRow) -> str:
    return (
        f"{scorecard_row.variant_name} / {scorecard_row.check_name}: expected at least {scorecard_row.minimum_pass_rate:.0%}, "
        f"actual {scorecard_row.pass_rate:.0%} ({scorecard_row.passed_count} of {scorecard_row.run_count} runs passed, "
        f"{scorecard_row.errored_count} errored)"
    )


def report_progress(progress_message: str) -> None:
    print(progress_message, flush=True)  # noqa: T201 - step-boundary progress, visible with `pytest -s`


# ----------------------------------------------------------------------------------------------------------
# The eval
# ----------------------------------------------------------------------------------------------------------


@pytest.mark.prompt_eval
def test_ExpenseAnalysis_WhenEachPromptRunsRepeatedlyInIsolatedSessions_ThenEveryGatedCheckMeetsItsMinimumPassRate(
    pytestconfig: pytest.Config,
) -> None:
    # Arrange: everything comes from the eval suite folder, whose references load_eval_suite has already checked.
    eval_suite: EvalSuite = load_eval_suite(EVAL_SUITE_DIRECTORY)
    variant_names: list[str] = [prompt_variant.variant_name for prompt_variant in eval_suite.prompt_variants]
    if pytestconfig.getoption("--eval-assistant") != CLAUDE_CODE_ASSISTANT:
        pytest.skip("this single-file eval drives Claude Code only; the library eval covers the other assistants")
    model: str = str(pytestconfig.getoption("--eval-model"))
    effort: str = str(pytestconfig.getoption("--eval-effort"))
    repetitions: int = int(str(pytestconfig.getoption("--eval-repetitions")))
    attachment_note: str = f"\n\n---\nAttached files (in the current working directory): {', '.join(eval_suite.content_by_input_file_name)}\n"
    run_directory: Path = create_run_directory(model, effort)
    report_progress(
        f"eval suite '{eval_suite.eval_suite_name}': {len(variant_names)} prompt variants, {repetitions} runs each, results in {run_directory}"
    )

    run_grades: list[RunGrade] = []
    for prompt_variant in eval_suite.prompt_variants:
        trial_session_request: SessionRequest = SessionRequest(
            prompt=prompt_variant.prompt_text + attachment_note,
            model=model,
            effort=effort,
            content_by_file_name=eval_suite.content_by_input_file_name,
            tools=eval_suite.trial_tool_names,
            json_schema=None,
        )
        for run_number in range(1, repetitions + 1):
            run_label: str = f"{prompt_variant.variant_name} run {run_number}/{repetitions}"
            report_progress(f"{run_label}: trial session starting")

            # Act: one isolated session per run.
            try:
                session: Session = run_claude(trial_session_request)
            except SessionFailedException as trial_failure:
                trial_error_description: str = f"the trial session did not complete: {trial_failure}"
                run_grades.append(
                    RunGrade(prompt_variant.variant_name, run_number, create_errored_grades(eval_suite.checks, trial_error_description))
                )
                report_progress(f"{run_label}: every check errored, the trial session did not complete")
                continue
            run_folder: Path = run_directory / prompt_variant.variant_name / f"run-{run_number:02d}"
            run_folder.mkdir(parents=True)
            (run_folder / "answer.md").write_text(session.answer, encoding=TEXT_ENCODING)
            (run_folder / "event_stream.jsonl").write_text(session.event_stream, encoding=TEXT_ENCODING)

            # Assert, part 1a: gather what the grader sessions report about this answer; a failed session is kept as a failed attempt.
            report_progress(f"{run_label}: grader sessions starting")
            fact_extraction_attempt: FactExtractionAttempt = attempt_fact_extraction(session.answer, eval_suite.fact_extraction)
            judgment_attempt_by_check_name: dict[str, JudgmentAttempt] = {
                check.check_name: attempt_judgment(check.rubric_text, session.answer) for check in eval_suite.checks if isinstance(check, JudgeCheck)
            }

            # Assert, part 1b: grade this run by comparing what was gathered with the expected values.
            run_evidence: RunEvidence = RunEvidence(session.tool_calls, fact_extraction_attempt, judgment_attempt_by_check_name)
            check_grade_by_check_name: dict[str, CheckGrade] = grade_run(
                eval_suite.checks, eval_suite.expected_fact_values_by_fact_name, eval_suite.reference_ledger, run_evidence
            )
            trial_grade_document: TrialGradeDocument = build_trial_grade_document(fact_extraction_attempt, check_grade_by_check_name)
            (run_folder / "grade.json").write_text(json.dumps(asdict(trial_grade_document), indent=2), encoding=TEXT_ENCODING)
            run_grades.append(RunGrade(prompt_variant.variant_name, run_number, check_grade_by_check_name))
            check_statuses: list[CheckStatus] = [check_grade.check_status for check_grade in check_grade_by_check_name.values()]
            graded_progress_message: str = (
                f"{run_label}: graded, {check_statuses.count(CheckStatus.PASSED)} passed, "
                f"{check_statuses.count(CheckStatus.FAILED)} failed, {check_statuses.count(CheckStatus.ERRORED)} errored"
            )
            report_progress(graded_progress_message)

    # Assert, part 2: pass rates against each check's minimum, for the gated variant(s) only.
    actual_scorecard_rows: list[ScorecardRow] = build_scorecard_rows(eval_suite.checks, variant_names, eval_suite.gated_variant_names, run_grades)
    scorecard_report: str = render_scorecard_report(actual_scorecard_rows, run_grades)
    (run_directory / "scorecard.md").write_text(scorecard_report, encoding=TEXT_ENCODING)
    print(scorecard_report)  # noqa: T201 - visible with `pytest -s`

    actual_gated_rows: list[ScorecardRow] = [scorecard_row for scorecard_row in actual_scorecard_rows if scorecard_row.is_gated]
    actual_rows_below_minimum: list[ScorecardRow] = [gated_row for gated_row in actual_gated_rows if not gated_row.meets_minimum_pass_rate]
    assert not actual_rows_below_minimum, (
        f"{len(actual_rows_below_minimum)} of {len(actual_gated_rows)} gated checks are below their minimum pass rate:\n"
        + "\n".join(describe_row_below_minimum(scorecard_row) for scorecard_row in actual_rows_below_minimum)
    )
