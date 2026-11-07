from django.urls import path

from telescope_otel import releases

urlpatterns = [
    path("ui/v1/otel/<slug:slug>/releases", releases.ReleasesView.as_view()),
]
