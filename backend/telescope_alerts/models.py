from django.contrib.auth.models import User
from django.db import models

from telescope.models import Dashboard

KIND_SEARCH = "search"
KIND_TILE = "tile"
ALERT_KINDS = [KIND_SEARCH, KIND_TILE]

INTERVAL_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "6h": 360,
    "12h": 720,
    "1d": 1440,
}

THRESHOLD_TYPES = [
    "above",
    "above_exclusive",
    "below",
    "below_or_equal",
    "equal",
    "not_equal",
    "between",
    "not_between",
]
RANGE_THRESHOLD_TYPES = {"between", "not_between"}

STATE_OK = "OK"
STATE_ALERT = "ALERT"
STATE_PENDING = "PENDING"
STATE_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
STATE_ERROR = "ERROR"
STATE_DISABLED = "DISABLED"
ALERT_STATES = [
    STATE_OK,
    STATE_ALERT,
    STATE_PENDING,
    STATE_INSUFFICIENT_DATA,
    STATE_ERROR,
    STATE_DISABLED,
]

CHANNEL_KINDS = ["slack", "webhook", "pagerduty", "email"]
MAX_CHANNELS_PER_ALERT = 10


def _choices(values):
    return [(v, v) for v in values]


class AlertChannel(models.Model):
    kind = models.CharField(max_length=16, choices=_choices(CHANNEL_KINDS))
    name = models.CharField(max_length=128)
    config = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.kind}:{self.name}"


class Alert(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alerts")
    kind = models.CharField(max_length=8, choices=_choices(ALERT_KINDS))
    # Search alerts carry the query; tile alerts keep the source of their tile here.
    source_slug = models.CharField(max_length=64, blank=True, db_index=True)
    query = models.TextField(blank=True, default="")
    raw_query = models.TextField(blank=True, default="")
    context_columns = models.JSONField(default=dict, blank=True)
    group_by = models.CharField(max_length=255, blank=True, default="")
    series = models.JSONField(default=dict, blank=True)
    dashboard = models.ForeignKey(
        Dashboard, on_delete=models.CASCADE, null=True, blank=True
    )
    tile_id = models.CharField(max_length=32, blank=True, default="")
    series_index = models.PositiveSmallIntegerField(default=0)
    interval = models.CharField(max_length=4, choices=_choices(INTERVAL_MINUTES))
    threshold_type = models.CharField(max_length=16, choices=_choices(THRESHOLD_TYPES))
    threshold = models.FloatField()
    threshold_max = models.FloatField(null=True, blank=True)
    consecutive_windows = models.PositiveSmallIntegerField(default=1)
    of_windows = models.PositiveSmallIntegerField(default=1)
    state = models.CharField(
        max_length=20, choices=_choices(ALERT_STATES), default=STATE_OK
    )
    last_error = models.TextField(blank=True, default="")
    # Groups notified as firing and not yet resolved.
    firing_groups = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    channels = models.ManyToManyField(AlertChannel, blank=True, related_name="alerts")
    # Start (ms) of the last window evaluated without error.
    last_evaluated_window = models.BigIntegerField(null=True, blank=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def interval_ms(self) -> int:
        return INTERVAL_MINUTES[self.interval] * 60_000

    def __str__(self):
        return f"alert {self.pk} {self.name}"


class AlertHistory(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="history")
    group_key = models.CharField(max_length=255, blank=True, default="")
    window_start = models.BigIntegerField()
    window_end = models.BigIntegerField()
    state = models.CharField(max_length=20, choices=_choices(ALERT_STATES))
    value = models.FloatField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "group_key", "window_start"],
                name="telescope_alerts_history_unique_window",
            )
        ]
        indexes = [models.Index(fields=["alert", "window_start"])]


class SchedulerLease(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
    holder = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
