from __future__ import annotations

from django.db.models import F, QuerySet

from translation_models.models import ModelLanguage


class ModelLanguageRepository:
    def active_pairs(self, source: str, target: str) -> QuerySet[ModelLanguage]:
        return (
            ModelLanguage.objects.filter(
                model__is_active=True,
                source_language_code=source,
                target_language_code=target,
            )
            .select_related("model")
            .order_by(F("bleu").desc(nulls_last=True), F("nist").desc(nulls_last=True))
        )

    def active_language_rows(self) -> QuerySet[ModelLanguage]:
        return ModelLanguage.objects.filter(model__is_active=True)
