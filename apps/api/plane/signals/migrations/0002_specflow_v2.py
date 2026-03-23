from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("db", "0120_issueview_archived_at"),
    ]

    operations = [
        # Add status + agent_payload to GeneratedSpec
        migrations.AddField(
            model_name="generatedspec",
            name="status",
            field=models.CharField(
                choices=[
                    ("proposed", "Proposed"),
                    ("in_progress", "In Progress"),
                    ("completed", "Completed"),
                    ("rejected", "Rejected"),
                ],
                default="proposed",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="agent_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
        # SpecIssue model
        migrations.CreateModel(
            name="SpecIssue",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("todo", "To Do"),
                        ("in_progress", "In Progress"),
                        ("done", "Done"),
                        ("cancelled", "Cancelled"),
                    ],
                    default="todo",
                    max_length=20,
                )),
                ("assignee_email", models.EmailField(blank=True, null=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created_by", to=settings.AUTH_USER_MODEL, verbose_name="Created By")),
                ("updated_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated_by", to=settings.AUTH_USER_MODEL, verbose_name="Last Modified By")),
                ("project", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="project_%(class)s", to="db.project")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="spec_issues", to="db.workspace")),
                ("spec", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="signals.generatedspec")),
            ],
            options={
                "verbose_name": "Spec Issue",
                "verbose_name_plural": "Spec Issues",
                "db_table": "spec_issues",
            },
        ),
        # ProductMemory model
        migrations.CreateModel(
            name="ProductMemory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ("category", models.CharField(
                    choices=[
                        ("shipped", "Shipped Feature"),
                        ("rejected", "Rejected Feature"),
                        ("recurring_problem", "Recurring Problem"),
                        ("spec_reference", "Spec Reference"),
                    ],
                    max_length=30,
                )),
                ("title", models.CharField(max_length=255)),
                ("summary", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created_by", to=settings.AUTH_USER_MODEL, verbose_name="Created By")),
                ("updated_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated_by", to=settings.AUTH_USER_MODEL, verbose_name="Last Modified By")),
                ("project", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="project_%(class)s", to="db.project")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_memories", to="db.workspace")),
                ("spec", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="memories", to="signals.generatedspec")),
            ],
            options={
                "verbose_name": "Product Memory",
                "verbose_name_plural": "Product Memories",
                "db_table": "product_memories",
                "ordering": ["-created_at"],
            },
        ),
    ]
