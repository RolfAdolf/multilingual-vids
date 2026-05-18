from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings

from flow.zeroshot.mt_savedmodel import load_saved_model

logger = logging.getLogger(__name__)


def _graduate_project_dir() -> Path:
    raw = getattr(settings, "ZEROSHOT_GRADUATE_PROJECT_DIR", "") or os.environ.get(
        "ZEROSHOT_GRADUATE_PROJECT_DIR", ""
    )
    if raw:
        return Path(raw).resolve()
    here = Path(__file__).resolve()
    for base in here.parents:
        for rel in (
            "diploma/bachelor/graduate-project",
            "bachelor/graduate-project",
        ):
            candidate = base / rel
            if (candidate / "trained_models").is_dir():
                return candidate
    raise FileNotFoundError(
        "Set ZEROSHOT_GRADUATE_PROJECT_DIR to bachelor/graduate-project"
    )


def _translator_path(project_dir: Path) -> Path:
    explicit = getattr(settings, "ZEROSHOT_MT_TRANSLATOR_PATH", "") or os.environ.get(
        "ZEROSHOT_MT_TRANSLATOR_PATH", ""
    )
    if explicit:
        path = Path(explicit).resolve()
        if path.is_dir():
            return path
        raise FileNotFoundError(f"ZEROSHOT_MT_TRANSLATOR_PATH not found: {path}")

    export_subdir = getattr(settings, "ZEROSHOT_MT_EXPORT_DIR", "") or os.environ.get(
        "ZEROSHOT_MT_EXPORT_DIR", "trained_models/augmented"
    )
    epoch = str(
        getattr(settings, "ZEROSHOT_MT_EPOCH", "")
        or os.environ.get("ZEROSHOT_MT_EPOCH", "8")
    )
    path = (project_dir / export_subdir / f"translator_{epoch}").resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Translator SavedModel not found: {path}")
    return path


def get_mt_model():
    project_dir = _graduate_project_dir()
    translator_path = _translator_path(project_dir)
    logger.info("Loading zero-shot MT SavedModel from %s", translator_path)
    return load_saved_model(str(translator_path))


def translate_de_to_uk(text: str) -> str:
    return get_mt_model().translate(text, target_lang="uk")
