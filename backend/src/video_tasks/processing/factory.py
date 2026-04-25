from core.settings import translator_settings
from video_tasks.processing.seamless import SeamlessM4TTranslator
from video_tasks.processing.translator import VideoTranslator


def get_video_translator() -> VideoTranslator:
    if translator_settings.provider == "seamless_m4t":
        return SeamlessM4TTranslator()
    raise ValueError(f"Unknown translator provider: {translator_settings.provider}")
