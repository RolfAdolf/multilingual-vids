from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from django.conf import settings

logger = logging.getLogger(__name__)

SAMPLE_RATE_HZ = 16_000


def _resolve_device() -> torch.device:
    choice = (getattr(settings, "SEAMLESS_DEVICE", "auto") or "auto").lower()
    if choice == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(choice)


def _load_audio_mono_16k(wav_path: Path) -> np.ndarray:
    audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if isinstance(audio, np.ndarray) and audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE_HZ:
        import torchaudio

        tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
        tensor = torchaudio.functional.resample(tensor, sr, SAMPLE_RATE_HZ)
        audio = tensor.squeeze(0).numpy()
    return np.asarray(audio, dtype=np.float32)


def _waveform_from_generate(output) -> np.ndarray:
    if hasattr(output, "sequences"):
        tensor = output.sequences
    else:
        tensor = output
    if isinstance(tensor, (list, tuple)):
        tensor = tensor[0]
    if hasattr(tensor, "cpu"):
        tensor = tensor.cpu()
    array = tensor.numpy() if hasattr(tensor, "numpy") else np.asarray(tensor)
    return np.squeeze(array).astype(np.float32)


@lru_cache(maxsize=1)
def _model_bundle():
    from transformers import AutoProcessor, SeamlessM4TModel

    model_id = getattr(
        settings,
        "SEAMLESS_HF_MODEL_ID",
        "facebook/hf-seamless-m4t-medium",
    )
    device = _resolve_device()
    logger.info("Loading SeamlessM4T model_id=%s device=%s", model_id, device)
    processor = AutoProcessor.from_pretrained(model_id)
    model = SeamlessM4TModel.from_pretrained(model_id).to(device)
    model.eval()
    return processor, model, device


def translate_speech_file(
    source_wav: Path,
    output_wav: Path,
    *,
    src_lang: str,
    tgt_lang: str,
) -> None:
    """
    Speech-to-speech: 16 kHz mono WAV in → translated speech WAV out.

    src_lang / tgt_lang: Seamless codes (e.g. deu, ukr) from lang_mapping.
    """
    processor, model, device = _model_bundle()
    audio = _load_audio_mono_16k(source_wav)

    inputs = processor(
        audios=audio,
        sampling_rate=SAMPLE_RATE_HZ,
        src_lang=src_lang,
        return_tensors="pt",
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}

    generate_kwargs: dict = {
        "tgt_lang": tgt_lang,
        "generate_speech": True,
    }
    max_new_tokens = getattr(settings, "SEAMLESS_MAX_NEW_TOKENS", None)
    if max_new_tokens:
        generate_kwargs["max_new_tokens"] = int(max_new_tokens)

    logger.info(
        "Seamless S2ST src_lang=%s tgt_lang=%s samples=%d",
        src_lang,
        tgt_lang,
        len(audio),
    )

    with torch.no_grad():
        output = model.generate(**inputs, **generate_kwargs)

    translated = _waveform_from_generate(output)
    if translated.size == 0:
        raise RuntimeError("SeamlessM4T returned empty audio")

    peak = float(np.max(np.abs(translated))) if translated.size else 0.0
    if peak > 1.0:
        translated = translated / peak

    sf.write(str(output_wav), translated, SAMPLE_RATE_HZ)
    logger.info("Seamless S2ST wrote %s (%d samples)", output_wav, translated.size)
