from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from languages.lang_mapping import normalize_zeroswot_api_code

logger = logging.getLogger(__name__)

# edge-tts neural voices for ZeroSwot target languages (en source only in HF model).
ZEROSWOT_TTS_VOICES: dict[str, str] = {
    "ar": "ar-SA-ZariyahNeural",
    "ca": "ca-ES-JoanaNeural",
    "cy": "cy-GB-NiaNeural",
    "de": "de-DE-KatjaNeural",
    "en": "en-US-JennyNeural",
    "et": "et-EE-AnuNeural",
    "fa": "fa-IR-DilaraNeural",
    "id": "id-ID-GadisNeural",
    "ja": "ja-JP-NanamiNeural",
    "lv": "lv-LV-EveritaNeural",
    "mn": "mn-MN-YesuiNeural",
    "sl": "sl-SI-PetraNeural",
    "sv-se": "sv-SE-SofieNeural",
    "ta": "ta-IN-PallaviNeural",
    "tr": "tr-TR-EmelNeural",
    "zh-cn": "zh-CN-XiaoxiaoNeural",
}


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def zeroswot_tts_voice(target_api: str) -> str:
    code = normalize_zeroswot_api_code(target_api)
    voice = ZEROSWOT_TTS_VOICES.get(code)
    if not voice:
        raise KeyError(target_api)
    return voice


def synthesize(text: str, target_api: str, output_path: Path) -> None:
    voice = zeroswot_tts_voice(target_api)
    logger.info("zeroswot TTS target_api=%s voice=%s chars=%d", target_api, voice, len(text))
    asyncio.run(_synthesize_async(text, output_path, voice))
