from __future__ import annotations

import logging
import uuid

from django.utils import timezone

from config.json_log import log_event
from translation_models.models import TranslationModel
from video.models import Video, VideoStatus

logger = logging.getLogger(__name__)


class VideoRepository:
    def find_by_idempotency_key(self, key: str, *, request_id: str | None = None) -> Video | None:
        log_event(
            logger,
            logging.DEBUG,
            "video.repository.find_by_idempotency_key",
            layer="repository",
            request_id=request_id,
            idempotency_key=key,
        )
        return Video.objects.filter(idempotency_key=key).first()

    def create(
        self,
        *,
        video_id: uuid.UUID,
        original_filename: str,
        model: TranslationModel,
        source: str,
        target: str,
        input_object_key: str,
        content_type: str,
        file_size_bytes: int | None,
        idempotency_key: str | None,
        request_id: str | None = None,
    ) -> Video:
        log_event(
            logger,
            logging.INFO,
            "video.repository.create",
            layer="repository",
            request_id=request_id,
            video_id=str(video_id),
            model_id=str(model.id),
            model_slug=model.slug,
            source=source,
            target=target,
            input_object_key=input_object_key,
        )
        return Video.objects.create(
            id=video_id,
            original_filename=original_filename,
            model=model,
            source_language_code=source,
            target_language_code=target,
            input_object_key=input_object_key,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            idempotency_key=idempotency_key,
            status=VideoStatus.WAITING,
        )

    def save_celery_task_id(
        self,
        video: Video,
        task_id: str,
        *,
        request_id: str | None = None,
    ) -> None:
        log_event(
            logger,
            logging.INFO,
            "video.repository.save_celery_task_id",
            layer="repository",
            request_id=request_id,
            video_id=str(video.id),
            celery_task_id=task_id,
        )
        video.celery_task_id = task_id
        video.save(update_fields=["celery_task_id", "updated_at"])

    def mark_error(
        self,
        video: Video,
        error_message: str,
        *,
        request_id: str | None = None,
    ) -> None:
        log_event(
            logger,
            logging.WARNING,
            "video.repository.mark_error",
            layer="repository",
            request_id=request_id,
            video_id=str(video.id),
            error_message=error_message[:500],
        )
        video.status = VideoStatus.ERROR
        video.error_message = error_message[:2000]
        video.finished_at = timezone.now()
        video.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
