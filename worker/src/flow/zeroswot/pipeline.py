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
from video.models import Video

logger = logging.getLogger(__name__)


class ZeroSwotPipeline:
    """Placeholder until ZeroSwot encoder + NLLB are wired (§15.4)."""

    def run(self, video: Video, progress_callback) -> PipelineResult:
        bucket_in = settings.YANDEX_S3_BUCKET_UPLOADS
        bucket_out = settings.YANDEX_S3_BUCKET_RESULTS
        client = s3_client()
        prefix = task_prefix(video.id)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_local = local_input_path(tmp_path, video.input_object_key)
            output_local = tmp_path / "translated.mp4"
            wav_local = tmp_path / "source.wav"

            progress_callback(20)
            client.download_file(bucket_in, video.input_object_key, str(source_local))
            ensure_non_empty_file(source_local)

            progress_callback(40)
            extract_audio_mono_16k(source_local, wav_local)

            progress_callback(60)
            mux_video_with_audio(source_local, wav_local, output_local)

            out_key = result_object_key(video.id)
            progress_callback(80)
            client.upload_file(
                str(output_local),
                bucket_out,
                out_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )

            progress_callback(95)
            artifacts = {
                "extracted_audio": f"{prefix}/source.wav",
                "translated_audio": f"{prefix}/translated.wav",
            }
            client.upload_file(
                str(wav_local),
                settings.YANDEX_S3_BUCKET_TEMP,
                artifacts["extracted_audio"],
            )

        return PipelineResult(output_object_key=out_key, artifact_key=artifacts)
