from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.conf import settings

from common.media import extract_audio_mono_16k, mux_video_with_audio
from common.pipeline_base import PipelineResult
from common.s3 import result_object_key, s3_client, task_prefix
from flow.zeroshot.mt_client import translate_de_to_uk
from flow.zeroshot.stt import transcribe_german
from flow.zeroshot.tts import synthesize_ukrainian
from video.models import Video

logger = logging.getLogger(__name__)


class ZeroshotPipeline:
    """Whisper STT (de) → zero-shot Transformer MT (→ uk) → edge-tts → mux."""

    def run(self, video: Video, progress_callback) -> PipelineResult:
        bucket_in = settings.YANDEX_S3_BUCKET_UPLOADS
        bucket_out = settings.YANDEX_S3_BUCKET_RESULTS
        client = s3_client()
        prefix = task_prefix(video.id)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_video = tmp_path / "source"
            source_wav = tmp_path / "source.wav"
            translated_wav = tmp_path / "translated.wav"
            output_video = tmp_path / "translated.mp4"
            transcript_file = tmp_path / "transcript.txt"

            progress_callback(5)
            client.download_file(bucket_in, video.input_object_key, str(source_video))

            progress_callback(15)
            extract_audio_mono_16k(source_video, source_wav)

            progress_callback(30)
            logger.info("video_id=%s STT start", video.id)
            german_text = transcribe_german(source_wav)
            transcript_file.write_text(german_text, encoding="utf-8")
            logger.info("video_id=%s STT done: %d chars", video.id, len(german_text))

            progress_callback(55)
            logger.info("video_id=%s MT start", video.id)
            ukrainian_text = translate_de_to_uk(german_text)
            logger.info("video_id=%s MT done: %d chars", video.id, len(ukrainian_text))

            progress_callback(70)
            synthesize_ukrainian(ukrainian_text, translated_wav)

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
