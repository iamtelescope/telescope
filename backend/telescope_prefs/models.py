"""Per-user preferences synced across browsers, kept out of the core telescope migrations."""

from django.contrib.auth.models import User
from django.db import models

from telescope.models import Dashboard, Source


class PinnedFacets(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="+")
    facets = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source"], name="telescope_prefs_pinned_unique"
            )
        ]


class DashboardFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dashboard"], name="telescope_prefs_favorite_unique"
            )
        ]
