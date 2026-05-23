from __future__ import annotations

import os

from django.conf import settings


def is_worker_enabled() -> bool:
    return bool(getattr(settings, "WORKER_ENABLED", True))


def worker_disabled_message() -> str:
    queue = os.environ.get("CELERY_QUEUE", "unknown")
    return (
        f"Translation worker for queue '{queue}' is disabled "
        "(set WORKER_ENABLED=true in this worker's .env to enable)."
    )
