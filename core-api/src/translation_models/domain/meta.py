from __future__ import annotations

from typing import Any

from translation_models.models import TranslationModel


def model_meta(model: TranslationModel) -> dict[str, Any]:
    config = model.config or {}
    description = (model.description or "").strip()
    pipeline_summary = (config.get("pipeline_summary") or description).strip()
    tags = config.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    return {
        "description": description,
        "provider": str(config.get("provider") or "").strip(),
        "pipeline_summary": pipeline_summary,
        "tags": tuple(str(t) for t in tags),
    }
