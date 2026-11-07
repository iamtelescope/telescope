from django.urls import path

from telescope_otel import metrics_views, views

urlpatterns = [
    path("ui/v1/otel/detect", views.DetectView.as_view()),
    path(
        "ui/v1/otel/<slug:slug>/metrics/names", metrics_views.MetricNamesView.as_view()
    ),
    path(
        "ui/v1/otel/<slug:slug>/metrics/attributes",
        metrics_views.MetricAttributesView.as_view(),
    ),
]
