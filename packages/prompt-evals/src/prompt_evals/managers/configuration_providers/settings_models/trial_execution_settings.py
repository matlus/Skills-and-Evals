from dataclasses import dataclass


@dataclass(frozen=True)
class TrialExecutionSettings:
    maximum_concurrent_trials: int
