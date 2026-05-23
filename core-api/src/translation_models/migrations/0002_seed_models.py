from django.db import migrations


def seed(apps, schema_editor):
    TranslationModel = apps.get_model("translation_models", "TranslationModel")

    models_data = [
        {
            "slug": "seamless_m4t",
            "display_name": "SeamlessM4T Medium",
            "worker_queue": "seamless",
            "description": (
                "End-to-end speech translation via Meta SeamlessM4T. "
                "Strong fluency on multilingual pairs with a single unified model."
            ),
            "config": {
                "provider": "Meta AI",
                "tags": ["Recommended", "High Quality"],
                "pipeline_summary": "Audio in → SeamlessM4T → translated audio out",
                "hf_model_id": "facebook/hf-seamless-m4t-medium",
                "sample_rate_hz": 16000,
            },
        },
        {
            "slug": "zeroswot",
            "display_name": "ZeroSwot Medium (en→200)",
            "worker_queue": "zeroswot",
            "description": (
                "Zero-shot speech translation with ZeroSwot encoder and NLLB-200 decoder. "
                "Good balance of quality and throughput for many language pairs."
            ),
            "config": {
                "provider": "Research",
                "tags": ["High Quality", "Balanced"],
                "pipeline_summary": "Audio → ZeroSwot ASR/encoder → NLLB MT → audio",
                "encoder_hf_id": "johntsi/ZeroSwot-Medium_asr-mustc_en-to-200",
                "nllb_hf_id": "facebook/nllb-200-distilled-600M",
            },
        },
        {
            "slug": "zeroshot",
            "display_name": "STT + Zero-shot MT + TTS",
            "worker_queue": "zeroshot",
            "description": (
                "Modular pipeline: Whisper STT, bachelor zero-shot Transformer MT "
                "(tags <2ru>, <2en>, <2uk>), and neural TTS. "
                "Pairs: de→ru, de→en, de→uk, en→uk."
            ),
            "config": {
                "provider": "Thesis (SPbSU)",
                "tags": ["Balanced", "Custom MT"],
                "pipeline_summary": "Whisper STT → SavedModel MT → Edge TTS",
                "whisper_model": "large-v3",
                "mt_translator_path": "trained_models/augmented/translator_8",
                "tts_voice": "uk-UA-OstapNeural",
            },
        },
    ]

    for item in models_data:
        TranslationModel.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "display_name": item["display_name"],
                "worker_queue": item["worker_queue"],
                "description": item["description"],
                "config": item["config"],
                "is_active": True,
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
