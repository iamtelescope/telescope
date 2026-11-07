from django.urls import path

from telescope_api2 import views

urlpatterns = [
    path("api/v1/openapi.json", views.OpenAPIView.as_view()),
    path("api/v1/dashboards", views.DashboardView.as_view()),
    path("api/v1/dashboards/<slug:slug>", views.DashboardView.as_view()),
    path("api/v1/alerts", views.AlertView.as_view()),
    path("api/v1/alerts/<int:pk>", views.AlertView.as_view()),
    path("api/v1/saved-views", views.SavedViewView.as_view()),
    path(
        "api/v1/saved-views/<slug:source>/<slug:view_slug>",
        views.SavedViewView.as_view(),
    ),
    path("api/v1/sources/<slug:slug>/search", views.SearchView.as_view()),
    path("api/v1/sources/<slug:slug>/chart", views.ChartView.as_view()),
]
