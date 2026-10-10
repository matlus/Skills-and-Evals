import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from acceptance_support.random_data_generator import RandomDataGenerator

BASELINE_VARIANT_NAME: Final[str] = "baseline"
CANDIDATE_VARIANT_NAME: Final[str] = "candidate"
CASE_NAME: Final[str] = "case-one"
TOTAL_AMOUNT_CHECK_NAME: Final[str] = "total-amount"
STATUS_VALUE_CHECK_NAME: Final[str] = "status-value"
CODE_EXECUTED_CHECK_NAME: Final[str] = "code-executed"
TABLES_FIRST_CHECK_NAME: Final[str] = "tables-first"
TOTAL_FACT_NAME: Final[str] = "total"
STATUS_FACT_NAME: Final[str] = "status"
EXPECTED_STATUS: Final[str] = "over"
TRIAL_TOOL_KINDS: Final[tuple[str, ...]] = ("shell", "read_file")
PROMPTS_DIRECTORY_NAME: Final[str] = "prompts"
CASES_DIRECTORY_NAME: Final[str] = "cases"
INPUTS_DIRECTORY_NAME: Final[str] = "inputs"
GRADING_DIRECTORY_NAME: Final[str] = "grading"
EXPECTED_FACTS_FILE_NAME: Final[str] = "expected_facts.json"
BASELINE_PROMPT_FILE: Final[str] = f"{PROMPTS_DIRECTORY_NAME}/baseline.md"
CANDIDATE_PROMPT_FILE: Final[str] = f"{PROMPTS_DIRECTORY_NAME}/candidate.md"
FACT_EXTRACTION_INSTRUCTIONS_FILE: Final[str] = f"{GRADING_DIRECTORY_NAME}/instructions.md"
FACT_EXTRACTION_SCHEMA_FILE: Final[str] = f"{GRADING_DIRECTORY_NAME}/schema.json"
TABLES_FIRST_RUBRIC_FILE: Final[str] = f"{GRADING_DIRECTORY_NAME}/tables_first.md"
CASE_DIRECTORY: Final[str] = f"{CASES_DIRECTORY_NAME}/{CASE_NAME}"
CASE_INPUTS_DIRECTORY: Final[str] = f"{CASE_DIRECTORY}/{INPUTS_DIRECTORY_NAME}"
CASE_EXPECTED_FACTS_FILE: Final[str] = f"{CASE_DIRECTORY}/{EXPECTED_FACTS_FILE_NAME}"
CHECK_NAMES_IN_SUITE_ORDER: Final[tuple[str, ...]] = (
    TOTAL_AMOUNT_CHECK_NAME,
    STATUS_VALUE_CHECK_NAME,
    CODE_EXECUTED_CHECK_NAME,
    TABLES_FIRST_CHECK_NAME,
)


@dataclass(frozen=True)
class SampleEvalSuite:
    eval_suite_directory: Path
    eval_suite_name: str
    baseline_prompt_text: str
    candidate_prompt_text: str
    # Sorted, as the sandbox lists them.
    input_file_names: tuple[str, ...]
    expected_total_amount: str
    rubric_marker: str
    check_descriptions_in_eval_suite_order: tuple[str, ...]


class SampleEvalSuiteBuilder:
    """Writes a small but complete eval suite: two variants (one gated), one case, and one check of every grader kind."""

    @staticmethod
    def write_sample_eval_suite(eval_suite_directory: Path) -> SampleEvalSuite:
        eval_suite_name: str = f"suite-{RandomDataGenerator.create_random_word()}"
        baseline_prompt_text: str = f"Baseline prompt. {RandomDataGenerator.create_random_sentence()}"
        candidate_prompt_text: str = f"Candidate prompt. {RandomDataGenerator.create_random_sentence()}"
        expected_total_amount: str = RandomDataGenerator.create_random_amount_text()
        rubric_marker: str = f"rubric-{RandomDataGenerator.create_random_word()}"
        input_file_names: tuple[str, ...] = tuple(sorted(f"{RandomDataGenerator.create_random_word()}.txt" for _ in range(2)))
        check_descriptions_in_eval_suite_order: tuple[str, ...] = tuple(
            RandomDataGenerator.create_random_sentence() for _ in CHECK_NAMES_IN_SUITE_ORDER
        )

        SampleEvalSuiteBuilder._write_text(eval_suite_directory / BASELINE_PROMPT_FILE, baseline_prompt_text)
        SampleEvalSuiteBuilder._write_text(eval_suite_directory / CANDIDATE_PROMPT_FILE, candidate_prompt_text)
        for input_file_name in input_file_names:
            SampleEvalSuiteBuilder._write_text(
                eval_suite_directory / CASE_INPUTS_DIRECTORY / input_file_name, RandomDataGenerator.create_random_sentence()
            )
        SampleEvalSuiteBuilder._write_json(
            eval_suite_directory / CASE_EXPECTED_FACTS_FILE,
            {"expected_facts": {TOTAL_FACT_NAME: [expected_total_amount], STATUS_FACT_NAME: [EXPECTED_STATUS]}},
        )
        SampleEvalSuiteBuilder._write_text(eval_suite_directory / FACT_EXTRACTION_INSTRUCTIONS_FILE, RandomDataGenerator.create_random_sentence())
        SampleEvalSuiteBuilder._write_json(
            eval_suite_directory / FACT_EXTRACTION_SCHEMA_FILE,
            {
                "type": "object",
                "required": [TOTAL_FACT_NAME, STATUS_FACT_NAME],
                "properties": {TOTAL_FACT_NAME: {"type": ["string", "null"]}, STATUS_FACT_NAME: {"type": "string"}},
            },
        )
        SampleEvalSuiteBuilder._write_text(eval_suite_directory / TABLES_FIRST_RUBRIC_FILE, f"{rubric_marker}: PASS if tables come first.")
        SampleEvalSuiteBuilder.write_eval_suite_definition(
            eval_suite_directory, SampleEvalSuiteBuilder._create_eval_suite_definition(eval_suite_name, check_descriptions_in_eval_suite_order)
        )
        return SampleEvalSuite(
            eval_suite_directory=eval_suite_directory,
            eval_suite_name=eval_suite_name,
            baseline_prompt_text=baseline_prompt_text,
            candidate_prompt_text=candidate_prompt_text,
            input_file_names=input_file_names,
            expected_total_amount=expected_total_amount,
            rubric_marker=rubric_marker,
            check_descriptions_in_eval_suite_order=check_descriptions_in_eval_suite_order,
        )

    @staticmethod
    def create_eval_suite_definition() -> dict[str, object]:
        return SampleEvalSuiteBuilder._create_eval_suite_definition(
            f"suite-{RandomDataGenerator.create_random_word()}",
            tuple(RandomDataGenerator.create_random_sentence() for _ in CHECK_NAMES_IN_SUITE_ORDER),
        )

    @staticmethod
    def _create_eval_suite_definition(eval_suite_name: str, check_descriptions_in_eval_suite_order: tuple[str, ...]) -> dict[str, object]:
        total_amount_description: str
        status_value_description: str
        code_executed_description: str
        tables_first_description: str
        total_amount_description, status_value_description, code_executed_description, tables_first_description = (
            check_descriptions_in_eval_suite_order
        )
        return {
            "eval_suite_name": eval_suite_name,
            "prompt_variants": [
                {"variant_name": BASELINE_VARIANT_NAME, "prompt_file": BASELINE_PROMPT_FILE},
                {"variant_name": CANDIDATE_VARIANT_NAME, "prompt_file": CANDIDATE_PROMPT_FILE},
            ],
            "gated_variant_names": [CANDIDATE_VARIANT_NAME],
            "trial_tool_kinds": list(TRIAL_TOOL_KINDS),
            "cases": [
                {
                    "case_name": CASE_NAME,
                    "inputs_directory": CASE_INPUTS_DIRECTORY,
                    "expected_facts_file": CASE_EXPECTED_FACTS_FILE,
                }
            ],
            "fact_extraction": {"instructions_file": FACT_EXTRACTION_INSTRUCTIONS_FILE, "json_schema_file": FACT_EXTRACTION_SCHEMA_FILE},
            "checks": [
                {
                    "check_name": TOTAL_AMOUNT_CHECK_NAME,
                    "grader": "amount",
                    "fact_name": TOTAL_FACT_NAME,
                    "minimum_pass_rate": 1.0,
                    "description": total_amount_description,
                },
                {
                    "check_name": STATUS_VALUE_CHECK_NAME,
                    "grader": "fact_value",
                    "fact_name": STATUS_FACT_NAME,
                    "minimum_pass_rate": 1.0,
                    "description": status_value_description,
                },
                {
                    "check_name": CODE_EXECUTED_CHECK_NAME,
                    "grader": "tool_use",
                    "tool_kind": "shell",
                    "tool_input_pattern": "\\bpython",
                    "minimum_pass_rate": 1.0,
                    "description": code_executed_description,
                },
                {
                    "check_name": TABLES_FIRST_CHECK_NAME,
                    "grader": "judge",
                    "rubric_file": TABLES_FIRST_RUBRIC_FILE,
                    "minimum_pass_rate": 1.0,
                    "description": tables_first_description,
                },
            ],
        }

    @staticmethod
    def write_expected_facts(eval_suite_directory: Path, accepted_values_by_fact_name: dict[str, list[str]]) -> None:
        SampleEvalSuiteBuilder._write_json(eval_suite_directory / CASE_EXPECTED_FACTS_FILE, {"expected_facts": accepted_values_by_fact_name})

    @staticmethod
    def write_eval_suite_definition(eval_suite_directory: Path, eval_suite_definition: dict[str, object]) -> None:
        SampleEvalSuiteBuilder._write_json(eval_suite_directory / "eval_suite.json", eval_suite_definition)

    @staticmethod
    def _write_text(file_path: Path, file_text: str) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_text, encoding="utf-8")

    @staticmethod
    def _write_json(file_path: Path, json_document: dict[str, object]) -> None:
        SampleEvalSuiteBuilder._write_text(file_path, json.dumps(json_document, indent=2))
