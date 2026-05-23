from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    layer: str,
    task_id: str | None = None,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "timestamp": iso_timestamp(),
        "level": logging.getLevelName(level),
        "event": event,
        "layer": layer,
    }
    if task_id:
        payload["task_id"] = task_id
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def log_exception(
    logger: logging.Logger,
    event: str,
    *,
    layer: str,
    exc: BaseException,
    task_id: str | None = None,
    level: int = logging.ERROR,
    **fields: Any,
) -> None:
    log_event(
        logger,
        level,
        event,
        layer=layer,
        task_id=task_id,
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc(),
        **fields,
    )
