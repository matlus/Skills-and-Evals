from abc import ABC, abstractmethod

from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome


class ProcessRunnerBase(ABC):
    """The wire under a coding-assistant CLI gateway: start a process, feed it stdin, collect its output.

    Implementations raise ProcessStartFailedException when the process cannot be created, ProcessContainmentFailedException
    when it started but cannot be contained with the processes it starts, ProcessResumeFailedException when it was created
    suspended to be contained and cannot be resumed, and ProcessTimedOutException when it outlives its timeout (after ending
    it and every process it started).
    The runner does not know which CLI it ran, so translating these into exceptions that name the CLI is the gateway's job.
    """

    @abstractmethod
    async def run_process(self, process_invocation: ProcessInvocation) -> ProcessOutcome: ...
