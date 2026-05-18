from django.urls import path

from translation_models.api.views import ModelListView

urlpatterns = [
    path("models", ModelListView.as_view(), name="models"),
]
