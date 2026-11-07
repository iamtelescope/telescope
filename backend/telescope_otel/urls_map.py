from django.urls import path

from telescope_otel import service_map_views

urlpatterns = [
    path(
        "ui/v1/otel/<slug:slug>/serviceMap",
        service_map_views.ServiceMapView.as_view(),
    ),
]
