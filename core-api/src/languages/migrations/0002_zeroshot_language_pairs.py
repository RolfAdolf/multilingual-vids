from django.db import migrations


# (source_api, target_api, source_name, target_name, whisper_src, mt_tgt_tag)
ZEROSHOT_PAIRS = (
    ("de", "ru", "German", "Russian", "de", "ru"),
    ("de", "en", "German", "English", "de", "en"),
    ("de", "uk", "German", "Ukrainian", "de", "uk"),
    ("en", "uk", "English", "Ukrainian", "en", "uk"),
)


def seed(apps, schema_editor):
    TranslationModel = apps.get_model("translation_models", "TranslationModel")
    ModelLanguage = apps.get_model("translation_models", "ModelLanguage")

    try:
        model = TranslationModel.objects.get(slug="zeroshot")
    except TranslationModel.DoesNotExist:
        return

    ModelLanguage.objects.filter(model=model).delete()

    pairs = [
        ModelLanguage(
            model=model,
            source_language_code=src_api,
            target_language_code=tgt_api,
            source_model_lang_code=whisper,
            target_model_lang_code=mt_tag,
            source_name_en=src_name,
            target_name_en=tgt_name,
            dataset_name="thesis_zeroshot_mt",
            notes=f"MT tag <2{mt_tag}>",
        )
        for src_api, tgt_api, src_name, tgt_name, whisper, mt_tag in ZEROSHOT_PAIRS
    ]
    ModelLanguage.objects.bulk_create(pairs)

    ModelLanguage.objects.filter(
        model=model,
        source_language_code="en",
        target_language_code="uk",
    ).update(bleu=39.2)


def unseed(apps, schema_editor):
    ModelLanguage = apps.get_model("translation_models", "ModelLanguage")
    ModelLanguage.objects.filter(model__slug="zeroshot").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("languages", "0001_initial"),
        ("translation_models", "0002_seed_models"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
