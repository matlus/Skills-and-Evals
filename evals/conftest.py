import pytest
from prompt_eval_options import PromptEvalOptions

from prompt_evals import CodingAssistant, EffortLevel


def pytest_addoption(parser: pytest.Parser) -> None:
    prompt_eval_options_group: pytest.OptionGroup = parser.getgroup("prompt evals")
    prompt_eval_options_group.addoption(
        "--eval-assistant",
        default=CodingAssistant.CLAUDE_CODE.value,
        choices=[coding_assistant.value for coding_assistant in CodingAssistant],
        help="Coding assistant the prompts are evaluated in (default: claude_code)",
    )
    prompt_eval_options_group.addoption("--eval-model", default="sonnet", help="Model the prompts are evaluated on (default: sonnet)")
    prompt_eval_options_group.addoption(
        "--eval-effort",
        default=EffortLevel.MEDIUM.value,
        choices=[effort_level.value for effort_level in EffortLevel],
        help="Effort level (default: medium)",
    )
    prompt_eval_options_group.addoption("--eval-repetitions", type=int, default=5, help="Isolated runs per prompt variant per case (default: 5)")


@pytest.fixture
def prompt_eval_options(request: pytest.FixtureRequest) -> PromptEvalOptions:
    return PromptEvalOptions(
        coding_assistant=CodingAssistant(request.config.getoption("--eval-assistant")),
        model_name=str(request.config.getoption("--eval-model")),
        effort_level=EffortLevel(request.config.getoption("--eval-effort")),
        repetitions=int(str(request.config.getoption("--eval-repetitions"))),
    )
