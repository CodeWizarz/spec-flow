from django.db import models
from plane.db.models import WorkspaceBaseModel, Workspace

class Signal(WorkspaceBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="signals")
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="signals/", blank=True, null=True)
    source = models.CharField(max_length=50, default="manual")
    processing_status = models.CharField(max_length=20, default="pending")

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

    class Meta:
        verbose_name = "Insight"
        verbose_name_plural = "Insights"
        db_table = "insights"

    def __str__(self):
        return f"{self.theme} ({self.frequency})"

class GeneratedSpec(WorkspaceBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="specs")
    title = models.CharField(max_length=255)
    spec_json = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Generated Spec"
        verbose_name_plural = "Generated Specs"
        db_table = "generated_specs"

    def __str__(self):
        return f"{self.title} - {self.workspace.name}"


