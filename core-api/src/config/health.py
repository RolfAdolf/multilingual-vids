from django.db import connection
from django.http import JsonResponse


def health(_request):
    return JsonResponse({"status": "ok", "service": "core-api"})


def ready(_request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ready", "service": "core-api"})
    except Exception as exc:
        return JsonResponse(
            {"status": "not_ready", "service": "core-api", "detail": str(exc)},
            status=503,
        )
