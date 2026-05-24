from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.conf import settings

from common.media import (
    ensure_non_empty_file,
    extract_audio_mono_16k,
    local_input_path,
    match_audio_duration,
    mux_video_with_audio,
)
from common.pipeline_base import PipelineResult
from common.s3 import result_object_key, s3_client, task_prefix
from config.json_log import log_event
from flow.seamless.inference import translate_speech_file
from languages.lang_mapping import pair_from_video
from video.models import Video

logger = logging.getLogger(__name__)


class SeamlessPipeline:
    """Download video → SeamlessM4T S2ST → mux translated audio → upload."""

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

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_local = local_input_path(tmp_path, video.input_object_key)
            source_wav = tmp_path / "source.wav"
            translated_wav = tmp_path / "translated.wav"
            output_local = tmp_path / "translated.mp4"

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

            progress_callback(25)
            extract_audio_mono_16k(source_local, source_wav)

            progress_callback(40)
            log_event(
                logger,
                logging.INFO,
                "worker.pipeline.seamless.translate",
                layer="pipeline",
                video_id=str(video.id),
                src_lang=src_lang,
                tgt_lang=tgt_lang,
            )
            translate_speech_file(
                source_wav,
                translated_wav,
                src_lang=src_lang,
                tgt_lang=tgt_lang,
            )

            progress_callback(75)
            aligned_wav = tmp_path / "aligned.wav"
            match_audio_duration(source_wav, translated_wav, aligned_wav)
            mux_video_with_audio(source_local, aligned_wav, output_local)

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
                str(source_wav),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["extracted_audio"],
            )
            client.upload_file(
                str(translated_wav),
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
        )
        progress_callback(98)
        return PipelineResult(output_object_key=out_key, artifact_key=artifacts)
