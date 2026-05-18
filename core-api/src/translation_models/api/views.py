from rest_framework.response import Response
from rest_framework.views import APIView

from translation_models.api.serializers import ModelListItemSerializer
from translation_models.domain.services import TranslationModelQueryService


class ModelListView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TranslationModelQueryService()

    def get(self, request):
        source = request.query_params.get("source", "")
        target = request.query_params.get("target", "")
        if not source or not target:
            return Response(
                {"detail": "Query params 'source' and 'target' are required."},
                status=400,
            )

        result = self._service.list_for_language_pair(source, target)
        payload = [
            {
                "id": item.id,
                "slug": item.slug,
                "display_name": item.display_name,
                "is_recommended": item.is_recommended,
                "metrics": (
                    {
                        "bleu": item.metrics.bleu,
                        "nist": item.metrics.nist,
                        "dataset_name": item.metrics.dataset_name,
                        "measured_at": item.metrics.measured_at,
                    }
                    if item.metrics
                    else None
                ),
            }
            for item in result.items
        ]
        serializer = ModelListItemSerializer(payload, many=True)
        return Response(
            {
                "source": result.source,
                "target": result.target,
                "recommended_model_id": result.recommended_model_id,
                "items": serializer.data,
            }
        )
