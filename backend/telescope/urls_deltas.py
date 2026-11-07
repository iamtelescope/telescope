from django.urls import path

from telescope.views.source.deltas import SourceDeltasView, SourceHeatmapView

urlpatterns = [
    path("ui/v1/sources/<slug:slug>/heatmap", SourceHeatmapView.as_view()),
    path("ui/v1/sources/<slug:slug>/deltas", SourceDeltasView.as_view()),
]
