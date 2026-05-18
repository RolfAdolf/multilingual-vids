from __future__ import annotations

from translation_models.domain.repository import ModelLanguageRepository
from translation_models.domain.types import ModelListItem, ModelMetrics, ModelsForPairResult


class TranslationModelQueryService:
    def __init__(self, repository: ModelLanguageRepository | None = None):
        self._repository = repository or ModelLanguageRepository()

    def list_for_language_pair(self, source: str, target: str) -> ModelsForPairResult:
        source = source.lower()
        target = target.lower()
        rows = self._repository.active_pairs(source, target)

        recommended_id = None
        items: list[ModelListItem] = []
        for row in rows:
            if recommended_id is None:
                recommended_id = row.model_id
            metrics = None
            if row.bleu is not None or row.nist is not None:
                metrics = ModelMetrics(
                    bleu=row.bleu,
                    nist=row.nist,
                    dataset_name=row.dataset_name,
                    measured_at=row.measured_at,
                )
            items.append(
                ModelListItem(
                    id=row.model_id,
                    slug=row.model.slug,
                    display_name=row.model.display_name,
                    is_recommended=row.model_id == recommended_id,
                    metrics=metrics,
                )
            )

        return ModelsForPairResult(
            source=source,
            target=target,
            recommended_model_id=recommended_id,
            items=items,
        )
