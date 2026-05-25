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
from flow.seamless.inference import translate_speech_file
from languages.lang_mapping import pair_from_video
from video.models import Video

logger = logging.getLogger(__name__)


def _video_chunk_seconds() -> float:
    explicit = float(getattr(settings, "SEAMLESS_VIDEO_CHUNK_SECONDS", 5))
    if explicit > 0:
        return explicit
    # Backward compatibility if only the old env name is set.
    legacy = float(getattr(settings, "SEAMLESS_CHUNK_MAX_SECONDS", 5))
    return legacy if legacy > 0 else 5.0


class SeamlessPipeline:
    """Download video → per-segment S2ST → mux each segment → concat → upload."""

    def run(self, video: Video, progress_callback) -> PipelineResult:
        src_lang, tgt_lang = pair_from_video(video)
        log_event(
            logger,
            logging.INFO,
            f"worker.pipeline.{video.model.slug}.start",
            layer="pipeline",
            video_id=str(video.id),
            model_slug=video.model.slug,
            input_object_key=video.input_object_key,
            api_source=video.source_language_code,
            api_target=video.target_language_code,
            model_source_lang=src_lang,
            model_target_lang=tgt_lang,
            hf_model_id=getattr(
                settings, "SEAMLESS_HF_MODEL_ID", "facebook/hf-seamless-m4t-medium"
            ),
        )
        progress_callback(10)
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

            progress_callback(15)
            client.download_file(bucket_in, video.input_object_key, str(source_local))
            input_bytes = ensure_non_empty_file(source_local)
            log_event(
                logger,
                logging.DEBUG,
                "worker.pipeline.seamless.input_downloaded",
                layer="pipeline",
                video_id=str(video.id),
                local_path=source_local.name,
                bytes=input_bytes,
            )

            total_sec = probe_media_duration_sec(source_local)
            ranges = iter_segment_ranges(total_sec, chunk_sec)
            log_event(
                logger,
                logging.INFO,
                "worker.pipeline.seamless.segment_plan",
                layer="pipeline",
                video_id=str(video.id),
                total_duration_sec=round(total_sec, 2),
                segment_count=len(ranges),
                segment_seconds=chunk_sec,
            )

            segment_outputs: list[Path] = []
            translated_wavs: list[Path] = []

            for index, (start_sec, duration_sec) in enumerate(ranges):
                seg_dir = tmp_path / f"seg_{index:04d}"
                seg_dir.mkdir()
                segment_video = seg_dir / "segment.mp4"
                segment_wav = seg_dir / "source.wav"
                translated_wav = seg_dir / "translated.wav"
                aligned_wav = seg_dir / "aligned.wav"
                segment_out = seg_dir / "out.mp4"

                progress_pct = 25 + int(50 * index / max(len(ranges), 1))
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
                    "worker.pipeline.seamless.segment.translate",
                    layer="pipeline",
                    video_id=str(video.id),
                    segment_index=index,
                    segment_count=len(ranges),
                    start_sec=round(start_sec, 2),
                    duration_sec=round(duration_sec, 2),
                )
                translate_speech_file(
                    segment_wav,
                    translated_wav,
                    src_lang=src_lang,
                    tgt_lang=tgt_lang,
                )
                translated_wavs.append(translated_wav)

                # Stretch only within this clip so lip-sync matches the 5s video piece.
                match_audio_duration(segment_wav, translated_wav, aligned_wav)
                mux_video_with_audio(segment_video, aligned_wav, segment_out)
                segment_outputs.append(segment_out)

                log_event(
                    logger,
                    logging.INFO,
                    "worker.pipeline.seamless.segment.done",
                    layer="pipeline",
                    video_id=str(video.id),
                    segment_index=index,
                    segment_count=len(ranges),
                )

            progress_callback(80)
            concat_video_segments(segment_outputs, output_local)
            extract_audio_mono_16k(source_local, full_source_wav)
            full_translated_wav = tmp_path / "translated.wav"
            concat_wav_files(translated_wavs, full_translated_wav)

            out_key = result_object_key(video.id)
            progress_callback(85)
            client.upload_file(
                str(output_local),
                bucket_out,
                out_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )

            progress_callback(92)
            artifacts = {
                "extracted_audio": f"{prefix}/source.wav",
                "translated_audio": f"{prefix}/translated.wav",
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

        log_event(
            logger,
            logging.INFO,
            "worker.pipeline.seamless.done",
            layer="pipeline",
            video_id=str(video.id),
            output_object_key=out_key,
            segment_count=len(ranges),
            segment_seconds=chunk_sec,
        )
        progress_callback(98)
        return PipelineResult(output_object_key=out_key, artifact_key=artifacts)
