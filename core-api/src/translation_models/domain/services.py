from __future__ import annotations

import logging

from config.json_log import log_event
from translation_models.domain.meta import model_meta
from translation_models.domain.repository import ModelLanguageRepository
from translation_models.domain.types import (
    CoverageCell,
    ModelCatalogItem,
    ModelListItem,
    ModelMetrics,
    ModelsCoverageResult,
    ModelsForPairResult,
)
from translation_models.models import TranslationModel

logger = logging.getLogger(__name__)


def _quality_level(bleu: float | None) -> str:
    if bleu is None:
        return "none"
    if bleu >= 40:
        return "high"
    if bleu >= 20:
        return "medium"
    return "low"


class TranslationModelQueryService:
    def __init__(self, repository: ModelLanguageRepository | None = None):
        self._repository = repository or ModelLanguageRepository()

    def list_for_language_pair(self, source: str, target: str) -> ModelsForPairResult:
        source = source.lower()
        target = target.lower()
        log_event(
            logger,
            logging.INFO,
            "translation_models.service.list_for_language_pair",
            layer="service",
            source=source,
            target=target,
        )
        rows = self._repository.active_pairs(source, target)

        rows = list(rows)
        recommended_id = rows[0].model_id if rows else None
        items: list[ModelListItem] = []
        for row in rows:
            metrics = None
            if row.bleu is not None:
                metrics = ModelMetrics(
                    bleu=row.bleu,
                    dataset_name=row.dataset_name,
                    measured_at=row.measured_at,
                )
            meta = model_meta(row.model)
            items.append(
                ModelListItem(
                    id=row.model_id,
                    slug=row.model.slug,
                    display_name=row.model.display_name,
                    description=meta["description"],
                    provider=meta["provider"],
                    pipeline_summary=meta["pipeline_summary"],
                    tags=meta["tags"],
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

    def list_catalog(self) -> list[ModelCatalogItem]:
        models = TranslationModel.objects.filter(is_active=True).order_by("display_name")
        rows = self._repository.active_language_rows().select_related("model")
        pairs_by_model: dict = {}
        for row in rows:
            pairs_by_model.setdefault(row.model_id, []).append(
                {
                    "source": row.source_language_code,
                    "target": row.target_language_code,
                    "source_name_en": row.source_name_en,
                    "target_name_en": row.target_name_en,
                    "bleu": row.bleu,
                }
            )

        catalog: list[ModelCatalogItem] = []
        for model in models:
            meta = model_meta(model)
            catalog.append(
                ModelCatalogItem(
                    id=model.id,
                    slug=model.slug,
                    display_name=model.display_name,
                    description=meta["description"],
                    provider=meta["provider"],
                    pipeline_summary=meta["pipeline_summary"],
                    tags=meta["tags"],
                    worker_queue=model.worker_queue,
                    language_pairs=tuple(pairs_by_model.get(model.id, ())),
                )
            )
        return catalog

    def coverage_matrix(self) -> ModelsCoverageResult:
        rows = list(
            self._repository.active_language_rows().select_related("model").order_by(
                "model__display_name"
            )
        )
        target_codes: set[str] = set()
        for row in rows:
            target_codes.add(row.target_language_code)

        languages = []
        seen: set[str] = set()
        for row in rows:
            code = row.target_language_code
            if code in seen:
                continue
            seen.add(code)
            languages.append(
                {
                    "code": code,
                    "name_en": row.target_name_en or code.upper(),
                    "name_ru": row.target_name_ru or "",
                }
            )
        languages.sort(key=lambda x: x["code"])

        models_seen: dict = {}
        for row in rows:
            models_seen.setdefault(
                row.model_id,
                {"id": row.model_id, "slug": row.model.slug, "display_name": row.model.display_name},
            )

        items = []
        for model_info in models_seen.values():
            cells: dict[str, CoverageCell] = {}
            for lang in languages:
                code = lang["code"]
                match = next(
                    (
                        r
                        for r in rows
                        if r.model_id == model_info["id"] and r.target_language_code == code
                    ),
                    None,
                )
                if not match:
                    cells[code] = CoverageCell(
                        supported=False, bleu=None, quality="none"
                    )
                else:
                    cells[code] = CoverageCell(
                        supported=True,
                        bleu=match.bleu,
                        quality=_quality_level(match.bleu),
                    )
            items.append({**model_info, "coverage": {k: v for k, v in cells.items()}})

        return ModelsCoverageResult(languages=tuple(languages), items=tuple(items))
