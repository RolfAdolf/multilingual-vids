from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.conf import settings

from common.media import (
    concat_video_segments,
    concat_wav_files,
    cut_video_segment,
    ensure_non_empty_file,
    extract_audio_mono_16k,
    iter_segment_ranges,
    local_input_path,
    match_audio_duration,
    mux_video_with_audio,
    probe_media_duration_sec,
)
from common.pipeline_base import PipelineResult
from common.s3 import result_object_key, s3_client, task_prefix
from config.json_log import log_event
from flow.zeroswot.inference import translate_speech_to_text
from flow.zeroswot.tts import synthesize
from languages.lang_mapping import (
    UnknownLanguageCodeError,
    normalize_zeroswot_api_code,
    pair_from_video,
)
from video.models import Video

logger = logging.getLogger(__name__)

EN_SOURCE_API = "en"


class ZeroSwotSourceNotSupportedError(ValueError):
    """ZeroSwot-Large_asr-cv is trained for English source speech only."""


def _video_chunk_seconds() -> float:
    explicit = float(getattr(settings, "ZEROSWOT_VIDEO_CHUNK_SECONDS", 30))
    if explicit > 0:
        return explicit
    legacy = float(getattr(settings, "ZEROSWOT_CHUNK_MAX_SECONDS", 30))
    return legacy if legacy > 0 else 30.0


def _require_english_source(video: Video) -> None:
    src = normalize_zeroswot_api_code(video.source_language_code)
    if src != EN_SOURCE_API:
        raise ZeroSwotSourceNotSupportedError(
            f"ZeroSwot encoder supports English source only (got '{video.source_language_code}'). "
            "Choose source language English or another translation model."
        )


class ZeroSwotPipeline:
    """Download video → ZeroSwot+NLLB (text) → edge-tts → mux (optional per-segment)."""

    def run(self, video: Video, progress_callback) -> PipelineResult:
        _require_english_source(video)
        try:
            _src_nllb, tgt_nllb = pair_from_video(video)
        except UnknownLanguageCodeError as exc:
            log_event(
                logger,
                logging.ERROR,
                "worker.pipeline.zeroswot.unsupported_language",
                layer="pipeline",
                video_id=str(video.id),
                source=video.source_language_code,
                target=video.target_language_code,
                error_message=str(exc),
            )
            raise

        log_event(
            logger,
            logging.INFO,
            "worker.pipeline.zeroswot.start",
            layer="pipeline",
            video_id=str(video.id),
            api_source=video.source_language_code,
            api_target=video.target_language_code,
            tgt_nllb=tgt_nllb,
            encoder_hf_id=getattr(
                settings,
                "ZEROSWOT_ENCODER_HF_ID",
                "johntsi/ZeroSwot-Large_asr-cv_en-to-200",
            ),
        )

        bucket_in = settings.YANDEX_S3_BUCKET_UPLOADS
        bucket_out = settings.YANDEX_S3_BUCKET_RESULTS
        client = s3_client()
        prefix = task_prefix(video.id)
        chunk_sec = _video_chunk_seconds()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_local = local_input_path(tmp_path, video.input_object_key)
            output_local = tmp_path / "translated.mp4"
            full_source_wav = tmp_path / "source.wav"
            full_translated_wav = tmp_path / "translated.wav"
            transcript_file = tmp_path / "transcript.txt"

            progress_callback(10)
            client.download_file(bucket_in, video.input_object_key, str(source_local))
            ensure_non_empty_file(source_local)

            total_sec = probe_media_duration_sec(source_local)
            ranges = iter_segment_ranges(total_sec, chunk_sec)
            log_event(
                logger,
                logging.INFO,
                "worker.pipeline.zeroswot.segment_plan",
                layer="pipeline",
                video_id=str(video.id),
                total_duration_sec=round(total_sec, 2),
                segment_count=len(ranges),
                segment_seconds=chunk_sec,
            )

            segment_outputs: list[Path] = []
            translated_wavs: list[Path] = []
            transcript_parts: list[str] = []

            for index, (start_sec, duration_sec) in enumerate(ranges):
                seg_dir = tmp_path / f"seg_{index:04d}"
                seg_dir.mkdir()
                segment_video = seg_dir / "segment.mp4"
                segment_wav = seg_dir / "source.wav"
                translated_wav = seg_dir / "translated.wav"
                aligned_wav = seg_dir / "aligned.wav"
                segment_out = seg_dir / "out.mp4"

                progress_pct = 20 + int(55 * index / max(len(ranges), 1))
                progress_callback(progress_pct)

                cut_video_segment(
                    source_local,
                    segment_video,
                    start_sec=start_sec,
                    duration_sec=duration_sec,
                )
                extract_audio_mono_16k(segment_video, segment_wav)

                log_event(
                    logger,
                    logging.INFO,
                    "worker.pipeline.zeroswot.segment.translate",
                    layer="pipeline",
                    video_id=str(video.id),
                    segment_index=index,
                    segment_count=len(ranges),
                )
                text = translate_speech_to_text(segment_wav, tgt_nllb_code=tgt_nllb)
                if text.strip():
                    transcript_parts.append(text.strip())

                synthesize(text, video.target_language_code, translated_wav)
                translated_wavs.append(translated_wav)

                match_audio_duration(segment_wav, translated_wav, aligned_wav)
                mux_video_with_audio(segment_video, aligned_wav, segment_out)
                segment_outputs.append(segment_out)

            progress_callback(80)
            concat_video_segments(segment_outputs, output_local)
            extract_audio_mono_16k(source_local, full_source_wav)
            concat_wav_files(translated_wavs, full_translated_wav)

            transcript = "\n\n".join(transcript_parts)
            transcript_file.write_text(transcript, encoding="utf-8")

            out_key = result_object_key(video.id)
            progress_callback(85)
            client.upload_file(
                str(output_local),
                bucket_out,
                out_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )

            artifacts = {
                "extracted_audio": f"{prefix}/source.wav",
                "translated_audio": f"{prefix}/translated.wav",
                "transcript": f"{prefix}/transcript.txt",
            }
            client.upload_file(
                str(full_source_wav),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["extracted_audio"],
            )
            client.upload_file(
                str(full_translated_wav),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["translated_audio"],
            )
            client.upload_file(
                str(transcript_file),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["transcript"],
                ExtraArgs={"ContentType": "text/plain; charset=utf-8"},
            )

        log_event(
            logger,
            logging.INFO,
            "worker.pipeline.zeroswot.done",
            layer="pipeline",
            video_id=str(video.id),
            output_object_key=out_key,
            segment_count=len(ranges),
            transcript_chars=len(transcript),
        )
        progress_callback(98)
        return PipelineResult(output_object_key=out_key, artifact_key=artifacts)
