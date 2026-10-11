import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict, cast

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.scorecard_asserter import ExpectedScorecard, ExpectedScorecardRow, ScorecardAsserter
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.scripted_cli_sessions import ScriptedAnswerSession, ScriptedClaudeEventStreamSession, ScriptedClaudeToolCall
from acceptance_support.service_locator_testing import create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

from prompt_evals import CodingAssistant, DomainFacade, EffortLevel, EvaluationRequest, Scorecard

# The real expense eval suite lives at the repository root, outside this package; 5 is this file's depth below that root
# (packages/prompt-evals/tests/acceptance/domain_facade), so moving this file must change the index.
EXPENSE_SUITE_DIRECTORY: Final[Path] = Path(__file__).resolve().parents[5] / "evals" / "expense_analysis"
EXPENSE_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
ATTACHMENT_NOTE_PREFIX: Final[str] = "Attached files (in the current working directory): "
FACT_EXTRACTION_PROMPT_HEADING: Final[str] = "# Fact extraction task"
JUDGMENT_PROMPT_HEADING: Final[str] = "# Grading task"
# The scripted process is the Claude Code CLI, so the eval suite's "shell" tool kind appears under Claude's name for it.
CLAUDE_SHELL_TOOL_NAME: Final[str] = "Bash"
# Matches the code-executed check's "\bpython" pattern, so this trial proves "code ran".
SCRIPTED_ANALYSIS_COMMAND: Final[str] = "python analyze.py"


type JsonObject = dict[str, object]


@dataclass(frozen=True)
class PromptVariantDefinition:
    variant_name: str


@dataclass(frozen=True)
class CaseDefinition:
    inputs_directory: str
    expected_facts_file: str


@dataclass(frozen=True)
class CheckDefinition:
    check_name: str


@dataclass(frozen=True)
class ExpenseEvalSuiteDefinition:
    prompt_variant_definitions: tuple[PromptVariantDefinition, ...]
    case_definitions: tuple[CaseDefinition, ...]
    check_definitions: tuple[CheckDefinition, ...]


class ExpectedFactsDocument(TypedDict):
    expected_facts: Mapping[str, Sequence[str]]


def read_eval_suite_definition() -> ExpenseEvalSuiteDefinition:
    eval_suite_definition_text: str = (EXPENSE_SUITE_DIRECTORY / EXPENSE_SUITE_DEFINITION_FILE_NAME).read_text(encoding="utf-8")
    eval_suite_document: JsonObject = cast(JsonObject, json.loads(eval_suite_definition_text))
    prompt_variant_documents: list[JsonObject] = cast(list[JsonObject], eval_suite_document["prompt_variants"])
    case_documents: list[JsonObject] = cast(list[JsonObject], eval_suite_document["cases"])
    check_documents: list[JsonObject] = cast(list[JsonObject], eval_suite_document["checks"])
    return ExpenseEvalSuiteDefinition(
        prompt_variant_definitions=tuple(
            PromptVariantDefinition(variant_name=str(prompt_variant_document["variant_name"])) for prompt_variant_document in prompt_variant_documents
        ),
        case_definitions=tuple(
            CaseDefinition(inputs_directory=str(case_document["inputs_directory"]), expected_facts_file=str(case_document["expected_facts_file"]))
            for case_document in case_documents
        ),
        check_definitions=tuple(CheckDefinition(check_name=str(check_document["check_name"])) for check_document in check_documents),
    )


def read_reference_key_fact_value_by_fact_name(case_definition: CaseDefinition) -> Mapping[str, str]:
    # Grading normalizes each reported scalar to text, so the first accepted text value is a correct report of every fact.
    expected_facts_text: str = (EXPENSE_SUITE_DIRECTORY / case_definition.expected_facts_file).read_text(encoding="utf-8")
    expected_facts_document: ExpectedFactsDocument = cast("ExpectedFactsDocument", json.loads(expected_facts_text))
    return {fact_name: accepted_values[0] for fact_name, accepted_values in expected_facts_document["expected_facts"].items()}


def read_attached_file_names(case_definition: CaseDefinition) -> str:
    inputs_directory: Path = EXPENSE_SUITE_DIRECTORY / case_definition.inputs_directory
    return ", ".join(input_path.name for input_path in sorted(inputs_directory.iterdir()) if input_path.is_file())


@pytest.mark.acceptance
class TestRunEvaluationExpenseSuiteDefinition:
    async def test_RunEvaluation_WhenEveryAnswerReportsTheReferenceKeyValues_ThenEveryExpenseCheckPassesAndTheGatePasses(self) -> None:
        # Arrange
        expense_eval_suite_definition: ExpenseEvalSuiteDefinition = read_eval_suite_definition()
        # The expense eval suite defines one case, so each variant runs one trial per repetition.
        case_definitions: tuple[CaseDefinition, ...] = expense_eval_suite_definition.case_definitions
        assert len(case_definitions) == 1, (
            "'every expense check passes and the gate passes' scripts one trial per variant, so the seeded expense suite "
            f"must define exactly one case; it now defines {len(case_definitions)}, so the seeded data no longer supports this scenario"
        )
        case_definition: CaseDefinition = case_definitions[0]
        attachment_note: str = f"{ATTACHMENT_NOTE_PREFIX}{read_attached_file_names(case_definition)}"
        reference_key_fact_value_by_fact_name: Mapping[str, str] = read_reference_key_fact_value_by_fact_name(case_definition)
        variant_names_in_eval_suite_order: tuple[str, ...] = tuple(
            prompt_variant_definition.variant_name for prompt_variant_definition in expense_eval_suite_definition.prompt_variant_definitions
        )
        check_names_in_eval_suite_order: tuple[str, ...] = tuple(
            check_definition.check_name for check_definition in expense_eval_suite_definition.check_definitions
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (attachment_note,),
            ScriptedClaudeEventStreamSession(
                final_text=RandomDataGenerator.create_random_sentence(),
                scripted_claude_tool_calls=(
                    ScriptedClaudeToolCall(
                        tool_name=CLAUDE_SHELL_TOOL_NAME,
                        tool_input={"command": SCRIPTED_ANALYSIS_COMMAND},
                        tool_result_text=RandomDataGenerator.create_random_word(),
                    ),
                ),
            ),
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING,),
            ScriptedAnswerSession(structured_output=dict(reference_key_fact_value_by_fact_name)),
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,),
            ScriptedAnswerSession(structured_output={"passed": True, "reason": RandomDataGenerator.create_random_sentence(), "disputed_amounts": []}),
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, {"PROMPT_EVALS_GRADER_MODEL": f"grader-{RandomDataGenerator.create_random_word()}"}
        )
        evaluation_request: EvaluationRequest = EvaluationRequest(
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            eval_suite_directory=EXPENSE_SUITE_DIRECTORY,
            model_name=f"model-{RandomDataGenerator.create_random_word()}",
            effort_level=EffortLevel.MEDIUM,
            repetitions=1,
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=tuple(
                ExpectedScorecardRow(
                    check_name=check_name,
                    variant_name=variant_name,
                    trial_count=evaluation_request.repetitions,
                    passed_count=evaluation_request.repetitions,
                    errored_count=0,
                    meets_minimum_pass_rate=True,
                )
                for check_name in check_names_in_eval_suite_order
                for variant_name in variant_names_in_eval_suite_order
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
