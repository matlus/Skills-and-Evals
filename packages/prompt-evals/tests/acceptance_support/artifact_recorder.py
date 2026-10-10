from prompt_evals import EvaluationArtifact


class ArtifactRecorder:
    """A host callback that keeps every artifact in memory so tests can inspect what was emitted."""

    def __init__(self) -> None:
        self._evaluation_artifacts: list[EvaluationArtifact] = []

    @property
    def evaluation_artifacts(self) -> tuple[EvaluationArtifact, ...]:
        return tuple(self._evaluation_artifacts)

    def record_evaluation_artifact(self, evaluation_artifact: EvaluationArtifact) -> None:
        self._evaluation_artifacts.append(evaluation_artifact)
