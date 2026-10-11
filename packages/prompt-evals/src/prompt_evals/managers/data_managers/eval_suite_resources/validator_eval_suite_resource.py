import json
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, cast, final

from prompt_evals.managers.data_managers.eval_suite_resources.eval_suite_resources import (
    AmountCheckResource,
    AmountFactLedgerBucketResource,
    CaseResource,
    CheckHeaderResource,
    CheckResource,
    EvalSuiteResource,
    FactExtractionResource,
    FactValueCheckResource,
    GraderKindResource,
    JudgeCheckResource,
    LedgerEntryResource,
    PromptVariantResource,
    ReferenceLedgerResource,
    ToolUseCheckResource,
)
from prompt_evals.managers.exceptions.eval_suite_exceptions import (
    EvalSuiteFileNotJsonException,
    EvalSuiteFileNotJsonObjectException,
    EvalSuiteFileValidationException,
)
from prompt_evals.managers.models.eval_suite_models import ToolKind

type JsonObject = dict[str, object]


@final
class ValidatorEvalSuiteResource:
    """Parses eval_suite.json and the expected-facts and schema files into typed resources.

    Every problem found is collected and reported together, so a suite author fixes them in one pass.
    """

    EVAL_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
    PROMPT_VARIANT_LOCATION: Final[str] = "a prompt variant"
    CASE_LOCATION: Final[str] = "a case"
    CHECK_LOCATION: Final[str] = "a check"
    FACT_EXTRACTION_LOCATION: Final[str] = "fact_extraction"
    FACT_NAME_FIELD: Final[str] = "fact_name"
    NON_EMPTY_OBJECT_LIST_PROBLEM: Final[str] = "needs '{field_name}' to be a non-empty list of objects"
    # Stands in for a missing required string so parsing goes on and reports every problem in one pass. A recorded problem
    # always rejects the whole suite, so the placeholder never reaches a domain model.
    MISSING_STRING_PLACEHOLDER: Final[str] = ""

    @staticmethod
    def parse_eval_suite(eval_suite_definition_text: str, eval_suite_directory: Path) -> EvalSuiteResource:
        definition_problems: list[str] = []
        eval_suite_object: JsonObject = ValidatorEvalSuiteResource._parse_json_object(
            eval_suite_definition_text, ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, eval_suite_directory
        )
        eval_suite_resource: EvalSuiteResource = EvalSuiteResource(
            eval_suite_name=ValidatorEvalSuiteResource._read_string_or_placeholder(
                eval_suite_object, "eval_suite_name", ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
            ),
            prompt_variant_resources=tuple(
                ValidatorEvalSuiteResource._parse_prompt_variant(variant_object, definition_problems)
                for variant_object in ValidatorEvalSuiteResource._read_object_list(eval_suite_object, "prompt_variants", definition_problems)
            ),
            gated_variant_names=ValidatorEvalSuiteResource._read_string_list(
                eval_suite_object, "gated_variant_names", ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
            ),
            trial_tool_kinds=ValidatorEvalSuiteResource._parse_trial_tool_kinds(eval_suite_object, definition_problems),
            case_resources=tuple(
                ValidatorEvalSuiteResource._parse_case(case_object, definition_problems)
                for case_object in ValidatorEvalSuiteResource._read_object_list(eval_suite_object, "cases", definition_problems)
            ),
            fact_extraction_resource=ValidatorEvalSuiteResource._parse_fact_extraction(eval_suite_object, definition_problems),
            check_resources=ValidatorEvalSuiteResource._parse_checks(eval_suite_object, definition_problems),
        )
        ValidatorEvalSuiteResource._raise_if_any_problem(eval_suite_directory, definition_problems)
        return eval_suite_resource

    @staticmethod
    def parse_expected_facts(expected_facts_text: str, expected_facts_file: str, eval_suite_directory: Path) -> dict[str, tuple[str, ...]]:
        definition_problems: list[str] = []
        expected_facts_document: JsonObject = ValidatorEvalSuiteResource._parse_json_object(
            expected_facts_text, expected_facts_file, eval_suite_directory
        )
        expected_facts_object: JsonObject = ValidatorEvalSuiteResource._read_object(
            expected_facts_document, "expected_facts", expected_facts_file, definition_problems
        )
        accepted_values_by_fact_name: dict[str, tuple[str, ...]] = {
            fact_name: ValidatorEvalSuiteResource._read_string_list(expected_facts_object, fact_name, expected_facts_file, definition_problems)
            for fact_name in expected_facts_object
        }
        ValidatorEvalSuiteResource._raise_if_any_problem(eval_suite_directory, definition_problems)
        return accepted_values_by_fact_name

    @staticmethod
    def parse_reference_ledger(reference_ledger_text: str, reference_ledger_file: str, eval_suite_directory: Path) -> ReferenceLedgerResource:
        definition_problems: list[str] = []
        reference_ledger_object: JsonObject = ValidatorEvalSuiteResource._parse_json_object(
            reference_ledger_text, reference_ledger_file, eval_suite_directory
        )
        entry_objects: list[JsonObject] = ValidatorEvalSuiteResource._read_located_object_list(
            reference_ledger_object, "entries", reference_ledger_file, definition_problems
        )
        amount_facts_object: JsonObject = ValidatorEvalSuiteResource._read_object(
            reference_ledger_object, "amount_facts", reference_ledger_file, definition_problems
        )
        reference_ledger_resource: ReferenceLedgerResource = ReferenceLedgerResource(
            ledger_entry_resources=ValidatorEvalSuiteResource._parse_ledger_entries(entry_objects, reference_ledger_file, definition_problems),
            amount_fact_ledger_bucket_resources=tuple(
                ValidatorEvalSuiteResource._parse_amount_fact_ledger_bucket(
                    fact_name,
                    ValidatorEvalSuiteResource._read_object(amount_facts_object, fact_name, reference_ledger_file, definition_problems),
                    f"{reference_ledger_file} amount fact '{fact_name}'",
                    definition_problems,
                )
                for fact_name in amount_facts_object
            ),
        )
        ValidatorEvalSuiteResource._raise_if_any_problem(eval_suite_directory, definition_problems)
        return reference_ledger_resource

    @staticmethod
    def _parse_ledger_entries(
        entry_objects: Iterable[JsonObject], reference_ledger_file: str, definition_problems: list[str]
    ) -> tuple[LedgerEntryResource, ...]:
        ledger_entry_resources: list[LedgerEntryResource] = []
        entry_index: int
        entry_object: JsonObject
        for entry_index, entry_object in enumerate(entry_objects):
            # Suite authors count entries from 1.
            ledger_entry_resources.append(
                ValidatorEvalSuiteResource._parse_ledger_entry(entry_object, f"{reference_ledger_file} entry {entry_index + 1}", definition_problems)
            )
        return tuple(ledger_entry_resources)

    @staticmethod
    def _parse_ledger_entry(entry_object: JsonObject, entry_location: str, definition_problems: list[str]) -> LedgerEntryResource:
        alternative_categories: tuple[str, ...] = ValidatorEvalSuiteResource._read_string_list(
            entry_object, "alternative_categories", entry_location, definition_problems
        )
        policy_name: str | None = ValidatorEvalSuiteResource._read_optional_string(entry_object, "policy_name", entry_location, definition_problems)
        category: str = ValidatorEvalSuiteResource._read_string_or_placeholder(entry_object, "category", entry_location, definition_problems)
        # An alternative belongs to a named policy, so the entries a policy moves can switch together.
        if bool(alternative_categories) != (policy_name is not None):
            definition_problems.append(f"{entry_location} needs a 'policy_name' exactly when it lists alternative_categories")
        if category in alternative_categories:
            definition_problems.append(f"{entry_location} lists its own category '{category}' as an alternative")
        return LedgerEntryResource(
            line_number=ValidatorEvalSuiteResource._read_positive_integer(entry_object, "line_number", entry_location, definition_problems),
            source_text=ValidatorEvalSuiteResource._read_string_or_placeholder(entry_object, "source_text", entry_location, definition_problems),
            period=ValidatorEvalSuiteResource._read_string_or_placeholder(entry_object, "period", entry_location, definition_problems),
            amount=ValidatorEvalSuiteResource._read_amount(entry_object, "amount", entry_location, definition_problems),
            category=category,
            alternative_categories=alternative_categories,
            policy_name=policy_name,
            is_counted=ValidatorEvalSuiteResource._read_boolean(entry_object, "is_counted", entry_location, definition_problems),
            note=ValidatorEvalSuiteResource._read_optional_string(entry_object, "note", entry_location, definition_problems),
        )

    @staticmethod
    def _parse_amount_fact_ledger_bucket(
        fact_name: str, bucket_object: JsonObject, bucket_location: str, definition_problems: list[str]
    ) -> AmountFactLedgerBucketResource:
        return AmountFactLedgerBucketResource(
            fact_name=fact_name,
            category=ValidatorEvalSuiteResource._read_string_or_placeholder(bucket_object, "category", bucket_location, definition_problems),
            # A null period totals the category across every period.
            period=ValidatorEvalSuiteResource._read_optional_string(bucket_object, "period", bucket_location, definition_problems),
        )

    @staticmethod
    def parse_fact_names_from_schema(json_schema_text: str, json_schema_file: str, eval_suite_directory: Path) -> tuple[str, ...]:
        definition_problems: list[str] = []
        json_schema_object: JsonObject = ValidatorEvalSuiteResource._parse_json_object(json_schema_text, json_schema_file, eval_suite_directory)
        properties_object: JsonObject = ValidatorEvalSuiteResource._read_object(
            json_schema_object, "properties", json_schema_file, definition_problems
        )
        ValidatorEvalSuiteResource._raise_if_any_problem(eval_suite_directory, definition_problems)
        return tuple(properties_object)

    @staticmethod
    def _parse_prompt_variant(variant_object: JsonObject, definition_problems: list[str]) -> PromptVariantResource:
        return PromptVariantResource(
            variant_name=ValidatorEvalSuiteResource._read_string_or_placeholder(
                variant_object, "variant_name", ValidatorEvalSuiteResource.PROMPT_VARIANT_LOCATION, definition_problems
            ),
            prompt_file=ValidatorEvalSuiteResource._read_string_or_placeholder(
                variant_object, "prompt_file", ValidatorEvalSuiteResource.PROMPT_VARIANT_LOCATION, definition_problems
            ),
        )

    @staticmethod
    def _parse_case(case_object: JsonObject, definition_problems: list[str]) -> CaseResource:
        return CaseResource(
            case_name=ValidatorEvalSuiteResource._read_string_or_placeholder(
                case_object, "case_name", ValidatorEvalSuiteResource.CASE_LOCATION, definition_problems
            ),
            inputs_directory=ValidatorEvalSuiteResource._read_string_or_placeholder(
                case_object, "inputs_directory", ValidatorEvalSuiteResource.CASE_LOCATION, definition_problems
            ),
            expected_facts_file=ValidatorEvalSuiteResource._read_string_or_placeholder(
                case_object, "expected_facts_file", ValidatorEvalSuiteResource.CASE_LOCATION, definition_problems
            ),
            reference_ledger_file=ValidatorEvalSuiteResource._read_optional_string(
                case_object, "reference_ledger_file", ValidatorEvalSuiteResource.CASE_LOCATION, definition_problems
            ),
        )

    @staticmethod
    def _parse_fact_extraction(eval_suite_object: JsonObject, definition_problems: list[str]) -> FactExtractionResource:
        fact_extraction_object: JsonObject = ValidatorEvalSuiteResource._read_object(
            eval_suite_object, "fact_extraction", ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
        )
        return FactExtractionResource(
            instructions_file=ValidatorEvalSuiteResource._read_string_or_placeholder(
                fact_extraction_object, "instructions_file", ValidatorEvalSuiteResource.FACT_EXTRACTION_LOCATION, definition_problems
            ),
            json_schema_file=ValidatorEvalSuiteResource._read_string_or_placeholder(
                fact_extraction_object, "json_schema_file", ValidatorEvalSuiteResource.FACT_EXTRACTION_LOCATION, definition_problems
            ),
        )

    @staticmethod
    def _parse_checks(eval_suite_object: JsonObject, definition_problems: list[str]) -> tuple[CheckResource, ...]:
        check_resources: list[CheckResource] = []
        for check_object in ValidatorEvalSuiteResource._read_object_list(eval_suite_object, "checks", definition_problems):
            check_resource: CheckResource | None = ValidatorEvalSuiteResource._parse_check(check_object, definition_problems)
            if check_resource is not None:
                check_resources.append(check_resource)
        return tuple(check_resources)

    @staticmethod
    def _parse_check(check_object: JsonObject, definition_problems: list[str]) -> CheckResource | None:
        """None when the grader is unknown: that problem is already recorded, so the whole suite is rejected."""
        check_name: str = ValidatorEvalSuiteResource._read_string_or_placeholder(
            check_object, "check_name", ValidatorEvalSuiteResource.CHECK_LOCATION, definition_problems
        )
        check_location: str = f"check '{check_name}'"
        grader_kind: GraderKindResource | None = ValidatorEvalSuiteResource._parse_grader_kind(check_object, check_location, definition_problems)
        check_header_resource: CheckHeaderResource = CheckHeaderResource(
            check_name=check_name,
            description=ValidatorEvalSuiteResource._read_string_or_placeholder(check_object, "description", check_location, definition_problems),
            minimum_pass_rate=ValidatorEvalSuiteResource._parse_minimum_pass_rate(check_object, check_location, definition_problems),
            check_location=check_location,
        )
        match grader_kind:
            case GraderKindResource.AMOUNT:
                return AmountCheckResource(
                    check_name=check_header_resource.check_name,
                    description=check_header_resource.description,
                    minimum_pass_rate=check_header_resource.minimum_pass_rate,
                    fact_name=ValidatorEvalSuiteResource._read_string_or_placeholder(
                        check_object, ValidatorEvalSuiteResource.FACT_NAME_FIELD, check_location, definition_problems
                    ),
                )
            case GraderKindResource.FACT_VALUE:
                return FactValueCheckResource(
                    check_name=check_header_resource.check_name,
                    description=check_header_resource.description,
                    minimum_pass_rate=check_header_resource.minimum_pass_rate,
                    fact_name=ValidatorEvalSuiteResource._read_string_or_placeholder(
                        check_object, ValidatorEvalSuiteResource.FACT_NAME_FIELD, check_location, definition_problems
                    ),
                )
            case GraderKindResource.TOOL_USE:
                return ValidatorEvalSuiteResource._parse_tool_use_check(check_object, check_header_resource, definition_problems)
            case GraderKindResource.JUDGE:
                return JudgeCheckResource(
                    check_name=check_header_resource.check_name,
                    description=check_header_resource.description,
                    minimum_pass_rate=check_header_resource.minimum_pass_rate,
                    rubric_file=ValidatorEvalSuiteResource._read_string_or_placeholder(
                        check_object, "rubric_file", check_location, definition_problems
                    ),
                )
            case None:
                return None

    @staticmethod
    def _parse_tool_use_check(
        check_object: JsonObject, check_header_resource: CheckHeaderResource, definition_problems: list[str]
    ) -> ToolUseCheckResource | None:
        check_location: str = check_header_resource.check_location
        tool_input_pattern: str = ValidatorEvalSuiteResource._read_string_or_placeholder(
            check_object, "tool_input_pattern", check_location, definition_problems
        )
        tool_kind: ToolKind | None = ValidatorEvalSuiteResource._parse_tool_kind(
            ValidatorEvalSuiteResource._read_string_or_placeholder(check_object, "tool_kind", check_location, definition_problems),
            check_location,
            definition_problems,
        )
        if tool_kind is None:
            return None
        return ToolUseCheckResource(
            check_name=check_header_resource.check_name,
            description=check_header_resource.description,
            minimum_pass_rate=check_header_resource.minimum_pass_rate,
            tool_kind=tool_kind,
            tool_input_pattern=tool_input_pattern,
        )

    @staticmethod
    def _parse_trial_tool_kinds(eval_suite_object: JsonObject, definition_problems: list[str]) -> tuple[ToolKind, ...]:
        trial_tool_kinds: list[ToolKind] = []
        for tool_kind_text in ValidatorEvalSuiteResource._read_string_list(
            eval_suite_object, "trial_tool_kinds", ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
        ):
            tool_kind: ToolKind | None = ValidatorEvalSuiteResource._parse_tool_kind(
                tool_kind_text, ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
            )
            if tool_kind is not None:
                trial_tool_kinds.append(tool_kind)
        return tuple(trial_tool_kinds)

    @staticmethod
    def _parse_tool_kind(tool_kind_text: str, location: str, definition_problems: list[str]) -> ToolKind | None:
        """None when the text names no tool kind; that problem is recorded, so the whole suite is rejected."""
        try:
            return ToolKind(tool_kind_text)
        except ValueError:
            tool_kind_names: str = ", ".join(tool_kind.value for tool_kind in ToolKind)
            definition_problems.append(f"{location} has unknown tool kind '{tool_kind_text}' (expected one of {tool_kind_names})")
            return None

    @staticmethod
    def _parse_grader_kind(check_object: JsonObject, check_location: str, definition_problems: list[str]) -> GraderKindResource | None:
        grader_text: str = ValidatorEvalSuiteResource._read_string_or_placeholder(check_object, "grader", check_location, definition_problems)
        try:
            return GraderKindResource(grader_text)
        except ValueError:
            grader_names: str = ", ".join(grader_kind.value for grader_kind in GraderKindResource)
            definition_problems.append(f"{check_location} has unknown grader '{grader_text}' (expected one of {grader_names})")
            return None

    @staticmethod
    def _parse_minimum_pass_rate(check_object: JsonObject, check_location: str, definition_problems: list[str]) -> float:
        minimum_pass_rate: object = check_object.get("minimum_pass_rate")
        # Python's bool is a subclass of int, so a JSON `true` would otherwise be accepted as the rate 1.
        if not isinstance(minimum_pass_rate, int | float) or isinstance(minimum_pass_rate, bool) or not 0 <= minimum_pass_rate <= 1:
            definition_problems.append(f"{check_location} needs a minimum_pass_rate between 0 and 1")
            return 1.0
        return float(minimum_pass_rate)

    @staticmethod
    def _parse_json_object(json_text: str, file_label: str, eval_suite_directory: Path) -> JsonObject:
        try:
            parsed_document: object = json.loads(json_text)
        except json.JSONDecodeError as json_decode_error:
            raise EvalSuiteFileNotJsonException(eval_suite_directory, file_label, str(json_decode_error)) from json_decode_error
        if not isinstance(parsed_document, dict):
            raise EvalSuiteFileNotJsonObjectException(eval_suite_directory, file_label, type(parsed_document).__name__)
        return cast(JsonObject, parsed_document)

    @staticmethod
    def _read_string_or_placeholder(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> str:
        field_value: str | None = ValidatorEvalSuiteResource._read_string(json_object, field_name, location, definition_problems)
        return ValidatorEvalSuiteResource.MISSING_STRING_PLACEHOLDER if field_value is None else field_value

    @staticmethod
    def _read_string(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> str | None:
        field_value: object = json_object.get(field_name)
        if isinstance(field_value, str) and field_value.strip():
            return field_value
        definition_problems.append(f"{location} needs a non-empty string '{field_name}'")
        return None

    @staticmethod
    def _read_optional_string(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> str | None:
        field_value: object = json_object.get(field_name)
        if field_value is None:
            return None
        if isinstance(field_value, str) and field_value.strip():
            return field_value
        definition_problems.append(f"{location} needs '{field_name}' to be a non-empty string or absent")
        return None

    @staticmethod
    def _read_positive_integer(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> int:
        field_value: object = json_object.get(field_name)
        # Python's bool is a subclass of int, so a JSON `true` would otherwise be accepted as 1.
        if isinstance(field_value, int) and not isinstance(field_value, bool) and field_value > 0:
            return field_value
        definition_problems.append(f"{location} needs a positive integer '{field_name}'")
        return 0

    @staticmethod
    def _read_boolean(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> bool:
        field_value: object = json_object.get(field_name)
        if isinstance(field_value, bool):
            return field_value
        definition_problems.append(f"{location} needs a boolean '{field_name}'")
        return False

    @staticmethod
    def _read_amount(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> Decimal:
        # Amounts are strings, as in expected_facts.json, so no binary floating point ever touches money.
        amount_text: str | None = ValidatorEvalSuiteResource._read_string(json_object, field_name, location, definition_problems)
        try:
            amount: Decimal = Decimal("NaN") if amount_text is None else Decimal(amount_text)
        except InvalidOperation:
            amount = Decimal("NaN")
        if amount.is_finite():
            return amount
        if amount_text is not None:
            definition_problems.append(f"{location} has '{field_name}' '{amount_text}', which is not a plain number")
        return Decimal(0)

    @staticmethod
    def _read_located_object_list(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> list[JsonObject]:
        field_value: object = json_object.get(field_name)
        if isinstance(field_value, list) and field_value and all(isinstance(list_item, dict) for list_item in cast(list[object], field_value)):
            return cast(list[JsonObject], field_value)
        definition_problems.append(f"{location} {ValidatorEvalSuiteResource.NON_EMPTY_OBJECT_LIST_PROBLEM.format(field_name=field_name)}")
        return []

    @staticmethod
    def _read_string_list(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> tuple[str, ...]:
        field_value: object = json_object.get(field_name)
        if isinstance(field_value, list) and all(isinstance(list_item, str) for list_item in cast(list[object], field_value)):
            return tuple(cast(list[str], field_value))
        definition_problems.append(f"{location} needs '{field_name}' to be a list of strings")
        return ()

    @staticmethod
    def _read_object(json_object: JsonObject, field_name: str, location: str, definition_problems: list[str]) -> JsonObject:
        field_value: object = json_object.get(field_name)
        if isinstance(field_value, dict):
            return cast(JsonObject, field_value)
        definition_problems.append(f"{location} needs an object '{field_name}'")
        return {}

    @staticmethod
    def _read_object_list(json_object: JsonObject, field_name: str, definition_problems: list[str]) -> list[JsonObject]:
        return ValidatorEvalSuiteResource._read_located_object_list(
            json_object, field_name, ValidatorEvalSuiteResource.EVAL_SUITE_DEFINITION_FILE_NAME, definition_problems
        )

    @staticmethod
    def _raise_if_any_problem(eval_suite_directory: Path, definition_problems: list[str]) -> None:
        if definition_problems:
            raise EvalSuiteFileValidationException(eval_suite_directory, definition_problems)
