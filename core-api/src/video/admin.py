from django.contrib import admin

from video.models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "progress",
        "model",
        "source_language_code",
        "target_language_code",
        "created_at",
    )
    list_filter = ("status", "model")
    readonly_fields = ("created_at", "updated_at", "started_at", "finished_at")
