import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("translation_models", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Video",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_filename", models.CharField(max_length=512)),
                ("source_language_code", models.CharField(max_length=8)),
                ("target_language_code", models.CharField(max_length=8)),
                ("status", models.CharField(choices=[("WAITING", "Waiting"), ("PROCESSING", "Processing"), ("SUCCESS", "Success"), ("ERROR", "Error")], default="WAITING", max_length=16)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("input_object_key", models.TextField()),
                ("output_object_key", models.TextField(blank=True, null=True)),
                ("artifact_key", models.JSONField(blank=True, default=dict)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("file_size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("idempotency_key", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("celery_task_id", models.CharField(blank=True, max_length=255, null=True)),
                ("confidence_score", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("model", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="videos", to="translation_models.translationmodel")),
            ],
            options={"db_table": "video", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="video",
            index=models.Index(fields=["status"], name="idx_video_status"),
        ),
        migrations.AddIndex(
            model_name="video",
            index=models.Index(fields=["-created_at"], name="idx_video_created"),
        ),
    ]
