from django.urls import path

from video.api.views import UploadUrlView, VideoDetailView, VideoDownloadView, VideoListCreateView

urlpatterns = [
    path("videos/upload-url", UploadUrlView.as_view(), name="video-upload-url"),
    path("videos", VideoListCreateView.as_view(), name="video-list-create"),
    path("videos/<uuid:video_id>", VideoDetailView.as_view(), name="video-detail"),
    path("videos/<uuid:video_id>/download", VideoDownloadView.as_view(), name="video-download"),
]
