import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, final

from prompt_evals import CodingAssistant, EffortLevel, EvaluationArtifact, TrialIdentity

UNSAFE_PATH_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]+")
RUN_IDENTITY_RANDOM_BYTES: Final[int] = 3
TRIALS_DIRECTORY_NAME: Final[str] = "trials"
# Results of the PWI library (this app and the pytest gate) live apart from the minimal one-file eval's results/minimal.
PWI_RESULTS_DIRECTORY_NAME: Final[str] = "pwi"
REGRADE_RUN_MARKER: Final[str] = "regrade"
REGRADED_FROM_FILE_NAME: Final[str] = "regraded_from.txt"


@final
class ResultsDirectoryWriter:
    """The host's artifact callback: persists each artifact under one directory per evaluation run.

    Layout: <results root>/pwi/<eval suite>/<run>/, with run-level artifacts (the scorecard) at the top and each trial's
    artifacts in trials/<variant>/<case>/run-NN.
    """

    def __init__(self, run_directory: Path) -> None:
        self._run_directory: Path = run_directory

    @staticmethod
    def create_for_run(
        results_root: Path, eval_suite_name: str, coding_assistant: CodingAssistant, model_name: str, effort_level: EffortLevel
    ) -> ResultsDirectoryWriter:
        return ResultsDirectoryWriter(
            ResultsDirectoryWriter._compose_run_directory(results_root, eval_suite_name, f"{coding_assistant}-{model_name}-{effort_level}")
        )

    @staticmethod
    def create_for_regrade(
        results_root: Path, eval_suite_name: str, coding_assistant: CodingAssistant, model_name: str, effort_level: EffortLevel
    ) -> ResultsDirectoryWriter:
        """A new run directory for the regrade; the run it regrades stays as it was."""
        return ResultsDirectoryWriter(
            ResultsDirectoryWriter._compose_run_directory(
                results_root, eval_suite_name, f"{REGRADE_RUN_MARKER}-{coding_assistant}-{model_name}-{effort_level}"
            )
        )

    @staticmethod
    def _compose_run_directory(results_root: Path, eval_suite_name: str, run_description: str) -> Path:
        # Model names can contain ':' or '/' (for example provider-qualified IDs), which are not valid in folder names.
        # The random suffix keeps two runs started in the same second from writing into one folder.
        run_timestamp: str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_directory_name: str = UNSAFE_PATH_CHARACTERS.sub("-", f"{run_timestamp}-{run_description}-{secrets.token_hex(RUN_IDENTITY_RANDOM_BYTES)}")
        return results_root / PWI_RESULTS_DIRECTORY_NAME / UNSAFE_PATH_CHARACTERS.sub("-", eval_suite_name) / run_directory_name

    @property
    def run_directory(self) -> Path:
        return self._run_directory

    def write_evaluation_artifact(self, evaluation_artifact: EvaluationArtifact) -> None:
        artifact_directory: Path = self._compose_artifact_directory(evaluation_artifact.trial_identity)
        artifact_directory.mkdir(parents=True, exist_ok=True)
        (artifact_directory / evaluation_artifact.filename_suffix).write_bytes(evaluation_artifact.content)

    def write_regraded_from(self, source_run_directory: Path) -> None:
        self._run_directory.mkdir(parents=True, exist_ok=True)
        (self._run_directory / REGRADED_FROM_FILE_NAME).write_text(f"{source_run_directory.resolve()}\n", encoding="utf-8")

    def _compose_artifact_directory(self, trial_identity: TrialIdentity | None) -> Path:
        if trial_identity is None:
            return self._run_directory
        return (
            self._run_directory
            / TRIALS_DIRECTORY_NAME
            / UNSAFE_PATH_CHARACTERS.sub("-", trial_identity.variant_name)
            / UNSAFE_PATH_CHARACTERS.sub("-", trial_identity.case_name)
            / f"run-{trial_identity.repetition_number:02d}"
        )
