from django.urls import path

from video.views import UploadUrlView, VideoCreateView, VideoDetailView, VideoDownloadView

urlpatterns = [
    path("videos/upload-url", UploadUrlView.as_view(), name="video-upload-url"),
    path("videos", VideoCreateView.as_view(), name="video-create"),
    path("videos/<uuid:video_id>", VideoDetailView.as_view(), name="video-detail"),
    path("videos/<uuid:video_id>/download", VideoDownloadView.as_view(), name="video-download"),
]
