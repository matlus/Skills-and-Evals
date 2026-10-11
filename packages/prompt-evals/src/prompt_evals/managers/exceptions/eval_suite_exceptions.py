"""Why an eval suite cannot be loaded. Each failure has its own type and one raise site.

A validator that collects every problem in one pass raises one type of its own that carries them all. The suite is
supplied by the caller, so the whole family is business.
"""

from abc import ABC
from collections.abc import Sequence
from pathlib import Path
from typing import Final, final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsBusinessBaseException

EVAL_SUITE_DIRECTORY_CONTEXT_NAME: Final[str] = "EvalSuiteDirectory"
FILE_NAME_CONTEXT_NAME: Final[str] = "FileName"


class EvalSuiteBaseException(PromptEvalsBusinessBaseException, ABC):
    """The eval suite the caller supplied cannot be used."""


class EvalSuiteValidationBaseException(EvalSuiteBaseException, ABC):
    """Every problem one validation pass found, reported together so the suite author fixes them at once."""

    def __init__(self, eval_suite_directory: Path, problem_summary: str, definition_problems: Sequence[str]) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' {problem_summary}: " + "; ".join(definition_problems),
            {EVAL_SUITE_DIRECTORY_CONTEXT_NAME: str(eval_suite_directory), "DefinitionProblemCount": len(definition_problems)},
        )
        self._definition_problems: tuple[str, ...] = tuple(definition_problems)

    @property
    def definition_problems(self) -> tuple[str, ...]:
        return self._definition_problems


@final
class EvalSuiteNotFoundException(EvalSuiteBaseException):
    def __init__(self, eval_suite_definition_path: Path) -> None:
        super().__init__(
            f"No eval suite definition was found at '{eval_suite_definition_path}'.",
            {"EvalSuiteDefinitionPath": str(eval_suite_definition_path)},
        )


@final
class EvalSuiteFileNotUtf8Exception(EvalSuiteBaseException):
    def __init__(self, eval_suite_directory: Path, file_name: str, text_encoding: str) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' is invalid: the file '{file_name}' is not valid {text_encoding} text.",
            {EVAL_SUITE_DIRECTORY_CONTEXT_NAME: str(eval_suite_directory), FILE_NAME_CONTEXT_NAME: file_name, "TextEncoding": text_encoding},
        )


@final
class EvalSuiteFileNotJsonException(EvalSuiteBaseException):
    def __init__(self, eval_suite_directory: Path, file_name: str, json_error: str) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' is invalid: {file_name} is not valid JSON: {json_error}",
            {EVAL_SUITE_DIRECTORY_CONTEXT_NAME: str(eval_suite_directory), FILE_NAME_CONTEXT_NAME: file_name, "JsonError": json_error},
        )


@final
class EvalSuiteFileNotJsonObjectException(EvalSuiteBaseException):
    def __init__(self, eval_suite_directory: Path, file_name: str, held_type_name: str) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' is invalid: {file_name} must contain a JSON object; it holds {held_type_name}",
            {EVAL_SUITE_DIRECTORY_CONTEXT_NAME: str(eval_suite_directory), FILE_NAME_CONTEXT_NAME: file_name, "HeldType": held_type_name},
        )


@final
class EvalSuiteCaseInputsEmptyException(EvalSuiteBaseException):
    def __init__(self, eval_suite_directory: Path, case_name: str, inputs_directory: str) -> None:
        super().__init__(
            f"The eval suite in '{eval_suite_directory}' is invalid: case '{case_name}' has no files in '{inputs_directory}'",
            {EVAL_SUITE_DIRECTORY_CONTEXT_NAME: str(eval_suite_directory), "CaseName": case_name, "InputsDirectory": inputs_directory},
        )


@final
class EvalSuiteFileValidationException(EvalSuiteValidationBaseException):
    """The content of eval_suite.json, an expected-facts file, a reference ledger, or the fact schema is invalid."""

    def __init__(self, eval_suite_directory: Path, definition_problems: Sequence[str]) -> None:
        super().__init__(eval_suite_directory, "has files whose content is invalid", definition_problems)


@final
class EvalSuiteFileReferenceValidationException(EvalSuiteValidationBaseException):
    """eval_suite.json names files or inputs directories that are missing, or answer-key files a trial could read."""

    def __init__(self, eval_suite_directory: Path, definition_problems: Sequence[str]) -> None:
        super().__init__(eval_suite_directory, "references files it cannot use", definition_problems)


@final
class EvalSuiteValidationException(EvalSuiteValidationBaseException):
    """The loaded suite breaks a rule that no single file can check on its own."""

    def __init__(self, eval_suite_directory: Path, definition_problems: Sequence[str]) -> None:
        super().__init__(eval_suite_directory, "is invalid", definition_problems)
