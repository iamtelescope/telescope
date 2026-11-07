from django.urls import path

from telescope_alerts import views

urlpatterns = [
    path("ui/v1/alerts", views.AlertView.as_view()),
    path("ui/v1/alerts/preview", views.AlertPreviewView.as_view()),
    path("ui/v1/alerts/<int:pk>", views.AlertView.as_view()),
    path("ui/v1/alerts/markers", views.AlertMarkersView.as_view()),
    path("ui/v1/alerts/saved-views/<slug:slug>", views.SavedViewMetaView.as_view()),
    path(
        "ui/v1/alerts/saved-views/<slug:slug>/<int:view_id>",
        views.SavedViewMetaView.as_view(),
    ),
    path("ui/v1/alerts/<int:pk>/history", views.AlertHistoryView.as_view()),
    path("ui/v1/alerts/<int:pk>/evaluations", views.AlertEvaluationsView.as_view()),
    path("ui/v1/alerts/<int:pk>/silenced", views.AlertSilenceView.as_view()),
    path("ui/v1/alerts/<int:pk>/enabled", views.AlertEnabledView.as_view()),
    path("ui/v1/alerts/<int:pk>/test", views.AlertTestView.as_view()),
    path("ui/v1/alert-channels", views.ChannelView.as_view()),
    path("ui/v1/alert-channels/<int:pk>", views.ChannelView.as_view()),
    path("ui/v1/alert-channels/<int:pk>/test", views.ChannelTestView.as_view()),
]
