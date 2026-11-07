from django.urls import path

from telescope_otel import trace_views

urlpatterns = [
    path("ui/v1/otel/<slug:slug>/trace", trace_views.TraceView.as_view()),
    path("ui/v1/otel/<slug:slug>/traceLogs", trace_views.TraceLogsView.as_view()),
]
