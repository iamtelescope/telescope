from django.urls import path

from telescope.views.source.facets import SourceFacetsView

urlpatterns = [
    path("ui/v1/sources/<slug:slug>/facets", SourceFacetsView.as_view()),
]
