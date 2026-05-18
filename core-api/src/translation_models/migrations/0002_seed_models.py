from django.db import migrations


def seed(apps, schema_editor):
    TranslationModel = apps.get_model("translation_models", "TranslationModel")
    ModelLanguage = apps.get_model("translation_models", "ModelLanguage")

    models_data = [
        {
            "slug": "seamless_m4t",
            "display_name": "SeamlessM4T Medium",
            "worker_queue": "seamless",
            "config": {
                "hf_model_id": "facebook/hf-seamless-m4t-medium",
                "sample_rate_hz": 16000,
            },
        },
        {
            "slug": "zeroswot",
            "display_name": "ZeroSwot Medium (en→200)",
            "worker_queue": "zeroswot",
            "config": {
                "encoder_hf_id": "johntsi/ZeroSwot-Medium_asr-mustc_en-to-200",
                "nllb_hf_id": "facebook/nllb-200-distilled-600M",
            },
        },
        {
            "slug": "zeroshot",
            "display_name": "STT + Zero-shot MT + TTS",
            "worker_queue": "zeroshot",
            "config": {
                "whisper_model": "large-v3",
                "mt_translator_path": "trained_models/augmented/translator_8",
                "tts_voice": "uk-UA-OstapNeural",
            },
        },
    ]

    for item in models_data:
        model, _ = TranslationModel.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "display_name": item["display_name"],
                "worker_queue": item["worker_queue"],
                "config": item["config"],
                "is_active": True,
            },
        )
        ModelLanguage.objects.update_or_create(
            model=model,
            source_language_code="de",
            target_language_code="uk",
            defaults={
                "source_model_lang_code": "deu",
                "target_model_lang_code": "ukr",
                "source_name_en": "German",
                "source_name_ru": "Немецкий",
                "target_name_en": "Ukrainian",
                "target_name_ru": "Украинский",
                "bleu": None,
                "nist": None,
                "dataset_name": "opus_opensubtitles",
            },
        )


def unseed(apps, schema_editor):
    TranslationModel = apps.get_model("translation_models", "TranslationModel")
    TranslationModel.objects.filter(
        slug__in=["seamless_m4t", "zeroswot", "zeroshot"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("translation_models", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
