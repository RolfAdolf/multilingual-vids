from __future__ import annotations

import logging

from config.json_log import log_event
from config.worker_enabled import is_worker_enabled, worker_disabled_message
from flow.zeroswot.inference import log_zeroswot_device_init, warm_zeroswot_model

logger = logging.getLogger(__name__)


def bootstrap_zeroswot_worker() -> None:
    if not is_worker_enabled():
        log_event(
            logger,
            logging.INFO,
            "worker.zeroswot.bootstrap.skipped",
            layer="worker",
            reason=worker_disabled_message(),
        )
        return

    log_zeroswot_device_init()
    warm_zeroswot_model()
    log_event(logger, logging.INFO, "worker.zeroswot.bootstrap.ready", layer="worker")
