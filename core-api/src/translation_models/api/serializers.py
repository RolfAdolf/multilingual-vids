from rest_framework import serializers

from translation_models.models import TranslationModel


class ModelMetricsSerializer(serializers.Serializer):
    bleu = serializers.FloatField(allow_null=True)
    nist = serializers.FloatField(allow_null=True)
    dataset_name = serializers.CharField(allow_null=True)
    measured_at = serializers.DateTimeField(allow_null=True)


class ModelListItemSerializer(serializers.ModelSerializer):
    is_recommended = serializers.BooleanField(read_only=True)
    metrics = ModelMetricsSerializer(allow_null=True)

    class Meta:
        model = TranslationModel
        fields = (
            "id",
            "slug",
            "display_name",
            "is_recommended",
            "metrics",
        )
