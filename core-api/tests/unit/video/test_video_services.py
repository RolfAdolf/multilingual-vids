import uuid

import pytest
from botocore.exceptions import ClientError

from translation_models.models import ModelSlug
from tests.factories.translation_models import TranslationModelFactory
from tests.utils import random_object_key
from video.services import VideoServiceError, create_upload_url, create_video_job


@pytest.mark.django_db()
class TestCreateUploadUrl:
    def test_success(self, mock_s3):
        payload = create_upload_url("demo.mp4", "video/mp4", 1024)
        assert payload["method"] == "PUT"
        assert payload["object_key"].startswith("uploads/")
        assert payload["object_key"].endswith("/source.mp4")
        assert "upload_url" in payload
        assert payload["expires_in"] > 0

    def test_rejects_unsupported_content_type(self, settings):
        settings.ALLOWED_VIDEO_CONTENT_TYPES = ("video/webm",)
        with pytest.raises(VideoServiceError) as exc:
            create_upload_url("demo.mp4", "video/mp4", 100)
        assert exc.value.status_code == 415

    def test_rejects_oversized_file(self, settings):
        settings.MAX_UPLOAD_BYTES = 100
        with pytest.raises(VideoServiceError) as exc:
            create_upload_url("big.mp4", "video/mp4", 10_000)
        assert exc.value.status_code == 413


@pytest.mark.django_db()
class TestCreateVideoJob:
    def test_creates_video_and_resolves_best_model(
        self, mock_s3, seamless_pair, model_language_factory
    ):
        worse = TranslationModelFactory(slug=ModelSlug.ZEROSHOT, worker_queue="zeroshot")
        model_language_factory(
            model=worse,
            source_language_code="en",
            target_language_code="de",
            bleu=5.0,
        )

        video_id = uuid.uuid4()
        object_key = random_object_key(str(video_id))
        video, created = create_video_job(
            object_key=object_key,
            source="en",
            target="de",
            model_id=None,
            original_filename="clip.mp4",
            content_type="video/mp4",
            file_size_bytes=1_024_000,
            idempotency_key=None,
        )

        assert created is True
        assert video.model.slug == ModelSlug.SEAMLESS_M4T
        assert video.source_language_code == "en"
        assert video.target_language_code == "de"

    def test_idempotency_returns_existing(self, mock_s3, seamless_pair, video_factory):
        existing = video_factory(idempotency_key="idem-1")
        video, created = create_video_job(
            object_key=existing.input_object_key,
            source="en",
            target="de",
            model_id=None,
            original_filename="clip.mp4",
            content_type=None,
            file_size_bytes=None,
            idempotency_key="idem-1",
        )
        assert created is False
        assert video.id == existing.id

    def test_unknown_language_pair(self, mock_s3):
        with pytest.raises(VideoServiceError) as exc:
            create_video_job(
                object_key="uploads/x/source.mp4",
                source="en",
                target="xx",
                model_id=None,
                original_filename="clip.mp4",
                content_type=None,
                file_size_bytes=None,
                idempotency_key=None,
            )
        assert exc.value.status_code == 400

    def test_missing_object_in_storage(self, mock_s3, seamless_pair, monkeypatch):
        def _missing(_object_key):
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadObject",
            )

        monkeypatch.setattr("storage.s3.head_object", _missing)
        with pytest.raises(VideoServiceError) as exc:
            create_video_job(
                object_key="uploads/missing/source.mp4",
                source="en",
                target="de",
                model_id=None,
                original_filename="clip.mp4",
                content_type=None,
                file_size_bytes=None,
                idempotency_key=None,
            )
        assert exc.value.status_code == 400
        assert "not found" in exc.value.message.lower()
