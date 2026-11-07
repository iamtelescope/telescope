from django.urls import path

from telescope.views.source.patterns import SourcePatternsView

urlpatterns = [
    path("ui/v1/sources/<slug:slug>/patterns", SourcePatternsView.as_view()),
]
