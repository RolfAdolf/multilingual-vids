import pytest
from django.urls import reverse


@pytest.mark.django_db()
def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db()
def test_ready(api_client):
    response = api_client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
