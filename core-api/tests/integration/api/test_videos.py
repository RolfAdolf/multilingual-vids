import uuid

import pytest
from django.urls import reverse
from rest_framework import status

from tests.utils import assert_status, random_object_key
from video.models import Video, VideoStatus


@pytest.mark.django_db()
class TestVideosAPI:
    def test_upload_url(self, api_client, mock_s3):
        data = assert_status(
            api_client.post(
                reverse("video-upload-url"),
                {
                    "filename": "clip.mp4",
                    "content_type": "video/mp4",
                    "size_bytes": 2048,
                },
                format="json",
            ),
            status.HTTP_201_CREATED,
        )
        assert data["method"] == "PUT"
        assert data["object_key"].startswith("uploads/")

    def test_create_video_enqueues_task(
        self, api_client, mock_s3, mock_celery_send_task, seamless_pair
    ):
        video_id = uuid.uuid4()
        object_key = random_object_key(str(video_id))

        data = assert_status(
            api_client.post(
                reverse("video-list-create"),
                {
                    "object_key": object_key,
                    "source": "en",
                    "target": "de",
                    "original_filename": "clip.mp4",
                },
                format="json",
            ),
            status.HTTP_201_CREATED,
        )

        assert data["status"] == VideoStatus.WAITING
        assert data["model_slug"] == seamless_pair.model.slug
        mock_celery_send_task.assert_called_once()
        kwargs = mock_celery_send_task.call_args.kwargs["kwargs"]
        assert kwargs["model_slug"] == seamless_pair.model.slug
        assert Video.objects.filter(pk=data["id"]).exists()

    def test_create_video_idempotent(
        self, api_client, mock_s3, mock_celery_send_task, seamless_pair, video_factory
    ):
        existing = video_factory(
            model=seamless_pair.model,
            source_language_code="en",
            target_language_code="de",
            idempotency_key="key-abc",
        )
        mock_celery_send_task.reset_mock()

        data = assert_status(
            api_client.post(
                reverse("video-list-create"),
                {
                    "object_key": existing.input_object_key,
                    "source": "en",
                    "target": "de",
                },
                format="json",
                HTTP_IDEMPOTENCY_KEY="key-abc",
            ),
            status.HTTP_200_OK,
        )
        assert data["id"] == str(existing.id)
        mock_celery_send_task.assert_not_called()

    def test_list_videos(self, api_client, video_factory, seamless_pair):
        video_factory(model=seamless_pair.model, status=VideoStatus.SUCCESS)
        video_factory(model=seamless_pair.model, status=VideoStatus.WAITING)

        data = assert_status(
            api_client.get(reverse("video-list-create")),
            status.HTTP_200_OK,
        )
        assert len(data["items"]) == 2

    def test_list_videos_filter_by_status(self, api_client, video_factory, seamless_pair):
        video_factory(model=seamless_pair.model, status=VideoStatus.SUCCESS)
        video_factory(model=seamless_pair.model, status=VideoStatus.ERROR)

        data = assert_status(
            api_client.get(reverse("video-list-create"), {"status": "SUCCESS"}),
            status.HTTP_200_OK,
        )
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == VideoStatus.SUCCESS

    def test_video_detail(self, api_client, video_factory, seamless_pair):
        video = video_factory(model=seamless_pair.model)
        data = assert_status(
            api_client.get(reverse("video-detail", kwargs={"video_id": video.id})),
            status.HTTP_200_OK,
        )
        assert data["id"] == str(video.id)

    def test_download_not_ready(self, api_client, video_factory, seamless_pair):
        video = video_factory(model=seamless_pair.model, status=VideoStatus.PROCESSING)
        assert_status(
            api_client.get(reverse("video-download", kwargs={"video_id": video.id})),
            status.HTTP_409_CONFLICT,
        )

    def test_download_redirects_when_ready(
        self, api_client, mock_s3, video_factory, seamless_pair
    ):
        video = video_factory(
            model=seamless_pair.model,
            status=VideoStatus.SUCCESS,
        )
        video.output_object_key = f"tasks/{video.id}/translated.mp4"
        video.save(update_fields=["output_object_key"])
        response = api_client.get(
            reverse("video-download", kwargs={"video_id": video.id}),
        )
        assert response.status_code == 302
        assert "storage.example" in response["Location"]
