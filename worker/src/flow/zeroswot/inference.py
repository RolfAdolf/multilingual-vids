from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import torch
import torchaudio
from django.conf import settings
from transformers import AutoModel, AutoModelForSeq2SeqLM, NllbTokenizer, Wav2Vec2Processor

from common.compute_device import log_compute_init, resolve_torch_device
from config.json_log import log_event

logger = logging.getLogger(__name__)

SAMPLE_RATE_HZ = 16_000

_ModelBundle = tuple[
    Wav2Vec2Processor,
    Any,
    AutoModelForSeq2SeqLM,
    NllbTokenizer,
    torch.device,
]

_model_bundle_cache: _ModelBundle | None = None


def _encoder_hf_id() -> str:
    return getattr(
        settings,
        "ZEROSWOT_ENCODER_HF_ID",
        "johntsi/ZeroSwot-Large_asr-cv_en-to-200",
    )


def _encoder_revision() -> str:
    return getattr(
        settings,
        "ZEROSWOT_ENCODER_REVISION",
        "fc0da35496bd26102f342b0694a3a89791eb713c",
    )


def _wav2vec_processor_id() -> str:
    return getattr(
        settings,
        "ZEROSWOT_WAV2VEC_PROCESSOR_ID",
        "facebook/wav2vec2-large-960h-lv60-self",
    )


def _nllb_hf_id() -> str:
    return getattr(
        settings,
        "ZEROSWOT_NLLB_HF_ID",
        "facebook/nllb-200-distilled-1.3B",
    )


def _resolve_device() -> torch.device:
    device, _info = resolve_torch_device(
        getattr(settings, "ZEROSWOT_DEVICE", "auto") or "auto"
    )
    return device


def log_zeroswot_device_init(*, layer: str = "worker") -> None:
    requested = getattr(settings, "ZEROSWOT_DEVICE", "auto") or "auto"
    _device, info = resolve_torch_device(requested)
    log_compute_init(
        logger,
        "worker.zeroswot.device.init",
        component="zeroswot",
        requested=requested,
        resolved=info["resolved"],
        using_gpu=info["using_gpu"],
        layer=layer,
        encoder_hf_id=_encoder_hf_id(),
        **{
            k: info[k]
            for k in (
                "cuda_available",
                "cuda_device_count",
                "cuda_device_name",
                "mps_available",
            )
            if k in info
        },
    )


def _load_audio_mono_16k(wav_path: Path) -> Any:
    audio, orig_freq = torchaudio.load(str(wav_path))
    if orig_freq != SAMPLE_RATE_HZ:
        audio = torchaudio.functional.resample(
            audio,
            orig_freq=orig_freq,
            new_freq=SAMPLE_RATE_HZ,
        )
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)
    return audio.squeeze(0).numpy()


def _load_model_bundle(*, layer: str = "worker") -> _ModelBundle:
    encoder_id = _encoder_hf_id()
    revision = _encoder_revision()
    wav2vec_id = _wav2vec_processor_id()
    nllb_id = _nllb_hf_id()
    requested = getattr(settings, "ZEROSWOT_DEVICE", "auto") or "auto"
    device, info = resolve_torch_device(requested)

    log_event(
        logger,
        logging.INFO,
        "worker.zeroswot.model.load.start",
        layer=layer,
        encoder_hf_id=encoder_id,
        encoder_revision=revision,
        nllb_hf_id=nllb_id,
        wav2vec_processor_id=wav2vec_id,
        resolved_device=info["resolved"],
        using_gpu=info["using_gpu"],
    )

    t0 = time.monotonic()
    processor = Wav2Vec2Processor.from_pretrained(wav2vec_id)
    tokenizer = NllbTokenizer.from_pretrained(nllb_id)
    encoder = AutoModel.from_pretrained(
        encoder_id,
        trust_remote_code=True,
        revision=revision,
    )
    nllb = AutoModelForSeq2SeqLM.from_pretrained(nllb_id)

    encoder.eval()
    nllb.eval()
    encoder.to(device)
    nllb.to(device)

    log_event(
        logger,
        logging.INFO,
        "worker.zeroswot.model.load.complete",
        layer=layer,
        encoder_hf_id=encoder_id,
        nllb_hf_id=nllb_id,
        resolved_device=info["resolved"],
        duration_sec=round(time.monotonic() - t0, 2),
    )
    return processor, encoder, nllb, tokenizer, device


def warm_zeroswot_model(*, layer: str = "worker") -> None:
    global _model_bundle_cache
    if _model_bundle_cache is not None:
        log_event(
            logger,
            logging.INFO,
            "worker.zeroswot.model.warm.skipped",
            layer=layer,
            reason="already_loaded",
        )
        return
    log_event(logger, logging.INFO, "worker.zeroswot.model.warm.scheduled", layer=layer)
    _model_bundle_cache = _load_model_bundle(layer=layer)


def _model_bundle() -> _ModelBundle:
    global _model_bundle_cache
    if _model_bundle_cache is None:
        _model_bundle_cache = _load_model_bundle(layer="pipeline")
    return _model_bundle_cache


def translate_speech_to_text(
    source_wav: Path,
    *,
    tgt_nllb_code: str,
) -> str:
    """16 kHz mono WAV → translated text (ZeroSwot encoder + NLLB decoder)."""
    processor, encoder, nllb, tokenizer, device = _model_bundle()
    audio = _load_audio_mono_16k(source_wav)

    if tgt_nllb_code not in tokenizer.lang_code_to_id:
        raise ValueError(f"Unknown NLLB language code: {tgt_nllb_code}")

    input_values = processor(audio, sampling_rate=SAMPLE_RATE_HZ, return_tensors="pt")
    input_values = {key: value.to(device) for key, value in input_values.items()}

    num_beams = int(getattr(settings, "ZEROSWOT_NUM_BEAMS", 5) or 5)
    bos_id = tokenizer.lang_code_to_id[tgt_nllb_code]

    log_event(
        logger,
        logging.INFO,
        "worker.zeroswot.translate.start",
        layer="pipeline",
        tgt_nllb_code=tgt_nllb_code,
        source_samples=len(audio),
        source_duration_sec=round(len(audio) / SAMPLE_RATE_HZ, 2),
        num_beams=num_beams,
    )

    with torch.no_grad():
        compressed_embeds, attention_mask = encoder(**input_values)
        predicted_ids = nllb.generate(
            inputs_embeds=compressed_embeds,
            attention_mask=attention_mask,
            forced_bos_token_id=bos_id,
            num_beams=num_beams,
        )

    text = tokenizer.decode(predicted_ids[0], skip_special_tokens=True)
    log_event(
        logger,
        logging.INFO,
        "worker.zeroswot.translate.done",
        layer="pipeline",
        tgt_nllb_code=tgt_nllb_code,
        chars=len(text),
    )
    return text
