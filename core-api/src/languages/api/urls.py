from django.urls import path

from languages.api.views import LanguageListView

urlpatterns = [
    path("languages", LanguageListView.as_view(), name="languages"),
]
