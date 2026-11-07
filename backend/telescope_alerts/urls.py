from django.urls import path

from telescope_alerts import views

urlpatterns = [
    path("ui/v1/alerts", views.AlertView.as_view()),
    path("ui/v1/alerts/preview", views.AlertPreviewView.as_view()),
    path("ui/v1/alerts/<int:pk>", views.AlertView.as_view()),
    path("ui/v1/alerts/<int:pk>/history", views.AlertHistoryView.as_view()),
    path("ui/v1/alert-channels", views.ChannelView.as_view()),
    path("ui/v1/alert-channels/<int:pk>", views.ChannelView.as_view()),
    path("ui/v1/alert-channels/<int:pk>/test", views.ChannelTestView.as_view()),
]
