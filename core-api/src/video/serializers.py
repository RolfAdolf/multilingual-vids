from rest_framework import serializers

from video.models import Video


class UploadUrlRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=512)
    content_type = serializers.CharField(max_length=128)
    size_bytes = serializers.IntegerField(min_value=1)


class UploadUrlResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    object_key = serializers.CharField()
    expires_in = serializers.IntegerField()
    method = serializers.CharField(default="PUT")
    headers = serializers.DictField(child=serializers.CharField())


class VideoCreateSerializer(serializers.Serializer):
    object_key = serializers.CharField()
    source = serializers.CharField(max_length=8)
    target = serializers.CharField(max_length=8)
    model_id = serializers.UUIDField(required=False)
    original_filename = serializers.CharField(max_length=512, required=False)


class VideoResponseSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source_language_code", read_only=True)
    target = serializers.CharField(source="target_language_code", read_only=True)
    model_id = serializers.UUIDField(source="model.id", read_only=True)
    model_slug = serializers.CharField(source="model.slug", read_only=True)
    model_display_name = serializers.CharField(source="model.display_name", read_only=True)
    object_key = serializers.CharField(source="input_object_key", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            "id",
            "original_filename",
            "status",
            "progress",
            "source",
            "target",
            "model_id",
            "model_slug",
            "model_display_name",
            "object_key",
            "file_size_bytes",
            "download_url",
            "error_message",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        )

    def get_download_url(self, obj: Video) -> str | None:
        if obj.status != "SUCCESS":
            return None
        return f"/api/v1/videos/{obj.id}/download"
