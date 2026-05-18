from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.utils import timezone

from flow.registry import get_pipeline
from video.models import Video, VideoStatus
from video.services import mark_video_error, mark_video_processing, mark_video_success, update_video_progress

logger = logging.getLogger(__name__)


@shared_task(name="video.translate", bind=True, max_retries=2)
def translate_video_task(self, video_id: str, model_slug: str, worker_queue: str):
    vid = uuid.UUID(video_id)
    video = Video.objects.select_related("model").get(pk=vid)

    if video.status == VideoStatus.SUCCESS:
        logger.info("video_id=%s already SUCCESS, skipping", video_id)
        return

    mark_video_processing(vid, progress=5)
    try:
        pipeline = get_pipeline(model_slug)
        result = pipeline.run(video, progress_callback=lambda p: update_video_progress(vid, p))
        mark_video_success(
            vid,
            output_object_key=result.output_object_key,
            artifact_key=result.artifact_key,
        )
        logger.info("video_id=%s finished SUCCESS", video_id)
    except Exception as exc:
        logger.exception("video_id=%s failed", video_id)
        if self.request.retries < self.max_retries:
            Video.objects.filter(pk=vid).update(
                status=VideoStatus.WAITING,
                updated_at=timezone.now(),
            )
            raise self.retry(exc=exc, countdown=30)
        mark_video_error(vid, str(exc))
        raise
