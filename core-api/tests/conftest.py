from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from tests.factories import (
    LanguageFactory,
    ModelLanguageFactory,
    TranslationModelFactory,
    VideoFactory,
)

register(TranslationModelFactory)
register(ModelLanguageFactory)
register(LanguageFactory)
register(VideoFactory)


@pytest.fixture()
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def mock_s3(monkeypatch):
    """Avoid real Yandex S3 in API/service tests."""
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://storage.example/presigned"
    client.head_object.return_value = {
        "ContentLength": 1_024_000,
        "ContentType": "video/mp4",
    }

    monkeypatch.setattr("storage.s3.s3_client", lambda: client)
    monkeypatch.setattr(
        "storage.s3.presigned_put_url",
        lambda object_key, content_type, *, content_length: (
            f"https://storage.example/put/{object_key}"
        ),
    )
    monkeypatch.setattr(
        "storage.s3.presigned_get_url",
        lambda object_key: f"https://storage.example/get/{object_key}",
    )
    monkeypatch.setattr(
        "storage.s3.head_object",
        lambda object_key: {
            "ContentLength": 1_024_000,
            "ContentType": "video/mp4",
        },
    )
    return client


@pytest.fixture()
def mock_celery_send_task(monkeypatch):
    result = MagicMock()
    result.id = "celery-task-test-id"

    send_task = MagicMock(return_value=result)
    monkeypatch.setattr("config.celery.app.send_task", send_task)
    return send_task


@pytest.fixture()
def seamless_pair(model_language_factory):
    """Active en→de pair for SeamlessM4T."""
    from translation_models.models import ModelSlug

    model = TranslationModelFactory(slug=ModelSlug.SEAMLESS_M4T, worker_queue="seamless")
    return model_language_factory(
        model=model,
        source_language_code="en",
        target_language_code="de",
        source_model_lang_code="eng",
        target_model_lang_code="deu",
        bleu=35.5,
    )


@pytest.fixture()
def zeroshot_pair(model_language_factory):
    from translation_models.models import ModelSlug

    model = TranslationModelFactory(slug=ModelSlug.ZEROSHOT, worker_queue="zeroshot")
    return model_language_factory(
        model=model,
        source_language_code="de",
        target_language_code="uk",
        source_model_lang_code="de",
        target_model_lang_code="uk",
        bleu=None,
    )
