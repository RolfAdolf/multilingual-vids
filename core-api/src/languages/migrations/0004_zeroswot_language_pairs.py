from django.db import migrations


# (api_code, name_en, script, nllb_code)
ZEROSWOT_LANGUAGES = (
    ("en", "English", "Latn", "eng_Latn"),
    ("ar", "Arabic", "Arab", "arb_Arab"),
    ("ca", "Catalan", "Latn", "cat_Latn"),
    ("cy", "Welsh", "Latn", "cym_Latn"),
    ("de", "German", "Latn", "deu_Latn"),
    ("et", "Estonian", "Latn", "est_Latn"),
    ("fa", "Western Persian", "Arab", "pes_Arab"),
    ("id", "Indonesian", "Latn", "ind_Latn"),
    ("ja", "Japanese", "Jpan", "jpn_Jpan"),
    ("lv", "Standard Latvian", "Latn", "lvs_Latn"),
    ("mn", "Halh Mongolian", "Cyrl", "khk_Cyrl"),
    ("sl", "Slovenian", "Latn", "slv_Latn"),
    ("sv-se", "Swedish", "Latn", "swe_Latn"),
    ("ta", "Tamil", "Taml", "tam_Taml"),
    ("tr", "Turkish", "Latn", "tur_Latn"),
    ("zh-cn", "Chinese (Simplified)", "Hans", "zho_Hans"),
)


ZEROSWOT_COVOST2_BLEU = (
    ("ar", 25.7),
    ("ca", 40.0),
    ("cy", 29.0),
    ("de", 32.8),
    ("et", 27.2),
    ("fa", 26.6),
    ("id", 37.1),
    ("ja", 47.1),
    ("lv", 25.7),
    ("mn", 18.9),
    ("sl", 33.2),
    ("sv-se", 39.3),
    ("ta", 25.3),
    ("tr", 19.8),
    ("zh-cn", 40.5),
)


def seed(apps, schema_editor):
    Language = apps.get_model("languages", "Language")
    TranslationModel = apps.get_model("translation_models", "TranslationModel")
    ModelLanguage = apps.get_model("translation_models", "ModelLanguage")

    extras = (
        ("sv_se", "sv-se", "Swedish", "Latn"),
        ("zho_cn", "zh-cn", "Chinese (Simplified)", "Hans"),
    )
    for code, api_code, name, script in extras:
        Language.objects.update_or_create(
            code=code,
            defaults={
                "api_code": api_code,
                "name_en": name,
                "script": script,
                "supports_source_speech": True,
                "supports_source_text": True,
                "supports_target_speech": True,
                "supports_target_text": True,
            },
        )

    try:
        model = TranslationModel.objects.get(slug="zeroswot")
    except TranslationModel.DoesNotExist:
        return

    ModelLanguage.objects.filter(model=model).delete()

    by_api = {api: (name, nllb) for api, name, _script, nllb in ZEROSWOT_LANGUAGES}
    apis = list(by_api.keys())

    pairs = []
    for src_api in apis:
        for tgt_api in apis:
            if src_api == tgt_api:
                continue
            src_name, src_nllb = by_api[src_api]
            tgt_name, tgt_nllb = by_api[tgt_api]
            pairs.append(
                ModelLanguage(
                    model=model,
                    source_language_code=src_api,
                    target_language_code=tgt_api,
                    source_model_lang_code=src_nllb,
                    target_model_lang_code=tgt_nllb,
                    source_name_en=src_name,
                    target_name_en=tgt_name,
                    dataset_name="covost2",
                )
            )

    ModelLanguage.objects.bulk_create(pairs, batch_size=500)

    for tgt_api, bleu in ZEROSWOT_COVOST2_BLEU:
        ModelLanguage.objects.filter(
            model=model,
            source_language_code="en",
            target_language_code=tgt_api,
        ).update(bleu=bleu, dataset_name="covost2_bleu")


def unseed(apps, schema_editor):
    ModelLanguage = apps.get_model("translation_models", "ModelLanguage")
    Language = apps.get_model("languages", "Language")
    ModelLanguage.objects.filter(model__slug="zeroswot").delete()
    Language.objects.filter(code__in=("sv_se", "zho_cn")).delete()


class Migration(migrations.Migration):
    dependencies = [("languages", "0003_seamless_languages")]

    operations = [migrations.RunPython(seed, unseed)]
