from django.urls import path

from translation_models.api.views import ModelCatalogView, ModelCoverageView, ModelListView

urlpatterns = [
    path("models/coverage", ModelCoverageView.as_view(), name="models-coverage"),
    path("models/catalog", ModelCatalogView.as_view(), name="models-catalog"),
    path("models", ModelListView.as_view(), name="models"),
]
