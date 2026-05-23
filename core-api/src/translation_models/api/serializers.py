from rest_framework import serializers

from translation_models.models import TranslationModel


class ModelMetricsSerializer(serializers.Serializer):
    bleu = serializers.FloatField(allow_null=True)
    dataset_name = serializers.CharField(allow_null=True)
    measured_at = serializers.DateTimeField(allow_null=True)


class ModelListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    provider = serializers.CharField()
    pipeline_summary = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())
    is_recommended = serializers.BooleanField()
    metrics = ModelMetricsSerializer(allow_null=True)


class ModelCatalogItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    provider = serializers.CharField()
    pipeline_summary = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())
    worker_queue = serializers.CharField()
    language_pairs = serializers.ListField(child=serializers.DictField())


class CoverageCellSerializer(serializers.Serializer):
    supported = serializers.BooleanField()
    bleu = serializers.FloatField(allow_null=True)
    quality = serializers.CharField()
