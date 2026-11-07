from django.urls import path

from telescope_otel import views

urlpatterns = [
    path("ui/v1/otel/detect", views.DetectView.as_view()),
]
