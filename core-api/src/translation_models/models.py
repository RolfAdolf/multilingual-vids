import uuid

from django.db import models


class ModelSlug(models.TextChoices):
    SEAMLESS_M4T = "seamless_m4t", "SeamlessM4T"
    ZEROSWOT = "zeroswot", "ZeroSwot"
    ZEROSHOT = "zeroshot", "Zeroshot pipeline"


class TranslationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=32, choices=ModelSlug.choices, unique=True)
    display_name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    worker_queue = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "model"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class ModelLanguage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        TranslationModel,
        on_delete=models.CASCADE,
        related_name="languages",
    )
    source_language_code = models.CharField(max_length=8)
    target_language_code = models.CharField(max_length=8)
    source_model_lang_code = models.CharField(max_length=32)
    target_model_lang_code = models.CharField(max_length=32)
    source_name_en = models.CharField(max_length=128, blank=True)
    source_name_ru = models.CharField(max_length=128, blank=True)
    target_name_en = models.CharField(max_length=128, blank=True)
    target_name_ru = models.CharField(max_length=128, blank=True)
    bleu = models.FloatField(null=True, blank=True)
    nist = models.FloatField(null=True, blank=True)
    dataset_name = models.CharField(max_length=128, default="default", blank=True)
    measured_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "model_language"
        constraints = [
            models.UniqueConstraint(
                fields=["model", "source_language_code", "target_language_code"],
                name="uniq_model_language_pair",
            ),
        ]
        indexes = [
            models.Index(
                fields=["source_language_code", "target_language_code"],
                name="idx_model_language_pair",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.model.slug}: {self.source_language_code}->{self.target_language_code}"
