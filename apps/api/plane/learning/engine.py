import logging
from django.utils import timezone
from datetime import timedelta
from plane.signals.models import Outcome, ProductMemory, GeneratedSpec
from plane.signals import supermemory as sm

logger = logging.getLogger(__name__)

class LearningEngine:
    @classmethod
    def analyze_outcome(cls, outcome_id: str):
        try:
            outcome = Outcome.objects.select_related("spec", "workspace").get(id=outcome_id)
        except Outcome.DoesNotExist:
            return

        spec = outcome.spec
        
        # Memory Decay
        cls.decay_memories(outcome.workspace)
        
        # Track Prediction Accuracy
        prediction_feedback = ""
        predicted_type = getattr(spec, "predicted_failure_type", "none")
        if predicted_type != "none":
            if outcome.predicted_failure_matched:
                prediction_feedback = f" Prediction '{predicted_type}' was ACCURATE."
            else:
                prediction_feedback = f" Prediction '{predicted_type}' was INCORRECT (actual: {getattr(outcome, 'failure_type', 'none')})."
        
        # Analyze why success/failure happened, pattern detection
        if outcome.result == Outcome.Result.FAILURE:
            failure_type = getattr(outcome, 'failure_type', 'unknown')
            
            # Clustering: look for recent similar failures
            recent_failures = Outcome.objects.filter(
                workspace=outcome.workspace,
                result=Outcome.Result.FAILURE,
                failure_type=failure_type,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            if recent_failures > 2:
                summary = f"Recurring Pattern: {failure_type} occurs frequently in recent specs. Notes: {outcome.notes}.{prediction_feedback}"
            else:
                summary = f"Feature '{spec.title}' failed due to {failure_type}. Notes: {outcome.notes}.{prediction_feedback}"
                
            success_weight = max(0.1, 0.5 - (0.1 * getattr(outcome, 'retry_count', 0)))
            if outcome.predicted_failure_matched:
                success_weight += 0.2 # Reward accurate predictions even on failure
        elif outcome.result == Outcome.Result.SUCCESS:
            confidence = getattr(outcome, 'confidence_score', 1.0)
            summary = f"Feature '{spec.title}' succeeded with confidence {confidence:.2f}. Code patterns worked well.{prediction_feedback}"
            success_weight = 1.0 + (0.5 * confidence)
            if predicted_type != "none" and outcome.predicted_failure_matched:
                success_weight += 0.3 # High reward if predicted failure was successfully avoided
        else:
            summary = f"Outcome for {spec.title} was {outcome.result}.{prediction_feedback}"
            success_weight = 1.0

        cls.store_learning(outcome, summary, success_weight)
        cls.update_prioritization(outcome)

    @classmethod
    def decay_memories(cls, workspace):
        # Decay memories older than 30 days
        cutoff = timezone.now() - timedelta(days=30)
        from django.db.models import F
        ProductMemory.objects.filter(
            workspace=workspace,
            created_at__lt=cutoff
        ).update(relevance_score=F('relevance_score') * 0.8)

    @classmethod
    def generate_learning_summary(cls, outcome: Outcome) -> str:
        return f"Learning Summary for {outcome.spec.title}: Result was {outcome.result}. Notes: {outcome.notes}"

    @classmethod
    def store_learning(cls, outcome: Outcome, summary: str, success_weight: float):
        ProductMemory.objects.create(
            workspace=outcome.workspace,
            category=ProductMemory.Category.SPEC_REFERENCE,
            title=f"Learning from {outcome.spec.title}",
            summary=summary,
            spec=outcome.spec,
            relevance_score=1.0,
            success_weight=success_weight
        )
        
        try:
            sm.add_document(
                outcome.workspace.slug,
                f"[LEARNING] {summary}",
                metadata={"type": "learning", "outcome_id": str(outcome.id), "success_weight": success_weight}
            )
        except Exception as e:
            logger.warning("Failed to store learning in supermemory: %s", e)

    @classmethod
    def update_prioritization(cls, outcome: Outcome):
        workspace = outcome.workspace
        from django.db.models import F
        if outcome.result == Outcome.Result.SUCCESS:
            GeneratedSpec.objects.filter(workspace=workspace, status=GeneratedSpec.Status.PROPOSED).update(
                priority_score=F('priority_score') * 1.1
            )
        elif outcome.result == Outcome.Result.FAILURE:
            GeneratedSpec.objects.filter(workspace=workspace, status=GeneratedSpec.Status.PROPOSED).update(
                priority_score=F('priority_score') * 0.9
            )
