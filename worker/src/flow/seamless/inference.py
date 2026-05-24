from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from django.conf import settings

from common.compute_device import log_compute_init, resolve_torch_device
from config.json_log import log_event

logger = logging.getLogger(__name__)

SAMPLE_RATE_HZ = 16_000
# Default HF generation_config uses max_new_tokens=256 (~10s of speech output).
_TOKENS_PER_10S_SPEECH = 256
_T2U_TOKENS_MULTIPLIER = 4


def _resolve_device() -> torch.device:
    device, _info = resolve_torch_device(
        getattr(settings, "SEAMLESS_DEVICE", "auto") or "auto"
    )
    return device


def _enable_hf_hub_logging() -> None:
    """Surface Hugging Face download / cache progress in container stdout."""
    os.environ.setdefault("HF_HUB_ENABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "info")
    for name in ("huggingface_hub", "transformers", "filelock"):
        hf_logger = logging.getLogger(name)
        hf_logger.setLevel(logging.INFO)
        hf_logger.propagate = True


def _log_model_load(phase: str, *, layer: str = "worker", model_id: str, **fields) -> None:
    log_event(
        logger,
        logging.INFO,
        f"worker.seamless.model.load.{phase}",
        layer=layer,
        component="seamless_m4t",
        model_id=model_id,
        **fields,
    )


def _is_seamless_v2_model(model_id: str, load_path: str | Path) -> bool:
    if "m4t-v2" in model_id or "seamless-m4t-v2" in model_id:
        return True

    config_path = Path(load_path) / "config.json"
    if not config_path.is_file():
        return False

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, ValueError):
        return False
    return config.get("model_type") == "seamless_m4t_v2"


def _model_load_path(model_id: str) -> str | Path:
    local_dir = (getattr(settings, "SEAMLESS_MODEL_LOCAL_DIR", "") or "").strip()
    if not local_dir:
        return model_id

    model_dir = Path(local_dir)
    if not (model_dir / "config.json").is_file():
        raise FileNotFoundError(f"config.json missing under {model_dir}")
    return model_dir


def log_seamless_device_init(*, layer: str = "worker") -> None:
    """Log CUDA/CPU choice at worker start (does not load the HF model)."""
    requested = getattr(settings, "SEAMLESS_DEVICE", "auto") or "auto"
    _device, info = resolve_torch_device(requested)
    log_compute_init(
        logger,
        "worker.seamless.device.init",
        component="seamless_m4t",
        requested=requested,
        resolved=info["resolved"],
        using_gpu=info["using_gpu"],
        layer=layer,
        **{k: info[k] for k in ("cuda_available", "cuda_device_count", "cuda_device_name", "mps_available") if k in info},
    )


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


def _load_model_bundle(*, layer: str = "worker"):
    from transformers import AutoProcessor, SeamlessM4TModel

    try:
        from transformers import SeamlessM4Tv2Model
    except ImportError:
        SeamlessM4Tv2Model = None

    _enable_hf_hub_logging()

    bundle_t0 = time.monotonic()
    model_id = getattr(
        settings,
        "SEAMLESS_HF_MODEL_ID",
        "facebook/hf-seamless-m4t-medium",
    )
    requested = getattr(settings, "SEAMLESS_DEVICE", "auto") or "auto"
    device, info = resolve_torch_device(requested)

    _log_model_load(
        "start",
        layer=layer,
        model_id=model_id,
        requested_device=requested,
        resolved_device=info["resolved"],
        using_gpu=info["using_gpu"],
        **{k: info[k] for k in ("cuda_available", "cuda_device_count", "cuda_device_name", "mps_available") if k in info},
    )
    log_compute_init(
        logger,
        "worker.seamless.model.init",
        component="seamless_m4t",
        requested=requested,
        resolved=info["resolved"],
        using_gpu=info["using_gpu"],
        layer=layer,
        model_id=model_id,
        **{k: info[k] for k in ("cuda_available", "cuda_device_count", "cuda_device_name", "mps_available") if k in info},
    )

    load_path = _model_load_path(model_id)
    source = "local" if isinstance(load_path, Path) else "huggingface"
    _log_model_load(
        "source",
        layer=layer,
        model_id=model_id,
        source=source,
        load_path=str(load_path),
    )

    t0 = time.monotonic()
    _log_model_load("processor", layer=layer, model_id=model_id, status="loading")
    processor = AutoProcessor.from_pretrained(load_path)
    _log_model_load(
        "processor",
        layer=layer,
        model_id=model_id,
        status="ready",
        duration_sec=round(time.monotonic() - t0, 2),
    )

    model_class = SeamlessM4TModel
    if _is_seamless_v2_model(model_id, load_path):
        if SeamlessM4Tv2Model is None:
            raise ImportError("Installed transformers does not provide SeamlessM4Tv2Model")
        model_class = SeamlessM4Tv2Model

    t1 = time.monotonic()
    _log_model_load(
        "weights",
        layer=layer,
        model_id=model_id,
        status="loading",
        model_class=model_class.__name__,
    )
    model = model_class.from_pretrained(load_path)
    _log_model_load(
        "weights",
        layer=layer,
        model_id=model_id,
        status="ready",
        model_class=model_class.__name__,
        duration_sec=round(time.monotonic() - t1, 2),
    )

    t2 = time.monotonic()
    _log_model_load(
        "device_transfer",
        layer=layer,
        model_id=model_id,
        status="started",
        target_device=str(device),
    )
    model = model.to(device)
    model.eval()
    _log_model_load(
        "device_transfer",
        layer=layer,
        model_id=model_id,
        status="ready",
        target_device=str(device),
        duration_sec=round(time.monotonic() - t2, 2),
    )

    total_sec = round(time.monotonic() - t0, 2)
    _log_model_load(
        "complete",
        layer=layer,
        model_id=model_id,
        resolved_device=info["resolved"],
        duration_sec=round(time.monotonic() - bundle_t0, 2),
        model_load_sec=total_sec,
    )
    return processor, model, device


_model_bundle_cache: tuple[Any, Any, torch.device] | None = None


def warm_seamless_model(*, layer: str = "worker") -> None:
    """Preload SeamlessM4T at worker start so load progress appears in container logs."""
    global _model_bundle_cache
    model_id = _seamless_model_id()
    if _model_bundle_cache is not None:
        _log_model_load("skipped", layer=layer, model_id=model_id, reason="already_loaded")
        return
    _log_model_load("scheduled", layer=layer, model_id=model_id)
    _model_bundle_cache = _load_model_bundle(layer=layer)


def _seamless_model_id() -> str:
    return getattr(settings, "SEAMLESS_HF_MODEL_ID", "facebook/hf-seamless-m4t-medium")


def _model_bundle():
    global _model_bundle_cache
    if _model_bundle_cache is None:
        _model_bundle_cache = _load_model_bundle(layer="pipeline")
    return _model_bundle_cache


def _generation_limits_for_audio(num_samples: int) -> dict[str, int]:
    """Scale token limits with source length so generation is not cut to ~9s."""
    duration_sec = num_samples / SAMPLE_RATE_HZ
    env_cap = int(getattr(settings, "SEAMLESS_MAX_NEW_TOKENS", 0) or 0)
    if env_cap > 0:
        max_new_tokens = env_cap
    else:
        max_new_tokens = max(
            _TOKENS_PER_10S_SPEECH,
            int(_TOKENS_PER_10S_SPEECH * (duration_sec / 10.0) * 1.25),
        )
    max_new_tokens = min(max_new_tokens, 4096)
    t2u_max_new_tokens = min(max(1024, max_new_tokens * _T2U_TOKENS_MULTIPLIER), 4096)
    return {
        "max_new_tokens": max_new_tokens,
        "t2u_max_new_tokens": t2u_max_new_tokens,
    }


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

    token_limits = _generation_limits_for_audio(len(audio))
    source_duration_sec = round(len(audio) / SAMPLE_RATE_HZ, 2)
    generate_kwargs: dict = {
        "tgt_lang": tgt_lang,
        "generate_speech": True,
        **token_limits,
    }

    log_event(
        logger,
        logging.INFO,
        "worker.seamless.translate.start",
        layer="pipeline",
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        source_samples=len(audio),
        source_duration_sec=source_duration_sec,
        **token_limits,
    )

    with torch.no_grad():
        output = model.generate(**inputs, **generate_kwargs)

    translated = _waveform_from_generate(output)
    if translated.size == 0:
        raise RuntimeError("SeamlessM4T returned empty audio")

    peak = float(np.max(np.abs(translated))) if translated.size else 0.0
    if peak > 1.0:
        translated = translated / peak

    raw_wav = output_wav.with_name(f"{output_wav.stem}_raw.wav")
    sf.write(str(raw_wav), translated, SAMPLE_RATE_HZ)
    raw_duration_sec = round(len(translated) / SAMPLE_RATE_HZ, 2)

    from common.media import match_audio_duration

    stretch_info = match_audio_duration(source_wav, raw_wav, output_wav)
    log_event(
        logger,
        logging.INFO,
        "worker.seamless.translate.duration",
        layer="pipeline",
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        source_duration_sec=source_duration_sec,
        raw_duration_sec=raw_duration_sec,
        output_duration_sec=stretch_info["output_sec"],
        duration_stretched=bool(stretch_info.get("stretched")),
        **token_limits,
    )
