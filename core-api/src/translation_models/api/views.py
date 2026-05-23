import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from config.json_log import log_event
from translation_models.api.serializers import ModelListItemSerializer
from translation_models.domain.services import TranslationModelQueryService

logger = logging.getLogger(__name__)


def _request_id(request) -> str | None:
    return getattr(request, "request_id", None)


def _serialize_list_item(item) -> dict:
    return {
        "id": item.id,
        "slug": item.slug,
        "display_name": item.display_name,
        "description": item.description,
        "provider": item.provider,
        "pipeline_summary": item.pipeline_summary,
        "tags": list(item.tags),
        "is_recommended": item.is_recommended,
        "metrics": (
            {
                "bleu": item.metrics.bleu,
                "dataset_name": item.metrics.dataset_name,
                "measured_at": item.metrics.measured_at,
            }
            if item.metrics
            else None
        ),
    }


class ModelListView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TranslationModelQueryService()

    def get(self, request):
        source = request.query_params.get("source", "").lower()
        target = request.query_params.get("target", "").lower()
        if not source or not target:
            log_event(
                logger,
                logging.WARNING,
                "translation_models.api.list.bad_request",
                layer="handler",
                request_id=_request_id(request),
            )
            return Response({"detail": "Query params 'source' and 'target' are required."}, status=400)
        log_event(
            logger,
            logging.INFO,
            "translation_models.api.list.request",
            layer="handler",
            request_id=_request_id(request),
            source=source,
            target=target,
        )

        result = self._service.list_for_language_pair(source, target)
        payload = [_serialize_list_item(item) for item in result.items]
        serializer = ModelListItemSerializer(payload, many=True)
        return Response(
            {
                "source": result.source,
                "target": result.target,
                "recommended_model_id": result.recommended_model_id,
                "items": serializer.data,
            }
        )


class ModelCatalogView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TranslationModelQueryService()

    def get(self, request):
        items = self._service.list_catalog()
        return Response(
            {
                "items": [
                    {
                        "id": item.id,
                        "slug": item.slug,
                        "display_name": item.display_name,
                        "description": item.description,
                        "provider": item.provider,
                        "pipeline_summary": item.pipeline_summary,
                        "tags": list(item.tags),
                        "worker_queue": item.worker_queue,
                        "language_pairs": list(item.language_pairs),
                    }
                    for item in items
                ]
            }
        )


class ModelCoverageView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = TranslationModelQueryService()

    def get(self, request):
        result = self._service.coverage_matrix()
        items = []
        for row in result.items:
            coverage = {
                code: {
                    "supported": cell.supported,
                    "bleu": cell.bleu,
                    "quality": cell.quality,
                }
                for code, cell in row["coverage"].items()
            }
            items.append(
                {
                    "id": row["id"],
                    "slug": row["slug"],
                    "display_name": row["display_name"],
                    "coverage": coverage,
                }
            )
        return Response({"languages": list(result.languages), "items": items})
