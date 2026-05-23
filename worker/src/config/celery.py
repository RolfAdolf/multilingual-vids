import logging
import os
import sys
from pathlib import Path

src = Path(__file__).resolve().parent.parent
root = src.parent.parent
core_src = Path(os.environ.get("CORE_SRC_PATH", root / "core-api" / "src")).resolve()

for path in (core_src, src):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from celery import Celery

from config.json_log import log_event

logger = logging.getLogger(__name__)

app = Celery("worker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["tasks"])

# Ensure video.translate is registered (autodiscover loads tasks.tasks → tasks.video).
import tasks.video  # noqa: E402, F401

from config.worker_enabled import is_worker_enabled, worker_disabled_message

if os.environ.get("CELERY_QUEUE") == "zeroshot" and is_worker_enabled():
    from celery.signals import worker_process_init

    @worker_process_init.connect
    def _bootstrap_zeroshot_worker(**_kwargs):
        from flow.zeroshot.bootstrap import bootstrap_zeroshot_worker

        bootstrap_zeroshot_worker()

if not is_worker_enabled():
    log_event(
        logger,
        logging.WARNING,
        "worker.celery.disabled",
        layer="worker",
        queue=os.environ.get("CELERY_QUEUE"),
        message=worker_disabled_message(),
    )

_task_names = sorted(
    name for name in app.tasks if not name.startswith("celery.")
)
log_event(
    logger,
    logging.INFO,
    "worker.celery.ready",
    layer="worker",
    registered_tasks=_task_names,
    broker_host=app.conf.broker_url.split("@")[-1] if app.conf.broker_url else None,
)
