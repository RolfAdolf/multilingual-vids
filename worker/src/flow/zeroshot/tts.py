from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _voice() -> str:
    return getattr(settings, "ZEROSHOT_TTS_VOICE", "") or os.environ.get(
        "ZEROSHOT_TTS_VOICE", "uk-UA-OstapNeural"
    )


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize_ukrainian(text: str, output_path: Path) -> None:
    voice = _voice()
    logger.info("TTS edge-tts voice=%s chars=%d", voice, len(text))
    asyncio.run(_synthesize_async(text, output_path, voice))
