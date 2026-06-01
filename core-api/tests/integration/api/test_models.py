import pytest
from django.urls import reverse
from rest_framework import status

from translation_models.models import ModelSlug
from tests.utils import assert_status


@pytest.mark.django_db()
class TestModelsAPI:
    def test_list_requires_source_and_target(self, api_client):
        data = assert_status(
            api_client.get(reverse("models")),
            status.HTTP_400_BAD_REQUEST,
        )
        assert "source" in data["detail"].lower()

    def test_list_for_pair(self, api_client, seamless_pair):
        data = assert_status(
            api_client.get(reverse("models"), {"source": "en", "target": "de"}),
            status.HTTP_200_OK,
        )
        assert data["source"] == "en"
        assert data["target"] == "de"
        assert len(data["items"]) == 1
        assert data["items"][0]["slug"] == ModelSlug.SEAMLESS_M4T
        assert data["recommended_model_id"] == data["items"][0]["id"]

    def test_catalog(self, api_client, seamless_pair, translation_model_factory):
        translation_model_factory(slug=ModelSlug.ZEROSHOT, worker_queue="zeroshot")
        data = assert_status(
            api_client.get(reverse("models-catalog")),
            status.HTTP_200_OK,
        )
        slugs = {item["slug"] for item in data["items"]}
        assert ModelSlug.SEAMLESS_M4T in slugs

    def test_coverage(self, api_client, seamless_pair):
        data = assert_status(
            api_client.get(reverse("models-coverage")),
            status.HTTP_200_OK,
        )
        assert "languages" in data
        assert "items" in data
        row = next(i for i in data["items"] if i["slug"] == ModelSlug.SEAMLESS_M4T)
        assert row["coverage"]["de"]["supported"] is True
