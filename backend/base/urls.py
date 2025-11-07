from django.urls import include, path

from django.views.generic import RedirectView
from django.conf import settings

oauth_patterns = []

if settings.CONFIG["auth"]["providers"]["github"]["enabled"]:
    from allauth.socialaccount.providers.github.urls import (
        urlpatterns as github_patterns,
    )

    oauth_patterns.extend(github_patterns)

if settings.CONFIG["auth"]["providers"]["okta"]["enabled"]:
    from allauth.socialaccount.providers.okta.urls import urlpatterns as okta_patterns

    oauth_patterns.extend(okta_patterns)

urlpatterns = [
    path(
        "editor.worker.js",
        RedirectView.as_view(url=f"{settings.BASE_URL}/static/editor.worker.js"),
    ),
    path("login/", include(oauth_patterns)),
    path("", include("telescope.urls")),
]
