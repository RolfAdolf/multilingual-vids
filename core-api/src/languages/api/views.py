from rest_framework.response import Response
from rest_framework.views import APIView

from languages.api.serializers import LanguageItemSerializer
from languages.domain.services import LanguageCatalogService


class LanguageListView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = LanguageCatalogService()

    def get(self, request):
        items = [
            {"code": item.code, "name_en": item.name_en, "name_ru": item.name_ru}
            for item in self._service.list_available()
        ]
        serializer = LanguageItemSerializer(items, many=True)
        return Response({"items": serializer.data})
