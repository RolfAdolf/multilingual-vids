from __future__ import annotations

import logging
import shutil
from pathlib import Path

from django.conf import settings

from config.json_log import log_event
from config.worker_enabled import is_worker_enabled, worker_disabled_message
from flow.zeroshot import mt_client
from flow.zeroshot.device_init import log_zeroshot_mt_device_init
from flow.zeroshot.mt_assets import _s3_prefix, download_translator_to_temp

logger = logging.getLogger(__name__)


def bootstrap_zeroshot_worker() -> None:
    """
    Zeroshot worker startup: download MT from S3, load into memory, remove temp files.
    """
    if not is_worker_enabled():
        log_event(
            logger,
            logging.INFO,
            "worker.zeroshot.bootstrap.skipped",
            layer="worker",
            reason=worker_disabled_message(),
        )
        return

    if not _s3_prefix():
        raise ValueError(
            "ZEROSHOT_MT_S3_PREFIX is required; zeroshot MT is loaded from S3 only."
        )

    tmp_dir: Path | None = None
    try:
        tmp_dir = download_translator_to_temp()
        mt_client.warm_mt_model(tmp_dir)
        log_zeroshot_mt_device_init()
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
