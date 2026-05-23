from __future__ import annotations

import logging

from django.db.models import F, QuerySet

from config.json_log import log_event
from translation_models.models import ModelLanguage

logger = logging.getLogger(__name__)


class ModelLanguageRepository:
    def active_pairs(self, source: str, target: str) -> QuerySet[ModelLanguage]:
        log_event(
            logger,
            logging.DEBUG,
            "translation_models.repository.active_pairs",
            layer="repository",
            source=source,
            target=target,
        )
        return (
            ModelLanguage.objects.filter(
                model__is_active=True,
                source_language_code=source,
                target_language_code=target,
            )
            .select_related("model")
            .order_by(F("bleu").desc(nulls_last=True))
        )

    def active_language_rows(self) -> QuerySet[ModelLanguage]:
        return ModelLanguage.objects.filter(model__is_active=True)
