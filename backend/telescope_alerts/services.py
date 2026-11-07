from typing import Any, Dict

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.models import SavedView
from telescope.services.exceptions import SerializerValidationError

from telescope_alerts import channels as channel_delivery
from telescope_alerts import templating
from telescope_alerts.definition import AlertDefinitionError, alert_data, resolve
from telescope_alerts.evaluator import latest_window_start, notify, now_ms, preview
from telescope_alerts.models import (
    KIND_SEARCH,
    KIND_TILE,
    STATE_ALERT,
    STATE_DISABLED,
    STATE_ERROR,
    STATE_INSUFFICIENT_DATA,
    STATE_OK,
    STATE_PENDING,
    Alert,
    AlertChannel,
    AlertHistory,
    SavedViewFavorite,
    SavedViewTags,
)
from telescope_alerts.serializers import (
    AlertInputSerializer,
    ChannelInputSerializer,
    SavedViewMetaInputSerializer,
    SilenceInputSerializer,
    alert_dict,
    channel_dict,
    history_dict,
)

ALERT_NOT_FOUND = "Alert not found"
CHANNEL_NOT_FOUND = "Channel not found"
HISTORY_LIMIT = 500
RANGE_HISTORY_LIMIT = 10_000
MAX_PAGE_SIZE = 100
MAX_EVALUATIONS = 200
# The worst state of a window's groups is the window's state.
STATE_RANK = [
    STATE_ERROR,
    STATE_ALERT,
    STATE_PENDING,
    STATE_OK,
    STATE_INSUFFICIENT_DATA,
]
SCHEDULE_FIELDS = ["interval", "schedule_offset_minutes", "schedule_start_at"]
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
    "schedule_offset_minutes",
    "schedule_start_at",
]

rbac_manager = RBACManager()


def can_manage_channels(user: User) -> bool:
    return (
        permissions.Global.MANAGE_ALERT_CHANNELS.value
        in rbac_manager.get_user_global_permissions(user)
    )


class AlertService:
    def _queryset(self):
        return Alert.objects.select_related(
            "owner", "dashboard", "silenced_by"
        ).prefetch_related("channels")

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

    def _visible_alerts(self, user: User, queryset=None):
        usable = self._usable(user)
        queryset = self._queryset() if queryset is None else queryset
        return [a for a in queryset if self._visible(user, a, usable)]

    def list(self, user: User, params=None):
        """A plain list without `page`; with it, one page filtered by tags (all of), state and name.
        Both narrow to one dashboard's tile alerts with `dashboard`."""
        params = params or {}
        queryset = self._queryset().order_by("name", "pk")
        if params.get("dashboard"):
            queryset = queryset.filter(
                kind=KIND_TILE, dashboard__slug=params["dashboard"]
            )
        alerts = self._visible_alerts(user, queryset)
        if "page" not in params:
            return [alert_dict(a, self.can_edit(user, a)) for a in alerts]
        all_tags = sorted({t for a in alerts for t in a.tags or []})
        tags = [t for t in (params.get("tags") or "").split(",") if t]
        states = [t for t in (params.get("state") or "").split(",") if t]
        name = (params.get("q") or "").strip().lower()
        alerts = [
            a
            for a in alerts
            if all(t in (a.tags or []) for t in tags)
            and (not states or a.state in states)
            and name in a.name.lower()
        ]
        page = max(1, as_int(params.get("page"), 1))
        size = min(MAX_PAGE_SIZE, max(1, as_int(params.get("page_size"), 25)))
        items = alerts[(page - 1) * size : page * size]
        return {
            "items": [alert_dict(a, self.can_edit(user, a)) for a in items],
            "total": len(alerts),
            "page": page,
            "page_size": size,
            "tags": all_tags,
        }

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
            schedule = [getattr(alert, f) for f in SCHEDULE_FIELDS]
            self._apply(alert, attrs)
            # Only the user's fields: the scheduler may have moved its own columns since _get.
            fields = DEFINITION_FIELDS + SETTINGS_FIELDS
            fields += ["source_slug", "series", "updated_at"]
            if [getattr(alert, f) for f in SCHEDULE_FIELDS] != schedule:
                alert.last_evaluated_window = None
                fields.append("last_evaluated_window")
            alert.save(update_fields=fields)
            alert.channels.set(attrs["channels"])
        return self.get(user, alert.pk)

    def delete(self, user: User, pk: int):
        self._get(user, pk, for_edit=True).delete()

    def history(self, user: User, pk: int, time_from=None, time_to=None):
        """Newest 500 rows, or with a range every row whose window starts in [from, to), oldest first."""
        alert = self._get(user, pk)
        if time_from is None or time_to is None:
            rows = alert.history.order_by("-window_start", "group_key")[:HISTORY_LIMIT]
        else:
            rows = alert.history.filter(
                window_start__gte=time_from, window_start__lt=time_to
            ).order_by("window_start", "group_key")[:RANGE_HISTORY_LIMIT]
        return [history_dict(row) for row in rows]

    def evaluations(self, user: User, pk: int, limit=50, before=None):
        """One entry per window across its groups, newest first; page with `next_before`."""
        alert = self._get(user, pk)
        limit = min(MAX_EVALUATIONS, max(1, limit))
        starts = alert.history.order_by("-window_start")
        if before is not None:
            starts = starts.filter(window_start__lt=before)
        starts = list(
            starts.values_list("window_start", flat=True).distinct()[: limit + 1]
        )
        has_more = len(starts) > limit
        starts = starts[:limit]
        rows = alert.history.filter(window_start__in=starts).order_by(
            "-window_start", "group_key"
        )
        by_window = {}
        for row in rows:
            entry = by_window.setdefault(
                row.window_start,
                {
                    "window_start": row.window_start,
                    "window_end": row.window_end,
                    "groups": [],
                },
            )
            entry["groups"].append(history_dict(row))
        data = []
        for start in starts:
            entry = by_window[start]
            states = {g["state"] for g in entry["groups"]}
            entry["state"] = next(
                s for s in STATE_RANK + [STATE_DISABLED] if s in states
            )
            data.append(entry)
        return {
            "items": data,
            "has_more": has_more,
            "next_before": starts[-1] if has_more else None,
        }

    def markers(self, user: User, params):
        """Firing transitions (ALERT after a non-ALERT window) of the alerts on a source or a tile."""
        time_from, time_to = as_int(params.get("from")), as_int(params.get("to"))
        if time_from is None or time_to is None:
            raise ValueError("from and to are required")
        queryset = self._queryset()
        if params.get("source"):
            queryset = queryset.filter(kind=KIND_SEARCH, source_slug=params["source"])
        elif params.get("dashboard") and params.get("tile"):
            queryset = queryset.filter(
                kind=KIND_TILE,
                dashboard__slug=params["dashboard"],
                tile_id=params["tile"],
            )
        else:
            raise ValueError("source, or dashboard and tile, is required")
        markers = []
        for alert in self._visible_alerts(user, queryset):
            rows = alert.history.filter(
                window_start__gte=time_from - alert.interval_ms,
                window_start__lte=time_to,
            ).order_by("group_key", "window_start")
            previous = {}
            for row in rows.values_list("group_key", "window_start", "state"):
                group, start, state = row
                was = previous.get(group)
                previous[group] = (start, state)
                if state != STATE_ALERT or start < time_from:
                    continue
                if (
                    was
                    and was[1] == STATE_ALERT
                    and was[0] == start - alert.interval_ms
                ):
                    continue
                markers.append(
                    {
                        "time": start,
                        "alert_id": alert.pk,
                        "name": alert.name,
                        "group_key": group,
                    }
                )
        return sorted(markers, key=lambda m: (m["time"], m["alert_id"]))

    def silence(self, user: User, pk: int, data):
        """Anyone who can see an alert may silence (acknowledge) it, as in HyperDX."""
        alert = self._get(user, pk)
        serializer = SilenceInputSerializer(data=data)
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        Alert.objects.filter(pk=alert.pk).update(
            silenced_until=serializer.validated_data["until"],
            silenced_at=timezone.now(),
            silenced_by=user,
        )
        return self.get(user, pk)

    def unsilence(self, user: User, pk: int):
        alert = self._get(user, pk)
        Alert.objects.filter(pk=alert.pk).update(
            silenced_until=None, silenced_at=None, silenced_by=None
        )
        return self.get(user, pk)

    def set_enabled(self, user: User, pk: int, enabled: bool):
        alert = self._get(user, pk, for_edit=True)
        if enabled:
            Alert.objects.filter(pk=alert.pk, state=STATE_DISABLED).update(
                state=STATE_OK, last_error=""
            )
        else:
            Alert.objects.filter(pk=alert.pk).update(state=STATE_DISABLED)
        return self.get(user, pk)

    def test(self, user: User, pk: int):
        """Sends this alert's firing message, at its threshold over the last window, to its channels."""
        alert = self._get(user, pk, for_edit=True)
        channels = list(alert.channels.all())
        if not channels:
            raise ValueError("the alert has no channels")
        try:
            aq = resolve(alert.owner, alert_data(alert))
        except AlertDefinitionError as err:
            raise ValueError(err.message)
        start = latest_window_start(alert.interval, now_ms(), alert.window_origin)
        message = templating.build_message(
            alert,
            STATE_ALERT,
            "",
            aq.group_by_name,
            alert.threshold,
            start,
            start + alert.interval_ms,
            aq.source_query,
            channel_delivery.alerts_config().get("public_url", ""),
        )
        message["title"] = "[Test] " + message["title"]
        errors, sent = notify(alert, message)
        if errors:
            raise ValueError("; ".join(errors))
        return {"sent": sent}

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


def as_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class SavedViewMetaService:
    """Tags and favorites of saved views, plus the alerts that run the same search."""

    def _views(self, user: User, source_slug: str):
        return rbac_manager.get_source_saved_views(
            user=user,
            source_slug=source_slug,
            required_permissions=[permissions.Source.READ.value],
        )

    def list(self, user: User, source_slug: str):
        views = self._views(user, source_slug)
        ids = [v.pk for v in views]
        tags = dict(
            SavedViewTags.objects.filter(view_id__in=ids).values_list("view_id", "tags")
        )
        favorites = set(
            SavedViewFavorite.objects.filter(view_id__in=ids, user=user).values_list(
                "view_id", flat=True
            )
        )
        alerts = AlertService()._visible_alerts(
            user,
            Alert.objects.filter(kind=KIND_SEARCH, source_slug=source_slug).order_by(
                "name", "pk"
            ),
        )
        result = {}
        for view in views:
            query = ((view.data or {}).get("query") or "").strip()
            raw = ((view.data or {}).get("raw_query") or "").strip()
            # The UI's saved view model has no id, so it matches on slug and user.
            result[str(view.pk)] = {
                "id": view.pk,
                "slug": view.slug,
                "user_id": view.user_id,
                "tags": tags.get(view.pk, []),
                "favorite": view.pk in favorites,
                "alerts": [
                    {"id": a.pk, "name": a.name, "state": a.state}
                    for a in alerts
                    if a.query.strip() == query and a.raw_query.strip() == raw
                ],
            }
        return result

    def update(self, user: User, source_slug: str, view_id: int, data):
        view = next(
            (v for v in self._views(user, source_slug) if v.pk == view_id), None
        )
        if view is None:
            raise SavedView.DoesNotExist("Saved view not found")
        serializer = SavedViewMetaInputSerializer(data=data)
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        attrs = serializer.validated_data
        if "tags" in attrs:
            if permissions.SavedView.EDIT.value not in view.permissions:
                raise PermissionDenied("Only those who can edit the view can tag it")
            SavedViewTags.objects.update_or_create(
                view=view, defaults={"tags": attrs["tags"]}
            )
        if attrs.get("favorite") is True:
            SavedViewFavorite.objects.get_or_create(view=view, user=user)
        elif attrs.get("favorite") is False:
            SavedViewFavorite.objects.filter(view=view, user=user).delete()
        return self.list(user, source_slug)[str(view.pk)]
