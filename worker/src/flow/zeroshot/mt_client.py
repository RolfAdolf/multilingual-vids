from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings

from flow.zeroshot.mt_assets import _s3_prefix
from flow.zeroshot.mt_savedmodel import ZeroshotMT, load_saved_model
from languages.lang_mapping import zeroshot_mt_tag

logger = logging.getLogger(__name__)

_mt_model: ZeroshotMT | None = None


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


def _local_translator_path() -> Path:
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
    path = (_graduate_project_dir() / export_subdir / f"translator_{epoch}").resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Translator SavedModel not found: {path}")
    return path


def warm_mt_model(model_dir: Path) -> ZeroshotMT:
    """Load MT SavedModel into process memory (used after S3 download)."""
    global _mt_model
    path = model_dir.resolve()
    logger.info("Loading zero-shot MT SavedModel from %s", path)
    _mt_model = load_saved_model(str(path))
    return _mt_model


def get_mt_model() -> ZeroshotMT:
    global _mt_model
    if _mt_model is not None:
        return _mt_model

    if _s3_prefix():
        raise RuntimeError(
            "Zeroshot MT is not loaded. Ensure worker bootstrap ran "
            "(ZEROSHOT_MT_S3_PREFIX is set)."
        )

    return warm_mt_model(_local_translator_path())


def translate(text: str, target_api: str) -> str:
    tag = zeroshot_mt_tag(target_api)
    logger.info("MT target_api=%s tag=<2%s>", target_api, tag)
    return get_mt_model().translate(text, target_lang=tag)


def translate_de_to_uk(text: str) -> str:
    return translate(text, target_api="uk")
