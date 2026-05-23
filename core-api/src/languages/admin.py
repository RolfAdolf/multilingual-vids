from django.contrib import admin

from languages.models import Language


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = (
        "api_code",
        "code",
        "name_en",
        "supports_source_speech",
        "supports_source_text",
        "supports_target_speech",
        "supports_target_text",
    )
    list_filter = (
        "supports_source_speech",
        "supports_target_speech",
        "script",
    )
    search_fields = ("api_code", "code", "name_en")
