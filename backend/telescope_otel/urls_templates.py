from django.urls import path

from telescope_otel import template_views

urlpatterns = [
    path("ui/v1/dashboard-templates", template_views.TemplateListView.as_view()),
    path(
        "ui/v1/dashboard-templates/<slug:slug>",
        template_views.TemplateInstantiateView.as_view(),
    ),
]
