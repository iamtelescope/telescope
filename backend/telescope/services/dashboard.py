import os
import hashlib
from typing import Any, Dict

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.text import slugify

from telescope.models import Dashboard
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.dashboard import (
    DashboardSerializer,
    DashboardListSerializer,
    NewDashboardSerializer,
    UpdateDashboardSerializer,
    dashboard_raw_queries,
    dashboard_sources,
)
from telescope.services.exceptions import SerializerValidationError
from telescope.services.helpers import check_user_hit_create_dashboards_limit

DASHBOARD_NOT_FOUND = "Dashboard not found"


class DashboardService:
    def __init__(self):
        self.rbac_manager = RBACManager()

    def _get(
        self, user: User, slug: str, permission: str, for_update: bool = False
    ) -> Dashboard:
        queryset = Dashboard.objects.select_related("owner", "updated_by")
        if for_update:
            queryset = queryset.select_for_update()
        try:
            dashboard = queryset.get(slug=slug)
        except Dashboard.DoesNotExist:
            raise Dashboard.DoesNotExist(DASHBOARD_NOT_FOUND)
        dashboard.add_perms(
            self.rbac_manager.calculate_dashboard_permissions(user, dashboard)
        )
        if permissions.Dashboard.READ.value not in dashboard.permissions:
            raise Dashboard.DoesNotExist(DASHBOARD_NOT_FOUND)
        if permission not in dashboard.permissions:
            raise PermissionDenied("Insufficient permissions")
        return dashboard

    def list(self, user: User):
        with transaction.atomic():
            dashboards = self.rbac_manager.get_dashboards(user)
            return DashboardListSerializer(dashboards, many=True).data

    def get(self, user: User, slug: str):
        with transaction.atomic():
            dashboard = self._get(user, slug, permissions.Dashboard.READ.value)
            return DashboardSerializer(dashboard).data

    def create(self, user: User, data: Dict[str, Any]):
        with transaction.atomic():
            serializer = NewDashboardSerializer(
                data=data, context={"user": user, "old_sources": set()}
            )
            if not serializer.is_valid():
                raise SerializerValidationError(serializer)
            ok, message = check_user_hit_create_dashboards_limit(user)
            if not ok:
                raise ValueError(message)
            salt = hashlib.sha1(os.urandom(32)).hexdigest()[:6]
            dashboard = Dashboard.objects.create(
                slug=f"{slugify(serializer.validated_data['name'])}-{salt}",
                name=serializer.validated_data["name"],
                description=serializer.validated_data["description"],
                shared=serializer.validated_data["shared"],
                data=serializer.validated_data["data"],
                owner=user,
                updated_by=user,
            )
            dashboard.add_perms(
                self.rbac_manager.calculate_dashboard_permissions(user, dashboard)
            )
            return DashboardSerializer(dashboard).data

    def update(self, user: User, slug: str, data: Dict[str, Any]):
        with transaction.atomic():
            dashboard = self._get(
                user, slug, permissions.Dashboard.EDIT.value, for_update=True
            )
            serializer = UpdateDashboardSerializer(
                data=data,
                context={
                    "user": user,
                    "old_sources": dashboard_sources(dashboard.data),
                    "old_raw_queries": dashboard_raw_queries(dashboard.data),
                    "version": dashboard.version,
                },
            )
            if not serializer.is_valid():
                raise SerializerValidationError(serializer)
            for key in ["name", "description", "shared", "data"]:
                setattr(dashboard, key, serializer.validated_data[key])
            dashboard.version += 1
            dashboard.updated_by = user
            dashboard.save()
            return DashboardSerializer(dashboard).data

    def delete(self, user: User, slug: str):
        with transaction.atomic():
            dashboard = self._get(user, slug, permissions.Dashboard.DELETE.value)
            dashboard.delete()
