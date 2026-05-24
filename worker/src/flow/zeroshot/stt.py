from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from common.compute_device import log_compute_init, torch_cuda_summary
from flow.zeroshot.device_init import log_zeroshot_whisper_device_init
from languages.lang_mapping import zeroshot_whisper_code

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    model_size = getattr(settings, "ZEROSHOT_WHISPER_MODEL", "large-v3")
    device = getattr(settings, "ZEROSHOT_WHISPER_DEVICE", "cpu") or "cpu"
    compute_type = getattr(settings, "ZEROSHOT_WHISPER_COMPUTE_TYPE", "int8")
    resolved = device.lower()
    log_compute_init(
        logger,
        "worker.zeroshot.whisper.model.init",
        component="whisper",
        requested=device,
        resolved=resolved,
        using_gpu=resolved == "cuda",
        layer="pipeline",
        model_size=model_size,
        compute_type=compute_type,
        **torch_cuda_summary(),
    )
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(wav_path: Path, source_api: str) -> str:
    language = zeroshot_whisper_code(source_api)
    model = _whisper_model()
    segments, _info = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )
    parts = [segment.text.strip() for segment in segments if segment.text.strip()]
    return " ".join(parts)


def transcribe_german(wav_path: Path) -> str:
    return transcribe(wav_path, source_api="de")
