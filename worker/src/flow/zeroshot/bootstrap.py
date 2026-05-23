from __future__ import annotations

import logging
import shutil
from pathlib import Path

from django.conf import settings

from config.json_log import log_event
from flow.zeroshot import mt_client
from flow.zeroshot.mt_assets import _s3_prefix, download_translator_to_temp

logger = logging.getLogger(__name__)


def bootstrap_zeroshot_worker() -> None:
    """
    Zeroshot worker startup: download MT from S3, load into memory, remove temp files.
    """
    if not _s3_prefix():
        log_event(
            logger,
            logging.INFO,
            "worker.zeroshot.bootstrap.skipped",
            layer="worker",
            reason="ZEROSHOT_MT_S3_PREFIX unset",
        )
        return

    tmp_dir: Path | None = None
    try:
        tmp_dir = download_translator_to_temp()
        mt_client.warm_mt_model(tmp_dir)
        log_event(
            logger,
            logging.INFO,
            "worker.zeroshot.bootstrap.ready",
            layer="worker",
            s3_prefix=_s3_prefix(),
            bucket=getattr(settings, "ZEROSHOT_MT_S3_BUCKET", "")
            or settings.YANDEX_S3_BUCKET_UPLOADS,
        )
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log_event(
                logger,
                logging.DEBUG,
                "worker.zeroshot.bootstrap.temp_removed",
                layer="worker",
                path=str(tmp_dir),
            )
