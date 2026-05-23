from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.conf import settings

from storage.s3 import download_prefix

logger = logging.getLogger(__name__)


def _bucket() -> str:
    return getattr(settings, "ZEROSHOT_MT_S3_BUCKET", "") or settings.YANDEX_S3_BUCKET_UPLOADS


def _s3_prefix() -> str:
    return (getattr(settings, "ZEROSHOT_MT_S3_PREFIX", "") or "").strip().strip("/")


def _assert_saved_model_layout(model_dir: Path) -> Path:
    model_dir = model_dir.resolve()
    if not (model_dir / "saved_model.pb").is_file():
        raise FileNotFoundError(f"saved_model.pb missing under {model_dir}")

    variables_dir = model_dir / "variables"
    if not (variables_dir / "variables.index").is_file():
        raise FileNotFoundError(f"variables.index missing under {model_dir}")

    data_files = list(variables_dir.glob("variables.data-*"))
    if not data_files:
        raise FileNotFoundError(f"variables.data-* missing under {variables_dir}")

    return model_dir


def download_translator_to_temp() -> Path:
    """Download SavedModel tree from S3 into a new temporary directory."""
    prefix = _s3_prefix()
    if not prefix:
        raise ValueError("ZEROSHOT_MT_S3_PREFIX is not set")

    tmp_dir = Path(tempfile.mkdtemp(prefix="zeroshot-mt-"))
    logger.info(
        "Downloading zeroshot MT from s3://%s/%s/ to %s",
        _bucket(),
        prefix,
        tmp_dir,
    )
    download_prefix(prefix, tmp_dir, bucket=_bucket())
    return _assert_saved_model_layout(tmp_dir)
