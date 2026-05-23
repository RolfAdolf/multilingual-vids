import logging

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.json_log import log_event, log_exception
from storage import s3
from video.models import Video, VideoStatus
from video.serializers import (
    UploadUrlRequestSerializer,
    UploadUrlResponseSerializer,
    VideoCreateSerializer,
    VideoResponseSerializer,
)
from video.repository import VideoRepository
from video.services import VideoServiceError, create_upload_url, create_video_job, enqueue_translation

logger = logging.getLogger(__name__)
_repo = VideoRepository()


def _request_id(request) -> str | None:
    return getattr(request, "request_id", None)


class UploadUrlView(APIView):
    def post(self, request):
        rid = _request_id(request)
        log_event(
            logger,
            logging.INFO,
            "video.api.upload_url.request",
            layer="handler",
            request_id=rid,
        )
        serializer = UploadUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = create_upload_url(
                **serializer.validated_data, request_id=rid
            )
        except VideoServiceError as exc:
            log_event(
                logger,
                logging.WARNING,
                "video.api.upload_url.error",
                layer="handler",
                request_id=rid,
                status_code=exc.status_code,
                detail=exc.message,
            )
            return Response({"detail": exc.message}, status=exc.status_code)

        payload.pop("video_id", None)
        return Response(UploadUrlResponseSerializer(payload).data, status=status.HTTP_201_CREATED)


class VideoListCreateView(APIView):
    def get(self, request):
        rid = _request_id(request)
        status_filter = request.query_params.get("status", "").upper()
        limit = min(int(request.query_params.get("limit", 50)), 100)
        log_event(
            logger,
            logging.INFO,
            "video.api.list.request",
            layer="handler",
            request_id=rid,
            status_filter=status_filter or None,
            limit=limit,
        )
        qs = Video.objects.select_related("model").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        videos = qs[:limit]
        return Response({"items": VideoResponseSerializer(videos, many=True).data})

    def post(self, request):
        rid = _request_id(request)
        log_event(
            logger,
            logging.INFO,
            "video.api.create.request",
            layer="handler",
            request_id=rid,
        )
        serializer = VideoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        idempotency_key = request.headers.get("Idempotency-Key")

        filename = data.get("original_filename") or data["object_key"].rsplit("/", 1)[-1]
        try:
            video, created = create_video_job(
                object_key=data["object_key"],
                source=data["source"].lower(),
                target=data["target"].lower(),
                model_id=data.get("model_id"),
                original_filename=filename,
                content_type=None,
                file_size_bytes=None,
                idempotency_key=idempotency_key,
                request_id=rid,
            )
        except VideoServiceError as exc:
            log_event(
                logger,
                logging.WARNING,
                "video.api.create.error",
                layer="handler",
                request_id=rid,
                status_code=exc.status_code,
                detail=exc.message,
            )
            return Response({"detail": exc.message}, status=exc.status_code)

        if created:
            try:
                enqueue_translation(video, request_id=rid)
            except Exception as exc:
                log_exception(
                    logger,
                    "video.api.create.enqueue_failed",
                    layer="handler",
                    exc=exc,
                    request_id=rid,
                    video_id=str(video.id),
                    model_slug=video.model.slug,
                    worker_queue=video.model.worker_queue,
                )
                _repo.mark_error(
                    video,
                    f"Failed to enqueue task: {exc}",
                    request_id=rid,
                )
                body = {"detail": "Failed to enqueue task."}
                if rid:
                    body["request_id"] = rid
                return Response(body, status=503)

        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        log_event(
            logger,
            logging.INFO,
            "video.api.create.success",
            layer="handler",
            request_id=rid,
            video_id=str(video.id),
            created=created,
            status_code=code,
        )
        return Response(VideoResponseSerializer(video).data, status=code)


class VideoDetailView(APIView):
    def get(self, request, video_id):
        rid = _request_id(request)
        log_event(
            logger,
            logging.DEBUG,
            "video.api.detail.request",
            layer="handler",
            request_id=rid,
            video_id=str(video_id),
        )
        video = get_object_or_404(Video.objects.select_related("model"), pk=video_id)
        return Response(VideoResponseSerializer(video).data)


class VideoDownloadView(APIView):
    def get(self, request, video_id):
        rid = _request_id(request)
        video = get_object_or_404(Video, pk=video_id)
        if video.status != VideoStatus.SUCCESS or not video.output_object_key:
            log_event(
                logger,
                logging.WARNING,
                "video.api.download.not_ready",
                layer="handler",
                request_id=rid,
                video_id=str(video_id),
                status=video.status,
            )
            return Response({"detail": "Video is not ready for download."}, status=409)
        url = s3.presigned_get_url(video.output_object_key)
        log_event(
            logger,
            logging.INFO,
            "video.api.download.redirect",
            layer="handler",
            request_id=rid,
            video_id=str(video_id),
        )
        return HttpResponseRedirect(url)
