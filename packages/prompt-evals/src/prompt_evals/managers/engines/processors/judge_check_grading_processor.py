from typing import final

from prompt_evals.managers.models.eval_suite_models import JudgeCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus, FailedJudgment, JudgmentAttempt, SucceededJudgment
from prompt_evals.managers.models.trial_models import TrialIdentity


@final
class JudgeCheckGradingProcessor:
    """Turns a judge's verdict into the check's outcome."""

    @staticmethod
    def grade_judge_check(
        judge_check_definition: JudgeCheckDefinition, judgment_attempt: JudgmentAttempt, trial_identity: TrialIdentity
    ) -> CheckOutcome:
        match judgment_attempt:
            case SucceededJudgment(judge_verdict=judge_verdict):
                return CheckOutcome(
                    check_name=judge_check_definition.check_name,
                    trial_identity=trial_identity,
                    check_status=CheckStatus.PASSED if judge_verdict.is_passed else CheckStatus.FAILED,
                    reason=judge_verdict.reason,
                    amount_discrepancy_diagnoses=(),
                )
            case FailedJudgment(failure_description=failure_description):
                # A judge that cannot answer is a grading problem, not evidence about the prompt; it is reported as errored.
                return CheckOutcome(
                    check_name=judge_check_definition.check_name,
                    trial_identity=trial_identity,
                    check_status=CheckStatus.ERRORED,
                    reason=f"the judge did not return a verdict: {failure_description}",
                    amount_discrepancy_diagnoses=(),
                )
