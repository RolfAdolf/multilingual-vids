from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.conf import settings

from common.media import (
    ensure_non_empty_file,
    extract_audio_mono_16k,
    local_input_path,
    mux_video_with_audio,
)
from common.pipeline_base import PipelineResult
from common.s3 import result_object_key, s3_client, task_prefix
from config.json_log import log_event
from flow.zeroshot.mt_client import translate
from flow.zeroshot.stt import transcribe
from flow.zeroshot.tts import synthesize
from languages.lang_mapping import zeroshot_mt_tag_literal
from languages.lang_mapping import ZeroshotPairNotSupportedError, pair_from_video
from video.models import Video

logger = logging.getLogger(__name__)


class ZeroshotPipeline:
    """Whisper STT → zero-shot Transformer MT (<2ru>|<2en>|<2uk>) → edge-tts → mux."""

    def run(self, video: Video, progress_callback) -> PipelineResult:
        try:
            whisper_src, mt_tgt = pair_from_video(video)
        except ZeroshotPairNotSupportedError as exc:
            log_event(
                logger,
                logging.ERROR,
                "worker.pipeline.zeroshot.unsupported_pair",
                layer="pipeline",
                video_id=str(video.id),
                source=video.source_language_code,
                target=video.target_language_code,
                error_message=str(exc),
            )
            raise

        mt_tag = zeroshot_mt_tag_literal(video.target_language_code)
        log_event(
            logger,
            logging.INFO,
            "worker.pipeline.zeroshot.start",
            layer="pipeline",
            video_id=str(video.id),
            api_source=video.source_language_code,
            api_target=video.target_language_code,
            whisper_language=whisper_src,
            mt_tag=mt_tag,
            mt_target_code=mt_tgt,
        )

        bucket_in = settings.YANDEX_S3_BUCKET_UPLOADS
        bucket_out = settings.YANDEX_S3_BUCKET_RESULTS
        client = s3_client()
        prefix = task_prefix(video.id)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_video = local_input_path(tmp_path, video.input_object_key)
            source_wav = tmp_path / "source.wav"
            translated_wav = tmp_path / "translated.wav"
            output_video = tmp_path / "translated.mp4"
            transcript_file = tmp_path / "transcript.txt"

            progress_callback(5)
            client.download_file(bucket_in, video.input_object_key, str(source_video))
            ensure_non_empty_file(source_video)

            progress_callback(15)
            extract_audio_mono_16k(source_video, source_wav)

            progress_callback(30)
            logger.info("video_id=%s STT start lang=%s", video.id, whisper_src)
            transcript = transcribe(source_wav, video.source_language_code)
            transcript_file.write_text(transcript, encoding="utf-8")
            logger.info("video_id=%s STT done: %d chars", video.id, len(transcript))

            progress_callback(55)
            logger.info("video_id=%s MT start tag=%s", video.id, mt_tag)
            translated_text = translate(transcript, video.target_language_code)
            logger.info("video_id=%s MT done: %d chars", video.id, len(translated_text))

            progress_callback(70)
            synthesize(translated_text, video.target_language_code, translated_wav)

            progress_callback(85)
            mux_video_with_audio(source_video, translated_wav, output_video)

            out_key = result_object_key(video.id)
            client.upload_file(
                str(output_video),
                bucket_out,
                out_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )

            artifacts = {
                "extracted_audio": f"{prefix}/source.wav",
                "translated_audio": f"{prefix}/translated.wav",
                "transcript": f"{prefix}/transcript.txt",
            }
            client.upload_file(str(source_wav), settings.YANDEX_S3_BUCKET_TEMP, artifacts["extracted_audio"])
            client.upload_file(
                str(translated_wav),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["translated_audio"],
            )
            client.upload_file(
                str(transcript_file),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["transcript"],
                ExtraArgs={"ContentType": "text/plain; charset=utf-8"},
            )

        progress_callback(98)
        return PipelineResult(output_object_key=out_key, artifact_key=artifacts)
