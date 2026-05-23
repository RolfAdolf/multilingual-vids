from django.db import models


class Language(models.Model):
    """Canonical language catalog (ISO 639-3 + script from SeamlessM4T)."""

    code = models.CharField(max_length=16, primary_key=True)
    api_code = models.CharField(max_length=16, db_index=True)
    name_en = models.CharField(max_length=128)
    name_ru = models.CharField(max_length=128, blank=True)
    script = models.CharField(max_length=16, blank=True)

    supports_source_speech = models.BooleanField(default=False)
    supports_source_text = models.BooleanField(default=False)
    supports_target_speech = models.BooleanField(default=False)
    supports_target_text = models.BooleanField(default=False)

    class Meta:
        db_table = "language"
        ordering = ["name_en"]

    def __str__(self) -> str:
        return f"{self.api_code} ({self.code})"

    @property
    def can_be_source(self) -> bool:
        return self.supports_source_speech or self.supports_source_text

    @property
    def can_be_target(self) -> bool:
        return self.supports_target_speech or self.supports_target_text
