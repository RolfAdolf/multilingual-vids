from __future__ import annotations

import logging

from django.conf import settings

from common.compute_device import log_compute_init, tensorflow_gpu_summary, torch_cuda_summary

logger = logging.getLogger(__name__)


def log_zeroshot_whisper_device_init(*, layer: str = "worker") -> None:
    requested = getattr(settings, "ZEROSHOT_WHISPER_DEVICE", "cpu") or "cpu"
    compute_type = getattr(settings, "ZEROSHOT_WHISPER_COMPUTE_TYPE", "int8")
    model_size = getattr(settings, "ZEROSHOT_WHISPER_MODEL", "large-v3")
    resolved = requested.lower()
    log_compute_init(
        logger,
        "worker.zeroshot.whisper.device.init",
        component="whisper",
        requested=requested,
        resolved=resolved,
        using_gpu=resolved == "cuda",
        layer=layer,
        model_size=model_size,
        compute_type=compute_type,
        **torch_cuda_summary(),
    )


def log_zeroshot_mt_device_init(*, layer: str = "worker") -> None:
    tf_info = tensorflow_gpu_summary()
    log_compute_init(
        logger,
        "worker.zeroshot.mt.device.init",
        component="zeroshot_mt",
        requested="tensorflow",
        resolved=tf_info["resolved"],
        using_gpu=tf_info["using_gpu"],
        layer=layer,
        **tf_info,
    )
