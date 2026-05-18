from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from storage import s3
from video.models import Video, VideoStatus
from video.serializers import (
    UploadUrlRequestSerializer,
    UploadUrlResponseSerializer,
    VideoCreateSerializer,
    VideoResponseSerializer,
)
from video.services import VideoServiceError, create_upload_url, create_video_job, enqueue_translation


class UploadUrlView(APIView):
    def post(self, request):
        serializer = UploadUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = create_upload_url(**serializer.validated_data)
        except VideoServiceError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)

        payload.pop("video_id", None)
        return Response(UploadUrlResponseSerializer(payload).data, status=status.HTTP_201_CREATED)


class VideoCreateView(APIView):
    def post(self, request):
        serializer = VideoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        idempotency_key = request.headers.get("Idempotency-Key")

        filename = data["object_key"].rsplit("/", 1)[-1]
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
            )
        except VideoServiceError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)

        if created:
            try:
                enqueue_translation(video)
            except Exception as exc:
                video.status = VideoStatus.ERROR
                video.error_message = str(exc)[:2000]
                video.save(update_fields=["status", "error_message", "updated_at"])
                return Response({"detail": "Failed to enqueue task."}, status=503)

        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(VideoResponseSerializer(video).data, status=code)


class VideoDetailView(APIView):
    def get(self, request, video_id):
        video = get_object_or_404(Video.objects.select_related("model"), pk=video_id)
        return Response(VideoResponseSerializer(video).data)


class VideoDownloadView(APIView):
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        if video.status != VideoStatus.SUCCESS or not video.output_object_key:
            return Response({"detail": "Video is not ready for download."}, status=409)
        url = s3.presigned_get_url(video.output_object_key)
        return HttpResponseRedirect(url)
