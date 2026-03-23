from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0003_prioritization_supermemory"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("db", "0120_issueview_archived_at"),
    ]

    operations = [
        # Advanced prioritization fields
        migrations.AddField(
            model_name="generatedspec",
            name="confidence_score",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="recency_weight",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="risk_score",
            field=models.FloatField(default=1.0),
        ),
        # Execution tracking fields
        migrations.AddField(
            model_name="generatedspec",
            name="execution_status",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("pending", "Pending"),
                    ("generating", "Generating Code"),
                    ("pr_created", "PR Created"),
                    ("pr_merged", "PR Merged"),
                    ("failed", "Failed"),
                ],
                default="none",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="github_pr_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="github_branch",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="execution_log",
            field=models.JSONField(blank=True, default=list),
        ),
        # Outcome model
        migrations.CreateModel(
            name="Outcome",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ("result", models.CharField(
                    choices=[("success", "Success"), ("partial", "Partial Success"), ("failure", "Failure"), ("inconclusive", "Inconclusive")],
                    default="inconclusive",
                    max_length=20,
                )),
                ("success_score", models.FloatField(default=0.0)),
                ("metrics_before", models.JSONField(blank=True, default=dict)),
                ("metrics_after", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True, null=True)),
                ("pr_url", models.URLField(blank=True, max_length=500, null=True)),
                ("supermemory_doc_id", models.CharField(blank=True, max_length=255, null=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created_by", to=settings.AUTH_USER_MODEL, verbose_name="Created By")),
                ("updated_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated_by", to=settings.AUTH_USER_MODEL, verbose_name="Last Modified By")),
                ("project", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="project_%(class)s", to="db.project")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outcomes", to="db.workspace")),
                ("spec", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="outcome", to="signals.generatedspec")),
            ],
            options={"verbose_name": "Outcome", "verbose_name_plural": "Outcomes", "db_table": "spec_outcomes", "ordering": ["-created_at"]},
        ),
    ]
