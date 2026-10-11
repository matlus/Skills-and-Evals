from pathlib import Path
from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsBusinessBaseException


@final
class EvalSuiteNotFoundException(PromptEvalsBusinessBaseException):
    def __init__(self, eval_suite_definition_path: Path) -> None:
        super().__init__(
            f"No eval suite definition was found at '{eval_suite_definition_path}'.",
            {"EvalSuiteDefinitionPath": str(eval_suite_definition_path)},
        )


@final
class EvalSuiteDefinitionInvalidException(PromptEvalsBusinessBaseException):
    def __init__(self, eval_suite_directory: Path, definition_problems: list[str]) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' is invalid: " + "; ".join(definition_problems),
            {"EvalSuiteDirectory": str(eval_suite_directory), "DefinitionProblemCount": len(definition_problems)},
        )
        self._definition_problems: tuple[str, ...] = tuple(definition_problems)

    @property
    def definition_problems(self) -> tuple[str, ...]:
        return self._definition_problems
