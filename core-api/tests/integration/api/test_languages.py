import pytest
from django.urls import reverse
from rest_framework import status

from tests.utils import assert_status


@pytest.mark.django_db()
class TestLanguageListAPI:
    def test_lists_catalog_languages(self, api_client, language_factory):
        language_factory(api_code="en", name_en="English", name_ru="Английский")
        language_factory(
            api_code="de",
            name_en="German",
            supports_source_speech=False,
            supports_source_text=False,
        )

        data = assert_status(
            api_client.get(reverse("languages")),
            status.HTTP_200_OK,
        )
        codes = {item["code"] for item in data["items"]}
        assert "en" in codes
        assert "de" not in codes
        assert "sv-se" in codes
