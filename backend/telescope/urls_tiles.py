from django.urls import path

from telescope.views.source.tiles import SourcePatternsTileView, SourceSearchTileView

urlpatterns = [
    path("ui/v1/sources/<slug:slug>/searchTile", SourceSearchTileView.as_view()),
    path("ui/v1/sources/<slug:slug>/patternsTile", SourcePatternsTileView.as_view()),
]
