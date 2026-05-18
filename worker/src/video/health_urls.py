from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health(_request):
    return JsonResponse({"status": "ok", "service": "worker"})


def ready(_request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ready", "service": "worker"})
    except Exception as exc:
        return JsonResponse(
            {"status": "not_ready", "service": "worker", "detail": str(exc)},
            status=503,
        )


urlpatterns = [
    path("health", health),
    path("ready", ready),
]
