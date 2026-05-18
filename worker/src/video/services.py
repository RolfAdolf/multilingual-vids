from __future__ import annotations

import uuid

from botocore.exceptions import ClientError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from translation_models.models import ModelLanguage, TranslationModel
from storage import s3
from video.models import Video, VideoStatus


class VideoServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def create_upload_url(filename: str, content_type: str, size_bytes: int) -> dict:
    if content_type not in settings.ALLOWED_VIDEO_CONTENT_TYPES:
        raise VideoServiceError("Unsupported content type.", 415)
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        raise VideoServiceError("File too large.", 413)

    video_id = uuid.uuid4()
    object_key = s3.upload_object_key(video_id, filename)
    upload_url = s3.presigned_put_url(object_key, content_type)

    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": settings.S3_PRESIGNED_TTL_SECONDS,
        "method": "PUT",
        "video_id": video_id,
    }


def _resolve_model(source: str, target: str, model_id: uuid.UUID | None) -> TranslationModel:
    qs = ModelLanguage.objects.filter(
        model__is_active=True,
        source_language_code=source,
        target_language_code=target,
    ).select_related("model")
    if not qs.exists():
        raise VideoServiceError("No model supports this language pair.", 400)

    if model_id:
        try:
            return TranslationModel.objects.get(pk=model_id, is_active=True)
        except TranslationModel.DoesNotExist as exc:
            raise VideoServiceError("Model not found.", 404) from exc

    row = qs.order_by("-bleu", "-nist").first()
    return row.model


def _verify_uploaded_object(object_key: str, expected_size: int | None = None) -> dict:
    try:
        head = s3.head_object(object_key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise VideoServiceError("Object not found in storage. Upload the file first.", 400) from exc
        raise VideoServiceError("Storage error.", 502) from exc

    size = head.get("ContentLength")
    if expected_size and size:
        tolerance = max(expected_size * 0.01, 1024)
        if abs(size - expected_size) > tolerance:
            raise VideoServiceError("Uploaded file size mismatch.", 400)
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
) -> tuple[Video, bool]:
    if idempotency_key:
        existing = Video.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

    _verify_uploaded_object(object_key, file_size_bytes)
    model = _resolve_model(source, target, model_id)

    parts = object_key.strip("/").split("/")
    video_id = uuid.UUID(parts[1]) if len(parts) >= 2 and parts[0] == "uploads" else uuid.uuid4()

    video = Video.objects.create(
        id=video_id,
        original_filename=original_filename,
        model=model,
        source_language_code=source,
        target_language_code=target,
        input_object_key=object_key,
        content_type=content_type or "",
        file_size_bytes=file_size_bytes,
        idempotency_key=idempotency_key,
        status=VideoStatus.WAITING,
    )
    return video, True


def enqueue_translation(video: Video) -> str:
    from celery import current_app

    async_result = current_app.send_task(
        "video.translate",
        kwargs={
            "video_id": str(video.id),
            "model_slug": video.model.slug,
            "worker_queue": video.model.worker_queue,
        },
        task_id=str(video.id),
        queue=video.model.worker_queue,
    )
    video.celery_task_id = async_result.id
    video.save(update_fields=["celery_task_id", "updated_at"])
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
    )


def update_video_progress(video_id: uuid.UUID, progress: int) -> None:
    Video.objects.filter(pk=video_id).update(
        progress=max(0, min(100, progress)),
        updated_at=timezone.now(),
    )
