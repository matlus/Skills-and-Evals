import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final, final

from prompt_evals.managers.data_managers.eval_suite_resources.eval_suite_resources import (
    AmountCheckResource,
    CaseResource,
    CheckResource,
    EvalSuiteResource,
    FactValueCheckResource,
    JudgeCheckResource,
    LedgerEntryResource,
    ReferenceLedgerResource,
    ToolUseCheckResource,
)
from prompt_evals.managers.data_managers.eval_suite_resources.validator_eval_suite import ValidatorEvalSuite
from prompt_evals.managers.data_managers.eval_suite_resources.validator_eval_suite_resource import ValidatorEvalSuiteResource
from prompt_evals.managers.data_managers.processors.reference_ledger_totals_processor import ReferenceLedgerTotalsProcessor
from prompt_evals.managers.exceptions.eval_suite_exceptions import EvalSuiteDefinitionInvalidException, EvalSuiteNotFoundException
from prompt_evals.managers.models.eval_suite_models import (
    AmountCheckDefinition,
    CheckDefinition,
    EvalCase,
    EvalSuite,
    ExpectedFact,
    FactExtraction,
    FactValueCheckDefinition,
    InputFile,
    JudgeCheckDefinition,
    PromptVariant,
    ToolUseCheckDefinition,
)
from prompt_evals.managers.models.reference_ledger_models import AmountFactLedgerBucket, LedgerBucket, LedgerEntry, ReferenceLedger

EVAL_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
TEXT_ENCODING: Final[str] = "utf-8"


@final
class DataManagerEvalSuite:
    """Loads an eval suite folder: eval_suite.json plus every prompt, input, expected-facts, schema, and rubric file it names."""

    def load_eval_suite(self, eval_suite_directory: Path) -> EvalSuite:
        eval_suite_definition_path: Path = eval_suite_directory / EVAL_SUITE_DEFINITION_FILE_NAME
        if not eval_suite_definition_path.is_file():
            raise EvalSuiteNotFoundException(eval_suite_definition_path)
        eval_suite_resource: EvalSuiteResource = ValidatorEvalSuiteResource.parse_eval_suite(
            self._read_text(eval_suite_directory, EVAL_SUITE_DEFINITION_FILE_NAME),
            eval_suite_directory,
        )
        self._raise_if_any_referenced_file_is_missing(eval_suite_resource, eval_suite_directory)
        json_schema_text: str = self._read_text(eval_suite_directory, eval_suite_resource.fact_extraction_resource.json_schema_file)
        schema_fact_names: tuple[str, ...] = ValidatorEvalSuiteResource.parse_fact_names_from_schema(
            json_schema_text,
            eval_suite_resource.fact_extraction_resource.json_schema_file,
            eval_suite_directory,
        )
        eval_suite: EvalSuite = EvalSuite(
            eval_suite_name=eval_suite_resource.eval_suite_name,
            prompt_variants=self._load_prompt_variants(eval_suite_resource, eval_suite_directory),
            eval_cases=tuple(self._load_eval_case(case_resource, eval_suite_directory) for case_resource in eval_suite_resource.case_resources),
            check_definitions=tuple(
                self._map_check_definition(check_resource, eval_suite_directory) for check_resource in eval_suite_resource.check_resources
            ),
            fact_extraction=self._load_fact_extraction(eval_suite_resource, eval_suite_directory, json_schema_text),
            gated_variant_names=eval_suite_resource.gated_variant_names,
            trial_tool_kinds=eval_suite_resource.trial_tool_kinds,
        )
        ValidatorEvalSuite.validate(eval_suite, schema_fact_names, eval_suite_directory)
        return eval_suite

    def _load_prompt_variants(self, eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path) -> tuple[PromptVariant, ...]:
        return tuple(
            PromptVariant(
                variant_name=prompt_variant_resource.variant_name,
                prompt_text=self._read_text(eval_suite_directory, prompt_variant_resource.prompt_file),
            )
            for prompt_variant_resource in eval_suite_resource.prompt_variant_resources
        )

    def _load_fact_extraction(self, eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path, json_schema_text: str) -> FactExtraction:
        return FactExtraction(
            instructions=self._read_text(eval_suite_directory, eval_suite_resource.fact_extraction_resource.instructions_file),
            # The schema travels as a command-line argument, so it is re-serialized onto one line.
            json_schema=json.dumps(json.loads(json_schema_text), separators=(",", ":")),
        )

    def _load_eval_case(self, case_resource: CaseResource, eval_suite_directory: Path) -> EvalCase:
        return EvalCase(
            case_name=case_resource.case_name,
            input_files=self._load_input_files(case_resource, eval_suite_directory),
            expected_facts=self._load_expected_facts(case_resource, eval_suite_directory),
            reference_ledger=self._load_reference_ledger(case_resource, eval_suite_directory),
        )

    def _load_reference_ledger(self, case_resource: CaseResource, eval_suite_directory: Path) -> ReferenceLedger | None:
        if case_resource.reference_ledger_file is None:
            return None
        reference_ledger_resource: ReferenceLedgerResource = ValidatorEvalSuiteResource.parse_reference_ledger(
            self._read_text(eval_suite_directory, case_resource.reference_ledger_file),
            case_resource.reference_ledger_file,
            eval_suite_directory,
        )
        # The bucket totals are computed once here, so validation and failure diagnosis read the same totals.
        return ReferenceLedgerTotalsProcessor.total_reference_ledger(
            tuple(self._map_ledger_entry(ledger_entry_resource) for ledger_entry_resource in reference_ledger_resource.ledger_entry_resources),
            tuple(
                AmountFactLedgerBucket(
                    fact_name=amount_fact_ledger_bucket_resource.fact_name,
                    ledger_bucket=LedgerBucket(
                        category=amount_fact_ledger_bucket_resource.category, period=amount_fact_ledger_bucket_resource.period
                    ),
                )
                for amount_fact_ledger_bucket_resource in reference_ledger_resource.amount_fact_ledger_bucket_resources
            ),
        )

    @staticmethod
    def _map_ledger_entry(ledger_entry_resource: LedgerEntryResource) -> LedgerEntry:
        return LedgerEntry(
            line_number=ledger_entry_resource.line_number,
            source_text=ledger_entry_resource.source_text,
            period=ledger_entry_resource.period,
            amount=ledger_entry_resource.amount,
            category=ledger_entry_resource.category,
            alternative_categories=ledger_entry_resource.alternative_categories,
            policy_name=ledger_entry_resource.policy_name,
            is_counted=ledger_entry_resource.is_counted,
            note=ledger_entry_resource.note,
        )

    def _load_expected_facts(self, case_resource: CaseResource, eval_suite_directory: Path) -> tuple[ExpectedFact, ...]:
        accepted_values_by_fact_name: dict[str, tuple[str, ...]] = ValidatorEvalSuiteResource.parse_expected_facts(
            self._read_text(eval_suite_directory, case_resource.expected_facts_file),
            case_resource.expected_facts_file,
            eval_suite_directory,
        )
        expected_facts: list[ExpectedFact] = []
        fact_name: str
        accepted_values: tuple[str, ...]
        for fact_name, accepted_values in accepted_values_by_fact_name.items():
            expected_facts.append(ExpectedFact(fact_name=fact_name, accepted_values=accepted_values))
        return tuple(expected_facts)

    @staticmethod
    def _load_input_files(case_resource: CaseResource, eval_suite_directory: Path) -> tuple[InputFile, ...]:
        inputs_directory: Path = eval_suite_directory / case_resource.inputs_directory
        input_files: tuple[InputFile, ...] = tuple(
            InputFile(file_name=input_path.name, content=input_path.read_bytes())
            for input_path in sorted(inputs_directory.iterdir())
            if input_path.is_file()
        )
        if not input_files:
            raise EvalSuiteDefinitionInvalidException(
                eval_suite_directory, [f"case '{case_resource.case_name}' has no files in '{case_resource.inputs_directory}'"]
            )
        return input_files

    def _map_check_definition(self, check_resource: CheckResource, eval_suite_directory: Path) -> CheckDefinition:
        match check_resource:
            case AmountCheckResource():
                return AmountCheckDefinition(
                    check_name=check_resource.check_name,
                    description=check_resource.description,
                    minimum_pass_rate=check_resource.minimum_pass_rate,
                    fact_name=check_resource.fact_name,
                )
            case FactValueCheckResource():
                return FactValueCheckDefinition(
                    check_name=check_resource.check_name,
                    description=check_resource.description,
                    minimum_pass_rate=check_resource.minimum_pass_rate,
                    fact_name=check_resource.fact_name,
                )
            case ToolUseCheckResource():
                return ToolUseCheckDefinition(
                    check_name=check_resource.check_name,
                    description=check_resource.description,
                    minimum_pass_rate=check_resource.minimum_pass_rate,
                    tool_kind=check_resource.tool_kind,
                    tool_input_pattern=check_resource.tool_input_pattern,
                )
            case JudgeCheckResource():
                return JudgeCheckDefinition(
                    check_name=check_resource.check_name,
                    description=check_resource.description,
                    minimum_pass_rate=check_resource.minimum_pass_rate,
                    rubric=self._read_text(eval_suite_directory, check_resource.rubric_file),
                )

    @staticmethod
    def _raise_if_any_referenced_file_is_missing(eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path) -> None:
        referenced_file_names: tuple[str, ...] = DataManagerEvalSuite._collect_referenced_file_names(eval_suite_resource)
        definition_problems: list[str] = [
            *DataManagerEvalSuite._find_missing_referenced_files(eval_suite_directory, referenced_file_names),
            *DataManagerEvalSuite._find_missing_inputs_directories(eval_suite_resource, eval_suite_directory),
            *DataManagerEvalSuite._find_referenced_files_inside_inputs(eval_suite_resource, eval_suite_directory, referenced_file_names),
        ]
        if definition_problems:
            raise EvalSuiteDefinitionInvalidException(eval_suite_directory, definition_problems)

    @staticmethod
    def _collect_referenced_file_names(eval_suite_resource: EvalSuiteResource) -> tuple[str, ...]:
        return (
            *(prompt_variant_resource.prompt_file for prompt_variant_resource in eval_suite_resource.prompt_variant_resources),
            *(case_resource.expected_facts_file for case_resource in eval_suite_resource.case_resources),
            *(
                case_resource.reference_ledger_file
                for case_resource in eval_suite_resource.case_resources
                if case_resource.reference_ledger_file is not None
            ),
            eval_suite_resource.fact_extraction_resource.instructions_file,
            eval_suite_resource.fact_extraction_resource.json_schema_file,
            *(check_resource.rubric_file for check_resource in eval_suite_resource.check_resources if isinstance(check_resource, JudgeCheckResource)),
        )

    @staticmethod
    def _find_missing_referenced_files(eval_suite_directory: Path, referenced_file_names: Iterable[str]) -> list[str]:
        return [
            f"the file '{referenced_file_name}' does not exist"
            for referenced_file_name in referenced_file_names
            if not (eval_suite_directory / referenced_file_name).is_file()
        ]

    @staticmethod
    def _find_missing_inputs_directories(eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path) -> list[str]:
        return [
            f"the inputs directory '{case_resource.inputs_directory}' of case '{case_resource.case_name}' does not exist"
            for case_resource in eval_suite_resource.case_resources
            if not (eval_suite_directory / case_resource.inputs_directory).is_dir()
        ]

    @staticmethod
    def _find_referenced_files_inside_inputs(
        eval_suite_resource: EvalSuiteResource, eval_suite_directory: Path, referenced_file_names: Sequence[str]
    ) -> list[str]:
        # Every file in a case's inputs directory is copied into the trial's sandbox, where the model under test can read it.
        return [
            f"the file '{referenced_file_name}' is inside the inputs directory of case '{case_resource.case_name}', so the trial could read it"
            for case_resource in eval_suite_resource.case_resources
            for referenced_file_name in referenced_file_names
            if (eval_suite_directory / referenced_file_name)
            .resolve()
            .is_relative_to((eval_suite_directory / case_resource.inputs_directory).resolve())
        ]

    @staticmethod
    def _read_text(eval_suite_directory: Path, relative_file_name: str) -> str:
        try:
            return (eval_suite_directory / relative_file_name).read_text(encoding=TEXT_ENCODING)
        except UnicodeDecodeError as unicode_decode_error:
            raise EvalSuiteDefinitionInvalidException(
                eval_suite_directory, [f"the file '{relative_file_name}' is not valid {TEXT_ENCODING} text"]
            ) from unicode_decode_error
