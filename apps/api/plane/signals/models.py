from django.db import models

from plane.db.models import Workspace, WorkspaceBaseModel


class Signal(WorkspaceBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="signals")
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="signals/", blank=True, null=True)
    source = models.CharField(max_length=50, default="manual")
    processing_status = models.CharField(max_length=20, default="pending")
    source_metadata = models.JSONField(default=dict, blank=True)
    supermemory_doc_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Signal"
        verbose_name_plural = "Signals"
        db_table = "signals"

    def __str__(self):
        return f"{self.title} - {self.workspace.name}"


class Insight(WorkspaceBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="insights")
    theme = models.CharField(max_length=255)
    problem = models.TextField()
    root_cause = models.TextField()
    evidence = models.JSONField(default=list)
    frequency = models.IntegerField(default=1)
    supermemory_doc_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Insight"
        verbose_name_plural = "Insights"
        db_table = "insights"

    def __str__(self):
        return f"{self.theme} ({self.frequency})"


class GeneratedSpec(WorkspaceBaseModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="specs")
    title = models.CharField(max_length=255)
    spec_json = models.JSONField(default=dict)
    agent_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)

    # Autonomous Prioritization Engine scores
    impact_score = models.FloatField(default=0.0)  # 0-10: user pain × frequency × revenue signal
    effort_score = models.FloatField(default=5.0)  # 0-10: complexity estimate
    priority_score = models.FloatField(default=0.0)  # impact / effort (auto-computed)

    # Supermemory reference
    supermemory_doc_id = models.CharField(max_length=255, blank=True, null=True)

    # Advanced Prioritization Engine v2
    confidence_score = models.FloatField(default=1.0)  # 0-2: signal volume + clustering consistency
    recency_weight = models.FloatField(default=1.0)  # 0-2: time-decay weight, recent = higher
    risk_score = models.FloatField(default=1.0)  # 0-2: complexity + past failures

    # Execution tracking
    execution_status = models.CharField(
        max_length=30,
        choices=[
            ("none", "None"),
            ("pending", "Pending"),
            ("generating", "Generating Code"),
            ("pr_created", "PR Created"),
            ("pr_merged", "PR Merged"),
            ("failed", "Failed"),
        ],
        default="none",
    )
    github_pr_url = models.URLField(max_length=500, blank=True, null=True)
    github_branch = models.CharField(max_length=255, blank=True, null=True)
    execution_log = models.JSONField(default=list, blank=True)
    retry_count = models.IntegerField(default=0)
    dependencies = models.JSONField(default=list, blank=True)
    predicted_failure_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Generated Spec"
        verbose_name_plural = "Generated Specs"
        db_table = "generated_specs"

    def __str__(self):
        return f"{self.title} - {self.workspace.name}"


class SpecIssue(WorkspaceBaseModel):
    """Tracks an issue (task) created from a spec to close the feedback loop."""

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="spec_issues")
    spec = models.ForeignKey(GeneratedSpec, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assignee_email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name = "Spec Issue"
        verbose_name_plural = "Spec Issues"
        db_table = "spec_issues"

    def __str__(self):
        return f"{self.title} ({self.status})"


class ProductMemory(WorkspaceBaseModel):
    """Persistent product memory: past specs, features, problems, rejections."""

    class Category(models.TextChoices):
        SHIPPED = "shipped", "Shipped Feature"
        REJECTED = "rejected", "Rejected Feature"
        RECURRING_PROBLEM = "recurring_problem", "Recurring Problem"
        SPEC_REFERENCE = "spec_reference", "Spec Reference"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="product_memories")
    category = models.CharField(max_length=30, choices=Category.choices)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    spec = models.ForeignKey(
        GeneratedSpec,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memories",
    )
    relevance_score = models.FloatField(default=1.0)
    success_weight = models.FloatField(default=1.0)

    class Meta:
        verbose_name = "Product Memory"
        verbose_name_plural = "Product Memories"
        db_table = "product_memories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.category}] {self.title}"


class Outcome(WorkspaceBaseModel):
    """
    Tracks the real-world outcome of a shipped feature.
    Used by the learning loop to improve future prioritization and spec generation.
    """

    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial Success"
        FAILURE = "failure", "Failure"
        INCONCLUSIVE = "inconclusive", "Inconclusive"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="outcomes")
    spec = models.OneToOneField(
        GeneratedSpec,
        on_delete=models.CASCADE,
        related_name="outcome",
        null=True,
        blank=True,
    )
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.INCONCLUSIVE)
    success_score = models.FloatField(default=0.0)  # 0-1: overall success confidence
    metrics_before = models.JSONField(default=dict, blank=True)  # e.g. {"bug_reports": 12, "churn": 0.05}
    metrics_after = models.JSONField(default=dict, blank=True)  # same keys, post-release values
    notes = models.TextField(blank=True, null=True)
    pr_url = models.URLField(max_length=500, blank=True, null=True)
    supermemory_doc_id = models.CharField(max_length=255, blank=True, null=True)
    success = models.BooleanField(default=False)
    failure_type = models.CharField(max_length=50, blank=True, null=True)
    confidence_score = models.FloatField(default=1.0)
    retry_count = models.IntegerField(default=0)
    predicted_failure_matched = models.BooleanField(default=False)
    simulation_success = models.BooleanField(default=False)
    consistency_success = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Outcome"
        verbose_name_plural = "Outcomes"
        db_table = "spec_outcomes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Outcome for {self.spec.title if self.spec else 'unknown'}: {self.result}"
