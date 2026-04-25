from abc import ABC, abstractmethod


class VideoTranslator(ABC):
    @abstractmethod
    def translate_audio(
        self,
        *,
        input_audio_path: str,
        output_audio_path: str,
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Translate speech from an audio file and save synthesized speech."""
