from __future__ import annotations

import logging
import uuid

from django.utils import timezone

from common.media import MediaProcessingError
from config.celery import app
from config.json_log import log_event, log_exception
from config.worker_enabled import is_worker_enabled, worker_disabled_message
from video.models import Video, VideoStatus
from video.services import (
    mark_video_error,
    mark_video_processing,
    mark_video_success,
    update_video_progress,
)

logger = logging.getLogger(__name__)


@app.task(name="video.translate", bind=True, max_retries=2)
def translate_video_task(self, video_id: str, model_slug: str, worker_queue: str):
    task_id = self.request.id
    log_event(
        logger,
        logging.INFO,
        "worker.task.translate.received",
        layer="task",
        task_id=task_id,
        video_id=video_id,
        model_slug=model_slug,
        worker_queue=worker_queue,
        retries=self.request.retries,
    )

    vid = uuid.UUID(video_id)
    try:
        video = Video.objects.select_related("model").get(pk=vid)
    except Video.DoesNotExist as exc:
        log_exception(
            logger,
            "worker.task.translate.video_not_found",
            layer="task",
            exc=exc,
            task_id=task_id,
            video_id=video_id,
        )
        raise

    if video.status == VideoStatus.SUCCESS:
        log_event(
            logger,
            logging.INFO,
            "worker.task.translate.skipped",
            layer="task",
            task_id=task_id,
            video_id=video_id,
            reason="already_success",
        )
        return

    if not is_worker_enabled():
        message = worker_disabled_message()
        mark_video_error(vid, message)
        log_event(
            logger,
            logging.WARNING,
            "worker.task.translate.disabled",
            layer="task",
            task_id=task_id,
            video_id=video_id,
            model_slug=model_slug,
            worker_queue=worker_queue,
            error_message=message,
        )
        return

    mark_video_processing(vid, progress=5)
    log_event(
        logger,
        logging.INFO,
        "worker.task.translate.processing",
        layer="task",
        task_id=task_id,
        video_id=video_id,
        model_slug=model_slug,
        input_object_key=video.input_object_key,
    )

    try:
        from flow.registry import get_pipeline

        pipeline = get_pipeline(model_slug, task_id=task_id)
        result = pipeline.run(
            video,
            progress_callback=lambda p: update_video_progress(vid, p),
        )
        mark_video_success(
            vid,
            output_object_key=result.output_object_key,
            artifact_key=result.artifact_key,
        )
        log_event(
            logger,
            logging.INFO,
            "worker.task.translate.success",
            layer="task",
            task_id=task_id,
            video_id=video_id,
            output_object_key=result.output_object_key,
        )
    except MediaProcessingError as exc:
        mark_video_error(vid, str(exc))
        log_event(
            logger,
            logging.WARNING,
            "worker.task.translate.media_error",
            layer="task",
            task_id=task_id,
            video_id=video_id,
            model_slug=model_slug,
            error_message=str(exc),
        )
        return
    except (ImportError, ModuleNotFoundError) as exc:
        message = (
            f"Worker missing ML dependencies for {model_slug}: {exc}. "
            "Rebuild the worker image with the correct Poetry group."
        )
        mark_video_error(vid, message)
        log_event(
            logger,
            logging.ERROR,
            "worker.task.translate.dependency_error",
            layer="task",
            task_id=task_id,
            video_id=video_id,
            model_slug=model_slug,
            error_message=message,
        )
        return
    except Exception as exc:
        log_exception(
            logger,
            "worker.task.translate.failed",
            layer="task",
            exc=exc,
            task_id=task_id,
            video_id=video_id,
            model_slug=model_slug,
            retry=self.request.retries,
            max_retries=self.max_retries,
        )
        if self.request.retries < self.max_retries:
            Video.objects.filter(pk=vid).update(
                status=VideoStatus.WAITING,
                updated_at=timezone.now(),
            )
            log_event(
                logger,
                logging.WARNING,
                "worker.task.translate.retry",
                layer="task",
                task_id=task_id,
                video_id=video_id,
                retry_in_seconds=30,
            )
            raise self.retry(exc=exc, countdown=30) from exc
        mark_video_error(vid, str(exc))
        raise
