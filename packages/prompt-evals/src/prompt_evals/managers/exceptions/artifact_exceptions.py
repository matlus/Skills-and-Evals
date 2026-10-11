from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalBaseException


@final
class ArtifactCallbackException(PromptEvalsTechnicalBaseException):
    def __init__(self, artifact_type: str, filename_suffix: str, artifact_origin: str) -> None:
        super().__init__(
            f"The host's artifact callback failed to persist the {artifact_type} artifact '{filename_suffix}' of {artifact_origin}.",
            {"ArtifactType": artifact_type, "FilenameSuffix": filename_suffix, "ArtifactOrigin": artifact_origin},
        )
