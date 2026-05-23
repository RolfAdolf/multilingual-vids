from __future__ import annotations

import logging
from pathlib import Path

from flow.zeroshot.mt_savedmodel import ZeroshotMT, load_saved_model
from languages.lang_mapping import zeroshot_mt_tag

logger = logging.getLogger(__name__)

_mt_model: ZeroshotMT | None = None


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
    raise RuntimeError(
        "Zeroshot MT is not loaded. Ensure worker bootstrap ran with "
        "ZEROSHOT_MT_S3_PREFIX set and WORKER_ENABLED=true."
    )


def translate(text: str, target_api: str) -> str:
    tag = zeroshot_mt_tag(target_api)
    logger.info("MT target_api=%s tag=<2%s>", target_api, tag)
    return get_mt_model().translate(text, target_lang=tag)


def translate_de_to_uk(text: str) -> str:
    return translate(text, target_api="uk")
