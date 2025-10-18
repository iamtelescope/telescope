from django.urls import include, path

from allauth.socialaccount.providers.github.urls import urlpatterns as github_patterns
from django.views.generic import RedirectView
from django.conf import settings

urlpatterns = [
    path("editor.worker.js", RedirectView.as_view(url=f"{settings.BASE_URL}/static/editor.worker.js")),
    path("login/", include(github_patterns)),
    path("", include("telescope.urls")),
]
