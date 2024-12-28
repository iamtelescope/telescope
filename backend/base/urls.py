from django.urls import include, path

from allauth.socialaccount.providers.github.urls import urlpatterns as github_patterns


urlpatterns = [
    path("login/", include(github_patterns)),
    path("", include("telescope.urls")),
]
