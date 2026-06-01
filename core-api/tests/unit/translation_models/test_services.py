import pytest

from translation_models.domain.services import TranslationModelQueryService
from translation_models.models import ModelSlug


@pytest.mark.django_db()
class TestTranslationModelQueryService:
    def test_list_for_language_pair_orders_by_bleu_and_recommends_first(
        self, model_language_factory, translation_model_factory
    ):
        low = translation_model_factory(
            slug=ModelSlug.ZEROSHOT,
            display_name="Zeroshot",
            worker_queue="zeroshot",
        )
        high = translation_model_factory(
            slug=ModelSlug.SEAMLESS_M4T,
            display_name="Seamless",
            worker_queue="seamless",
        )
        model_language_factory(
            model=low,
            source_language_code="en",
            target_language_code="de",
            bleu=10.0,
        )
        model_language_factory(
            model=high,
            source_language_code="en",
            target_language_code="de",
            bleu=40.0,
        )

        result = TranslationModelQueryService().list_for_language_pair("en", "de")

        assert result.source == "en"
        assert result.target == "de"
        assert len(result.items) == 2
        assert result.recommended_model_id == result.items[0].id
        assert result.items[0].slug == ModelSlug.SEAMLESS_M4T
        assert result.items[0].is_recommended is True
        assert result.items[1].is_recommended is False
        assert result.items[0].metrics is not None
        assert result.items[0].metrics.bleu == 40.0

    def test_list_for_language_pair_empty(self):
        result = TranslationModelQueryService().list_for_language_pair("en", "ja")
        assert result.items == []
        assert result.recommended_model_id is None

    def test_coverage_matrix_marks_supported_targets(
        self, model_language_factory, translation_model_factory
    ):
        model = translation_model_factory(slug=ModelSlug.SEAMLESS_M4T)
        model_language_factory(
            model=model,
            source_language_code="en",
            target_language_code="de",
            target_name_en="German",
            bleu=42.0,
        )
        model_language_factory(
            model=model,
            source_language_code="en",
            target_language_code="fr",
            target_name_en="French",
            bleu=15.0,
        )

        result = TranslationModelQueryService().coverage_matrix()
        codes = {lang["code"] for lang in result.languages}
        assert "de" in codes
        assert "fr" in codes

        row = next(item for item in result.items if item["slug"] == ModelSlug.SEAMLESS_M4T)
        assert row["coverage"]["de"].supported is True
        assert row["coverage"]["de"].quality == "high"
        assert row["coverage"]["fr"].quality == "low"

    def test_list_catalog_includes_language_pairs(
        self, seamless_pair, translation_model_factory
    ):
        translation_model_factory(slug=ModelSlug.ZEROSHOT, worker_queue="zeroshot")

        catalog = TranslationModelQueryService().list_catalog()
        slugs = {item.slug for item in catalog}
        assert ModelSlug.SEAMLESS_M4T in slugs
        assert ModelSlug.ZEROSHOT in slugs

        seamless = next(i for i in catalog if i.slug == ModelSlug.SEAMLESS_M4T)
        assert any(p["target"] == "de" for p in seamless.language_pairs)
