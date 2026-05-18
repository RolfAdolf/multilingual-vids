from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ModelMetrics:
    bleu: float | None
    nist: float | None
    dataset_name: str
    measured_at: datetime | None


@dataclass(frozen=True)
class ModelListItem:
    id: UUID
    slug: str
    display_name: str
    is_recommended: bool
    metrics: ModelMetrics | None


@dataclass(frozen=True)
class ModelsForPairResult:
    source: str
    target: str
    recommended_model_id: UUID | None
    items: list[ModelListItem]
