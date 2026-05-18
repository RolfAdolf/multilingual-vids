from rest_framework import serializers


class LanguageItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    name_en = serializers.CharField(allow_blank=True)
    name_ru = serializers.CharField(allow_blank=True)
