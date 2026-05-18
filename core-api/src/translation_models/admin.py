from django.contrib import admin

from translation_models.models import ModelLanguage, TranslationModel


class ModelLanguageInline(admin.TabularInline):
    model = ModelLanguage
    extra = 1


@admin.register(TranslationModel)
class TranslationModelAdmin(admin.ModelAdmin):
    list_display = ("display_name", "slug", "worker_queue", "is_active")
    list_filter = ("is_active",)
    inlines = [ModelLanguageInline]


@admin.register(ModelLanguage)
class ModelLanguageAdmin(admin.ModelAdmin):
    list_display = (
        "model",
        "source_language_code",
        "target_language_code",
        "bleu",
        "nist",
        "dataset_name",
    )
    list_filter = ("model", "source_language_code", "target_language_code")
