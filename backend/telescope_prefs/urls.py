from django.urls import path

from telescope_prefs import views

urlpatterns = [
    path("ui/v1/prefs/pinned-facets/<slug:slug>", views.PinnedFacetsView.as_view()),
    path("ui/v1/prefs/favorites/dashboards", views.FavoriteDashboardsView.as_view()),
    path(
        "ui/v1/prefs/favorites/dashboards/<slug:slug>",
        views.FavoriteDashboardView.as_view(),
    ),
]
