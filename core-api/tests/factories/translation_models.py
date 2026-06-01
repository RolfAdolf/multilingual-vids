import factory
from factory import fuzzy

from translation_models.models import ModelLanguage, ModelSlug, TranslationModel


class TranslationModelFactory(factory.django.DjangoModelFactory):
    slug = ModelSlug.SEAMLESS_M4T
    display_name = factory.Sequence(lambda n: f"Test Model {n}")
    description = "Test translation model"
    worker_queue = factory.LazyAttribute(
        lambda o: {
            ModelSlug.SEAMLESS_M4T: "seamless",
            ModelSlug.ZEROSWOT: "zeroswot",
            ModelSlug.ZEROSHOT: "zeroshot",
        }.get(o.slug, "seamless")
    )
    is_active = True
    config = factory.LazyFunction(
        lambda: {
            "provider": "Test",
            "tags": ["Test"],
            "pipeline_summary": "Test pipeline",
        }
    )

    class Meta:
        model = TranslationModel
        django_get_or_create = ("slug",)


class ModelLanguageFactory(factory.django.DjangoModelFactory):
    model = factory.SubFactory(TranslationModelFactory)
    source_language_code = "en"
    target_language_code = "de"
    source_model_lang_code = "eng"
    target_model_lang_code = "deu"
    source_name_en = "English"
    target_name_en = "German"
    bleu = fuzzy.FuzzyFloat(20.0, 45.0)
    dataset_name = "test"

    class Meta:
        model = ModelLanguage
