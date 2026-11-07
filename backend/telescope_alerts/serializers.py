import math

from rest_framework import serializers

from telescope.constants import CHART_MAX_SERIES
from telescope.models import Dashboard
from telescope.serializers.dashboard import ChartSeriesSerializer, StrictSerializer

from telescope_alerts.channels import clean_config, mask_config
from telescope_alerts.definition import AlertDefinitionError, resolve
from telescope_alerts.models import (
    ALERT_KINDS,
    CHANNEL_KINDS,
    INTERVAL_MINUTES,
    KIND_SEARCH,
    MAX_CHANNELS_PER_ALERT,
    RANGE_THRESHOLD_TYPES,
    THRESHOLD_TYPES,
    AlertChannel,
)

MAX_WINDOWS = 10
MAX_TAGS = 20


class FiniteFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            raise serializers.ValidationError("must be a finite number")
        return value


class AlertInputSerializer(StrictSerializer):
    """Context: `user`, the one the alert runs as, and optionally `now` for previews."""

    name = serializers.CharField(max_length=255)
    kind = serializers.ChoiceField(choices=ALERT_KINDS)
    source = serializers.CharField(max_length=64, required=False, allow_blank=True)
    query = serializers.CharField(allow_blank=True, required=False, default="")
    raw_query = serializers.CharField(allow_blank=True, required=False, default="")
    context_columns = serializers.DictField(required=False, default=dict)
    group_by = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=255
    )
    series = ChartSeriesSerializer(required=False)
    dashboard = serializers.CharField(max_length=262, required=False, allow_blank=True)
    tile_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    series_index = serializers.IntegerField(
        min_value=0, max_value=CHART_MAX_SERIES - 1, required=False, default=0
    )
    interval = serializers.ChoiceField(choices=list(INTERVAL_MINUTES))
    threshold_type = serializers.ChoiceField(choices=THRESHOLD_TYPES)
    threshold = FiniteFloatField()
    threshold_max = FiniteFloatField(required=False, allow_null=True, default=None)
    consecutive_windows = serializers.IntegerField(
        min_value=1, max_value=MAX_WINDOWS, required=False, default=1
    )
    of_windows = serializers.IntegerField(
        min_value=1, max_value=MAX_WINDOWS, required=False, default=1
    )
    note = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=4096
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=list,
        max_length=MAX_TAGS,
    )
    channels = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        max_length=MAX_CHANNELS_PER_ALERT,
    )

    def validate_channels(self, value):
        value = list(dict.fromkeys(value))
        found = set(
            AlertChannel.objects.filter(pk__in=value).values_list("pk", flat=True)
        )
        missing = [str(pk) for pk in value if pk not in found]
        if missing:
            raise serializers.ValidationError(f"unknown channel {', '.join(missing)}")
        return value

    def validate(self, attrs):
        errors = {}
        if attrs["kind"] == KIND_SEARCH:
            if not attrs.get("source"):
                errors["source"] = ["This field is required."]
            if "series" not in attrs:
                errors["series"] = ["This field is required."]
            attrs["dashboard"], attrs["tile_id"] = None, ""
        else:
            slug = attrs.get("dashboard") or ""
            attrs["dashboard"] = Dashboard.objects.filter(slug=slug).first()
            if attrs["dashboard"] is None:
                errors["dashboard"] = ["dashboard not found"]
            if not attrs.get("tile_id"):
                errors["tile_id"] = ["This field is required."]
        if attrs["threshold_type"] in RANGE_THRESHOLD_TYPES:
            if attrs.get("threshold_max") is None:
                errors["threshold_max"] = [f"required for {attrs['threshold_type']}"]
            elif attrs["threshold_max"] < attrs["threshold"]:
                errors["threshold_max"] = ["must be at least threshold"]
        else:
            attrs["threshold_max"] = None
        if attrs["of_windows"] < attrs["consecutive_windows"]:
            errors["of_windows"] = ["must be at least consecutive_windows"]
        if errors:
            raise serializers.ValidationError(errors)
        try:
            attrs["resolved"] = resolve(self.context["user"], attrs)
        except AlertDefinitionError as err:
            raise serializers.ValidationError(
                err.errors or {"non_field_errors": [err.message]}
            )
        return attrs


class ChannelInputSerializer(StrictSerializer):
    """Context: `old`, the stored channel on update, so masked secrets are kept."""

    name = serializers.CharField(max_length=128)
    kind = serializers.ChoiceField(choices=CHANNEL_KINDS)
    config = serializers.DictField()

    def validate(self, attrs):
        old = self.context.get("old")
        old_config = old.config if old is not None and old.kind == attrs["kind"] else {}
        config, errors = clean_config(attrs["kind"], attrs["config"], old_config)
        if errors:
            raise serializers.ValidationError({"config": errors})
        attrs["config"] = config
        return attrs


def user_dict(user):
    if user is None:
        return None
    return {"id": user.pk, "username": user.username}


def channel_dict(channel, with_config: bool):
    data = {"id": channel.pk, "name": channel.name, "kind": channel.kind}
    if with_config:
        data["config"] = mask_config(channel.kind, channel.config)
        data["created_by"] = user_dict(channel.created_by)
        data["updated_at"] = channel.updated_at
    return data


def alert_dict(alert, can_edit: bool):
    dashboard = None
    if alert.dashboard_id:
        dashboard = {"slug": alert.dashboard.slug, "name": alert.dashboard.name}
    return {
        "id": alert.pk,
        "name": alert.name,
        "kind": alert.kind,
        "source": alert.source_slug,
        "query": alert.query,
        "raw_query": alert.raw_query,
        "context_columns": alert.context_columns,
        "group_by": alert.group_by,
        "series": alert.series,
        "dashboard": dashboard,
        "tile_id": alert.tile_id,
        "series_index": alert.series_index,
        "interval": alert.interval,
        "threshold_type": alert.threshold_type,
        "threshold": alert.threshold,
        "threshold_max": alert.threshold_max,
        "consecutive_windows": alert.consecutive_windows,
        "of_windows": alert.of_windows,
        "state": alert.state,
        "last_error": alert.last_error,
        "firing_groups": alert.firing_groups,
        "note": alert.note,
        "tags": alert.tags,
        "channels": [c.pk for c in alert.channels.all()],
        "owner": user_dict(alert.owner),
        "last_evaluated_window": alert.last_evaluated_window,
        "last_evaluated_at": alert.last_evaluated_at,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
        "can_edit": can_edit,
    }


def history_dict(row):
    return {
        "group_key": row.group_key,
        "window_start": row.window_start,
        "window_end": row.window_end,
        "state": row.state,
        "value": row.value,
        "error": row.error,
        "notified_at": row.notified_at,
    }
