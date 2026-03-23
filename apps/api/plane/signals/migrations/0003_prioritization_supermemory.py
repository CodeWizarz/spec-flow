from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0002_specflow_v2"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedspec",
            name="impact_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="effort_score",
            field=models.FloatField(default=5.0),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="priority_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="generatedspec",
            name="supermemory_doc_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="signal",
            name="source_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="signal",
            name="supermemory_doc_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="insight",
            name="supermemory_doc_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
