from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ModelMetrics:
    bleu: float | None
    dataset_name: str
    measured_at: datetime | None


@dataclass(frozen=True)
class ModelListItem:
    id: UUID
    slug: str
    display_name: str
    description: str
    provider: str
    pipeline_summary: str
    tags: tuple[str, ...]
    is_recommended: bool
    metrics: ModelMetrics | None


@dataclass(frozen=True)
class ModelCatalogItem:
    id: UUID
    slug: str
    display_name: str
    description: str
    provider: str
    pipeline_summary: str
    tags: tuple[str, ...]
    worker_queue: str
    language_pairs: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class CoverageCell:
    supported: bool
    bleu: float | None
    quality: str  # high | medium | low | none


@dataclass(frozen=True)
class ModelsCoverageResult:
    languages: tuple[dict[str, str], ...]
    items: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ModelsForPairResult:
    source: str
    target: str
    recommended_model_id: UUID | None
    items: list[ModelListItem]
