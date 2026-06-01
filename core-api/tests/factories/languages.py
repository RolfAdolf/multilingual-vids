import factory

from languages.models import Language


class LanguageFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: f"lang_{n:04d}")
    api_code = factory.Sequence(lambda n: f"lg{n}")
    name_en = factory.Faker("language_name")
    name_ru = factory.LazyAttribute(lambda o: o.name_en)
    script = "Latn"
    supports_source_speech = True
    supports_source_text = True
    supports_target_speech = True
    supports_target_text = True

    class Meta:
        model = Language
