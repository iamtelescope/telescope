from django.urls import include, path

from allauth.socialaccount.providers.github.urls import urlpatterns as github_patterns
from allauth.socialaccount.providers.openid_connect.urls import urlpatterns as openid_patterns
from django.views.generic import RedirectView
from telescope.urls import urlpatterns as telescope_patterns


urlpatterns = [
    path("editor.worker.js", RedirectView.as_view(url="/static/editor.worker.js")),
    path("login/", include(github_patterns)),
    path("", include(openid_patterns + telescope_patterns)),
]
