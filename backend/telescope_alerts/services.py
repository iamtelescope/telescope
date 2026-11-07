from typing import Any, Dict

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction

from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.services.exceptions import SerializerValidationError

from telescope_alerts import channels as channel_delivery
from telescope_alerts import templating
from telescope_alerts.evaluator import preview
from telescope_alerts.models import KIND_TILE, Alert, AlertChannel
from telescope_alerts.serializers import (
    AlertInputSerializer,
    ChannelInputSerializer,
    alert_dict,
    channel_dict,
    history_dict,
)

ALERT_NOT_FOUND = "Alert not found"
CHANNEL_NOT_FOUND = "Channel not found"
HISTORY_LIMIT = 500
DEFINITION_FIELDS = [
    "kind",
    "query",
    "raw_query",
    "context_columns",
    "group_by",
    "dashboard",
    "tile_id",
    "series_index",
]
SETTINGS_FIELDS = [
    "name",
    "interval",
    "threshold_type",
    "threshold",
    "threshold_max",
    "consecutive_windows",
    "of_windows",
    "note",
    "tags",
]

rbac_manager = RBACManager()


def can_manage_channels(user: User) -> bool:
    return (
        permissions.Global.MANAGE_ALERT_CHANNELS.value
        in rbac_manager.get_user_global_permissions(user)
    )


class AlertService:
    def _queryset(self):
        return Alert.objects.select_related("owner", "dashboard").prefetch_related(
            "channels"
        )

    def can_edit(self, user: User, alert: Alert) -> bool:
        return user.is_superuser or alert.owner_id == user.pk

    def _visible(self, user: User, alert: Alert, usable: set) -> bool:
        """Owners always see their alerts; others need Source.USE (and dashboard read for tiles)."""
        if self.can_edit(user, alert):
            return True
        if alert.source_slug not in usable:
            return False
        if alert.kind == KIND_TILE:
            perms = rbac_manager.calculate_dashboard_permissions(user, alert.dashboard)
            return permissions.Dashboard.READ.value in perms
        return True

    def _usable(self, user: User) -> set:
        return {
            s.slug
            for s in rbac_manager.get_sources(
                user, required_permissions=[permissions.Source.USE.value]
            )
        }

    def _get(self, user: User, pk: int, for_edit=False) -> Alert:
        alert = self._queryset().filter(pk=pk).first()
        if alert is None or not self._visible(user, alert, self._usable(user)):
            raise Alert.DoesNotExist(ALERT_NOT_FOUND)
        if for_edit and not self.can_edit(user, alert):
            raise PermissionDenied("Only the owner can change this alert")
        return alert

    def list(self, user: User):
        usable = self._usable(user)
        return [
            alert_dict(alert, self.can_edit(user, alert))
            for alert in self._queryset().order_by("name", "pk")
            if self._visible(user, alert, usable)
        ]

    def get(self, user: User, pk: int):
        alert = self._get(user, pk)
        return alert_dict(alert, self.can_edit(user, alert))

    def _validate(self, user: User, data: Dict[str, Any]):
        serializer = AlertInputSerializer(data=data, context={"user": user})
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        return serializer.validated_data

    def _apply(self, alert: Alert, attrs: Dict[str, Any]):
        aq = attrs["resolved"]
        for name in DEFINITION_FIELDS + SETTINGS_FIELDS:
            setattr(alert, name, attrs[name])
        alert.source_slug = aq.source.slug
        alert.series = aq.series
        if alert.kind == KIND_TILE:
            alert.query = alert.raw_query = alert.group_by = ""
            alert.context_columns = {}

    def create(self, user: User, data: Dict[str, Any]):
        attrs = self._validate(user, data)
        with transaction.atomic():
            alert = Alert(owner=user)
            self._apply(alert, attrs)
            alert.save()
            alert.channels.set(attrs["channels"])
        return self.get(user, alert.pk)

    def update(self, user: User, pk: int, data: Dict[str, Any]):
        alert = self._get(user, pk, for_edit=True)
        # The alert keeps running as its owner, so it is validated as the owner.
        attrs = self._validate(alert.owner, data)
        with transaction.atomic():
            interval = alert.interval
            self._apply(alert, attrs)
            if alert.interval != interval:
                alert.last_evaluated_window = None
            alert.save()
            alert.channels.set(attrs["channels"])
        return self.get(user, alert.pk)

    def delete(self, user: User, pk: int):
        self._get(user, pk, for_edit=True).delete()

    def history(self, user: User, pk: int):
        alert = self._get(user, pk)
        rows = alert.history.order_by("-window_start", "group_key")[:HISTORY_LIMIT]
        return [history_dict(row) for row in rows]

    def preview(self, user: User, data: Dict[str, Any], at_ms=None):
        attrs = self._validate(user, data)
        alert = Alert(owner=user)
        self._apply(alert, attrs)
        return preview(alert, attrs["resolved"], at_ms)


class ChannelService:
    def _require(self, user: User):
        if not can_manage_channels(user):
            raise PermissionDenied(
                "Managing alert channels needs manage_alert_channels"
            )

    def _get(self, pk: int) -> AlertChannel:
        channel = (
            AlertChannel.objects.select_related("created_by").filter(pk=pk).first()
        )
        if channel is None:
            raise AlertChannel.DoesNotExist(CHANNEL_NOT_FOUND)
        return channel

    def list(self, user: User):
        manager = can_manage_channels(user)
        return [
            channel_dict(c, manager)
            for c in AlertChannel.objects.select_related("created_by").order_by(
                "name", "pk"
            )
        ]

    def _validate(self, data, old=None):
        serializer = ChannelInputSerializer(data=data, context={"old": old})
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        return serializer.validated_data

    def create(self, user: User, data: Dict[str, Any]):
        self._require(user)
        attrs = self._validate(data)
        channel = AlertChannel.objects.create(created_by=user, **attrs)
        return channel_dict(channel, True)

    def update(self, user: User, pk: int, data: Dict[str, Any]):
        self._require(user)
        channel = self._get(pk)
        attrs = self._validate(data, old=channel)
        for name, value in attrs.items():
            setattr(channel, name, value)
        channel.save()
        return channel_dict(channel, True)

    def delete(self, user: User, pk: int):
        self._require(user)
        self._get(pk).delete()

    def test(self, user: User, pk: int):
        """Sends a sample firing message; raises DeliveryError (or another error) on failure."""
        self._require(user)
        channel = self._get(pk)
        public_url = channel_delivery.alerts_config().get("public_url", "")
        channel_delivery.send(channel, templating.sample_message(public_url))
