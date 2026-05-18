import uuid

from django.db import models

from translation_models.models import TranslationModel


class VideoStatus(models.TextChoices):
    WAITING = "WAITING", "Waiting"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    ERROR = "ERROR", "Error"


class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=512)
    model = models.ForeignKey(TranslationModel, on_delete=models.PROTECT, related_name="videos")
    source_language_code = models.CharField(max_length=8)
    target_language_code = models.CharField(max_length=8)
    status = models.CharField(
        max_length=16,
        choices=VideoStatus.choices,
        default=VideoStatus.WAITING,
    )
    progress = models.PositiveSmallIntegerField(default=0)
    input_object_key = models.TextField()
    output_object_key = models.TextField(blank=True, null=True)
    artifact_key = models.JSONField(default=dict, blank=True)
    content_type = models.CharField(max_length=128, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    confidence_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "video"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_video_status"),
            models.Index(fields=["-created_at"], name="idx_video_created"),
        ]

    def __str__(self) -> str:
        return f"{self.id} ({self.status})"
