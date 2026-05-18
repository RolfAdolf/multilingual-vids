from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    model_size = getattr(settings, "ZEROSHOT_WHISPER_MODEL", "large-v3")
    device = getattr(settings, "ZEROSHOT_WHISPER_DEVICE", "cpu")
    compute_type = getattr(settings, "ZEROSHOT_WHISPER_COMPUTE_TYPE", "int8")
    logger.info("Loading Whisper %s on %s", model_size, device)
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_german(wav_path: Path) -> str:
    model = _whisper_model()
    segments, _info = model.transcribe(
        str(wav_path),
        language="de",
        beam_size=5,
        vad_filter=True,
    )
    parts = [segment.text.strip() for segment in segments if segment.text.strip()]
    return " ".join(parts)
