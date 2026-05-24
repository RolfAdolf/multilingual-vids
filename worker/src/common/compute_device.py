from __future__ import annotations

import logging
from typing import Any

from config.json_log import log_event

logger = logging.getLogger(__name__)


def torch_cuda_summary() -> dict[str, Any]:
    import torch

    summary: dict[str, Any] = {
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
    }
    if torch.cuda.is_available():
        summary["cuda_device_name"] = torch.cuda.get_device_name(0)
    mps = getattr(torch.backends, "mps", None)
    summary["mps_available"] = bool(mps and torch.backends.mps.is_available())
    return summary


def resolve_torch_device(requested: str) -> tuple[Any, dict[str, Any]]:
    """Map SEAMLESS_DEVICE / auto to torch.device and a log-friendly summary."""
    import torch

    choice = (requested or "auto").lower()
    info = torch_cuda_summary()
    info["requested"] = choice

    if choice == "auto":
        if info["cuda_available"]:
            device = torch.device("cuda")
            info["resolved"] = "cuda"
        elif info.get("mps_available"):
            device = torch.device("mps")
            info["resolved"] = "mps"
        else:
            device = torch.device("cpu")
            info["resolved"] = "cpu"
    else:
        device = torch.device(choice)
        info["resolved"] = choice

    info["using_gpu"] = info["resolved"] in ("cuda", "mps")
    return device, info


def tensorflow_gpu_summary() -> dict[str, Any]:
    try:
        import tensorflow as tf

        gpus = tf.config.list_physical_devices("GPU")
        count = len(gpus)
        return {
            "tensorflow_gpu_count": count,
            "resolved": "cuda" if count else "cpu",
            "using_gpu": count > 0,
        }
    except Exception as exc:
        return {
            "tensorflow_gpu_count": 0,
            "resolved": "cpu",
            "using_gpu": False,
            "probe_error": str(exc),
        }


def log_compute_init(
    log: logging.Logger,
    event: str,
    *,
    component: str,
    requested: str | None = None,
    resolved: str,
    using_gpu: bool,
    layer: str = "worker",
    **extra: Any,
) -> None:
    log_event(
        log,
        logging.INFO,
        event,
        layer=layer,
        component=component,
        requested=requested,
        resolved=resolved,
        using_gpu=using_gpu,
        compute=resolved,
        **extra,
    )
