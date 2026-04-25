import logging
from pathlib import Path

import torch

from core.settings import translator_settings
from video_tasks.processing.translator import VideoTranslator


logger = logging.getLogger(__name__)


class SeamlessM4TTranslator(VideoTranslator):
    def __init__(self, model_name: str | None = None, device: str | None = None):
        self._model_name = model_name or translator_settings.seamless_model
        self._device_name = device or translator_settings.device
        self._processor = None
        self._model = None
        self._device = None

    def translate_audio(
        self,
        *,
        input_audio_path: str,
        output_audio_path: str,
        source_lang: str,
        target_lang: str,
    ) -> None:
        logger.info(
            "Starting SeamlessM4T audio translation input_audio_path=%s output_audio_path=%s source_lang=%s target_lang=%s",
            input_audio_path,
            output_audio_path,
            source_lang,
            target_lang,
        )
        self._load_model()

        import librosa
        import soundfile as sf

        logger.info("Loading input audio for SeamlessM4T input_audio_path=%s", input_audio_path)
        waveform, sample_rate = librosa.load(input_audio_path, sr=16_000, mono=True)
        logger.info(
            "Input audio loaded for SeamlessM4T sample_rate=%s samples=%s",
            sample_rate,
            len(waveform),
        )
        inputs = self._processor(
            audios=waveform,
            sampling_rate=sample_rate,
            src_lang=source_lang,
            return_tensors="pt",
        )
        inputs = {key: value.to(self._device) for key, value in inputs.items()}

        logger.info("Generating translated speech with SeamlessM4T target_lang=%s", target_lang)
        with torch.no_grad():
            generated = self._model.generate(
                **inputs,
                tgt_lang=target_lang,
                generate_speech=True,
            )

        audio = self._extract_audio(generated)
        Path(output_audio_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_audio_path, audio, self._model.config.sampling_rate)
        logger.info(
            "SeamlessM4T translated speech saved output_audio_path=%s sampling_rate=%s",
            output_audio_path,
            self._model.config.sampling_rate,
        )

    def _load_model(self) -> None:
        if self._model is not None and self._processor is not None:
            logger.info("SeamlessM4T model already loaded model=%s device=%s", self._model_name, self._device)
            return

        from transformers import AutoProcessor, SeamlessM4TModel

        self._device = self._resolve_device(self._device_name)
        logger.info("Loading SeamlessM4T model %s on %s", self._model_name, self._device)
        self._processor = AutoProcessor.from_pretrained(self._model_name)
        self._model = SeamlessM4TModel.from_pretrained(self._model_name).to(self._device)
        self._model.eval()
        logger.info("SeamlessM4T model loaded model=%s device=%s", self._model_name, self._device)

    @staticmethod
    def _resolve_device(device_name: str) -> torch.device:
        if device_name != "auto":
            return torch.device(device_name)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    @staticmethod
    def _extract_audio(generated) -> object:
        if hasattr(generated, "waveform"):
            audio = generated.waveform
        elif isinstance(generated, tuple):
            audio = generated[0]
        else:
            audio = generated

        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        if getattr(audio, "ndim", 1) > 1:
            audio = audio.squeeze()
        return audio
