from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from django.conf import settings

from languages.lang_mapping import zeroshot_tts_voice

logger = logging.getLogger(__name__)


def _default_voice() -> str:
    return getattr(settings, "ZEROSHOT_TTS_VOICE", "") or os.environ.get(
        "ZEROSHOT_TTS_VOICE", "uk-UA-OstapNeural"
    )


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize(text: str, target_api: str, output_path: Path) -> None:
    try:
        voice = zeroshot_tts_voice(target_api)
    except KeyError:
        voice = _default_voice()
    logger.info("TTS target_api=%s voice=%s chars=%d", target_api, voice, len(text))
    asyncio.run(_synthesize_async(text, output_path, voice))


def synthesize_ukrainian(text: str, output_path: Path) -> None:
    synthesize(text, target_api="uk", output_path=output_path)
