from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from telescope.models import Dashboard
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.services.dashboard import DashboardService
from telescope.services.exceptions import SerializerValidationError

from telescope_prefs.models import DashboardFavorite, PinnedFacets

MAX_PINNED = 100
rbac_manager = RBACManager()


class PinnedFacetsSerializer(serializers.Serializer):
    facets = serializers.ListField(
        child=serializers.CharField(max_length=512), max_length=MAX_PINNED
    )


def _source(user: User, slug: str):
    return rbac_manager.get_source(
        user, slug, required_permissions=[permissions.Source.READ.value]
    )


def get_pinned(user: User, slug: str):
    """Returns the stored facet ids, or None when the user never saved any for the source."""
    source = _source(user, slug)
    row = PinnedFacets.objects.filter(user=user, source=source).first()
    return {"facets": row.facets if row else None}


def set_pinned(user: User, slug: str, data):
    source = _source(user, slug)
    serializer = PinnedFacetsSerializer(data=data)
    if not serializer.is_valid():
        raise SerializerValidationError(serializer)
    facets = list(dict.fromkeys(serializer.validated_data["facets"]))
    PinnedFacets.objects.update_or_create(
        user=user, source=source, defaults={"facets": facets}
    )
    return {"facets": facets}


def favorite_dashboards(user: User):
    visible = {d.pk: d.slug for d in rbac_manager.get_dashboards(user)}
    ids = DashboardFavorite.objects.filter(
        user=user, dashboard_id__in=visible
    ).values_list("dashboard_id", flat=True)
    return {"dashboards": sorted(visible[pk] for pk in ids)}


def set_favorite_dashboard(user: User, slug: str, favorite: bool):
    with transaction.atomic():
        dashboard: Dashboard = DashboardService()._get(
            user, slug, permissions.Dashboard.READ.value
        )
        if favorite:
            DashboardFavorite.objects.get_or_create(user=user, dashboard=dashboard)
        else:
            DashboardFavorite.objects.filter(user=user, dashboard=dashboard).delete()
    return favorite_dashboards(user)
