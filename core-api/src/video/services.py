from __future__ import annotations

import logging
import uuid

from botocore.exceptions import ClientError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from config.json_log import log_event, log_exception
from storage import s3
from translation_models.models import ModelLanguage, TranslationModel
from video.models import Video, VideoStatus
from video.repository import VideoRepository

logger = logging.getLogger(__name__)
_repo = VideoRepository()


class VideoServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _normalize_content_type(content_type: str, filename: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in settings.ALLOWED_VIDEO_CONTENT_TYPES:
        return ct
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    by_ext = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
    }
    return by_ext.get(ext, "video/mp4")


def create_upload_url(
    filename: str,
    content_type: str,
    size_bytes: int,
    *,
    request_id: str | None = None,
) -> dict:
    log_event(
        logger,
        logging.INFO,
        "video.service.create_upload_url.start",
        layer="service",
        request_id=request_id,
        filename=filename,
        size_bytes=size_bytes,
    )
    content_type = _normalize_content_type(content_type, filename)
    if content_type not in settings.ALLOWED_VIDEO_CONTENT_TYPES:
        log_event(
            logger,
            logging.WARNING,
            "video.service.create_upload_url.unsupported_type",
            layer="service",
            request_id=request_id,
            content_type=content_type,
        )
        raise VideoServiceError("Unsupported content type.", 415)
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        log_event(
            logger,
            logging.WARNING,
            "video.service.create_upload_url.too_large",
            layer="service",
            request_id=request_id,
            size_bytes=size_bytes,
            max_bytes=settings.MAX_UPLOAD_BYTES,
        )
        raise VideoServiceError("File too large.", 413)

    video_id = uuid.uuid4()
    object_key = s3.upload_object_key(video_id, filename)
    upload_url = s3.presigned_put_url(
        object_key, content_type, content_length=size_bytes
    )
    log_event(
        logger,
        logging.INFO,
        "video.service.create_upload_url.success",
        layer="service",
        request_id=request_id,
        video_id=str(video_id),
        object_key=object_key,
    )
    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": settings.S3_PRESIGNED_TTL_SECONDS,
        "method": "PUT",
        "headers": {
            "Content-Type": content_type,
            "Content-Length": str(size_bytes),
        },
        "video_id": video_id,
    }


def _resolve_model(
    source: str,
    target: str,
    model_id: uuid.UUID | None,
    *,
    request_id: str | None = None,
) -> TranslationModel:
    qs = ModelLanguage.objects.filter(
        model__is_active=True,
        source_language_code=source,
        target_language_code=target,
    ).select_related("model")
    if not qs.exists():
        log_event(
            logger,
            logging.WARNING,
            "video.service.resolve_model.no_pair",
            layer="service",
            request_id=request_id,
            source=source,
            target=target,
        )
        raise VideoServiceError("No model supports this language pair.", 400)

    if model_id:
        try:
            model = TranslationModel.objects.get(pk=model_id, is_active=True)
            log_event(
                logger,
                logging.DEBUG,
                "video.service.resolve_model.by_id",
                layer="service",
                request_id=request_id,
                model_id=str(model_id),
                model_slug=model.slug,
            )
            return model
        except TranslationModel.DoesNotExist as exc:
            log_event(
                logger,
                logging.WARNING,
                "video.service.resolve_model.not_found",
                layer="service",
                request_id=request_id,
                model_id=str(model_id),
            )
            raise VideoServiceError("Model not found.", 404) from exc

    row = qs.order_by("-bleu").first()
    log_event(
        logger,
        logging.DEBUG,
        "video.service.resolve_model.auto",
        layer="service",
        request_id=request_id,
        model_slug=row.model.slug,
    )
    return row.model


def _verify_uploaded_object(
    object_key: str,
    expected_size: int | None = None,
    *,
    request_id: str | None = None,
) -> dict:
    log_event(
        logger,
        logging.DEBUG,
        "video.service.verify_object.start",
        layer="service",
        request_id=request_id,
        object_key=object_key,
    )
    try:
        head = s3.head_object(object_key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        log_exception(
            logger,
            "video.service.verify_object.storage_error",
            layer="service",
            exc=exc,
            request_id=request_id,
            object_key=object_key,
            s3_error_code=code,
        )
        if code in ("404", "NoSuchKey", "NotFound"):
            raise VideoServiceError(
                "Object not found in storage. Upload the file first.", 400
            ) from exc
        raise VideoServiceError("Storage error.", 502) from exc

    size = head.get("ContentLength")
    if expected_size and size:
        tolerance = max(expected_size * 0.01, 1024)
        if abs(size - expected_size) > tolerance:
            log_event(
                logger,
                logging.WARNING,
                "video.service.verify_object.size_mismatch",
                layer="service",
                request_id=request_id,
                object_key=object_key,
                expected_size=expected_size,
                actual_size=size,
            )
            raise VideoServiceError("Uploaded file size mismatch.", 400)
    log_event(
        logger,
        logging.DEBUG,
        "video.service.verify_object.success",
        layer="service",
        request_id=request_id,
        object_key=object_key,
        content_length=size,
    )
    return head


@transaction.atomic
def create_video_job(
    *,
    object_key: str,
    source: str,
    target: str,
    model_id: uuid.UUID | None,
    original_filename: str,
    content_type: str | None,
    file_size_bytes: int | None,
    idempotency_key: str | None,
    request_id: str | None = None,
) -> tuple[Video, bool]:
    log_event(
        logger,
        logging.INFO,
        "video.service.create_video_job.start",
        layer="service",
        request_id=request_id,
        object_key=object_key,
        source=source,
        target=target,
        model_id=str(model_id) if model_id else None,
        idempotency_key=idempotency_key,
    )
    if idempotency_key:
        existing = _repo.find_by_idempotency_key(
            idempotency_key, request_id=request_id
        )
        if existing:
            log_event(
                logger,
                logging.INFO,
                "video.service.create_video_job.idempotent_hit",
                layer="service",
                request_id=request_id,
                video_id=str(existing.id),
            )
            return existing, False

    _verify_uploaded_object(object_key, file_size_bytes, request_id=request_id)
    model = _resolve_model(source, target, model_id, request_id=request_id)

    parts = object_key.strip("/").split("/")
    video_id = (
        uuid.UUID(parts[1])
        if len(parts) >= 2 and parts[0] == "uploads"
        else uuid.uuid4()
    )

    video = _repo.create(
        video_id=video_id,
        original_filename=original_filename,
        model=model,
        source=source,
        target=target,
        input_object_key=object_key,
        content_type=content_type or "",
        file_size_bytes=file_size_bytes,
        idempotency_key=idempotency_key,
        request_id=request_id,
    )
    log_event(
        logger,
        logging.INFO,
        "video.service.create_video_job.created",
        layer="service",
        request_id=request_id,
        video_id=str(video.id),
        worker_queue=model.worker_queue,
    )
    return video, True


def enqueue_translation(video: Video, *, request_id: str | None = None) -> str:
    from config.celery import app as celery_app

    queue = video.model.worker_queue
    log_event(
        logger,
        logging.INFO,
        "video.service.enqueue_translation.start",
        layer="service",
        request_id=request_id,
        video_id=str(video.id),
        model_slug=video.model.slug,
        worker_queue=queue,
        broker_url=settings.CELERY_BROKER_URL.split("@")[-1],
    )
    try:
        async_result = celery_app.send_task(
            "video.translate",
            kwargs={
                "video_id": str(video.id),
                "model_slug": video.model.slug,
                "worker_queue": queue,
            },
            task_id=str(video.id),
            queue=queue,
        )
    except Exception as exc:
        log_exception(
            logger,
            "video.service.enqueue_translation.failed",
            layer="service",
            exc=exc,
            request_id=request_id,
            video_id=str(video.id),
            worker_queue=queue,
        )
        raise

    _repo.save_celery_task_id(
        video, async_result.id, request_id=request_id
    )
    log_event(
        logger,
        logging.INFO,
        "video.service.enqueue_translation.success",
        layer="service",
        request_id=request_id,
        video_id=str(video.id),
        celery_task_id=async_result.id,
        worker_queue=queue,
    )
    return async_result.id


def mark_video_processing(video_id: uuid.UUID, progress: int = 5) -> None:
    Video.objects.filter(pk=video_id).update(
        status=VideoStatus.PROCESSING,
        progress=progress,
        started_at=timezone.now(),
        updated_at=timezone.now(),
    )


def mark_video_success(
    video_id: uuid.UUID,
    output_object_key: str,
    artifact_key: dict | None = None,
) -> None:
    updates = {
        "status": VideoStatus.SUCCESS,
        "progress": 100,
        "output_object_key": output_object_key,
        "finished_at": timezone.now(),
        "updated_at": timezone.now(),
        "error_message": None,
    }
    if artifact_key is not None:
        updates["artifact_key"] = artifact_key
    Video.objects.filter(pk=video_id).update(**updates)


def mark_video_error(video_id: uuid.UUID, error_message: str) -> None:
    Video.objects.filter(pk=video_id).update(
        status=VideoStatus.ERROR,
        error_message=error_message[:2000],
        finished_at=timezone.now(),
        updated_at=timezone.now(),
        celery_task_id=None,
    )


def update_video_progress(video_id: uuid.UUID, progress: int) -> None:
    Video.objects.filter(pk=video_id).update(
        progress=max(0, min(100, progress)),
        updated_at=timezone.now(),
    )
