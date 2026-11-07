"""The scheduler tick and the DB lease that lets only one replica evaluate."""

import logging
from datetime import timedelta

from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from telescope_alerts.evaluator import evaluate_alert
from telescope_alerts.models import STATE_DISABLED, Alert, SchedulerLease

logger = logging.getLogger("telescope.alerts")

LEASE_NAME = "alerts"


def acquire_lease(holder: str, seconds: int) -> bool:
    """Takes or renews the lease; plain UPDATE/INSERT so it works on SQLite, Postgres and MySQL.
    Only a lost insert race means "held elsewhere"; other database errors propagate."""
    now = timezone.now()
    expires = now + timedelta(seconds=seconds)
    try:
        with transaction.atomic():
            updated = (
                SchedulerLease.objects.filter(name=LEASE_NAME)
                .filter(Q(holder=holder) | Q(expires_at__lt=now))
                .update(holder=holder, expires_at=expires)
            )
        if updated:
            return True
        with transaction.atomic():
            SchedulerLease.objects.create(
                name=LEASE_NAME, holder=holder, expires_at=expires
            )
        return True
    except IntegrityError as err:
        logger.debug("lease not acquired by %s: %s", holder, err)
        return False


def release_lease(holder: str):
    SchedulerLease.objects.filter(name=LEASE_NAME, holder=holder).delete()


def tick(holder: str, lease_seconds: int, at_ms=None) -> int:
    """One pass over all alerts; returns the windows written, or -1 without the lease."""
    close_old_connections()
    if not acquire_lease(holder, lease_seconds):
        return -1
    written = 0
    ids = list(
        Alert.objects.exclude(state=STATE_DISABLED)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    lost = []

    def renew() -> bool:
        # Renewed before every window and after every delivery, since one alert can outlast the lease.
        if not lost and not acquire_lease(holder, lease_seconds):
            logger.warning("scheduler %s lost the lease", holder)
            lost.append(True)
        return not lost

    for pk in ids:
        if not renew():
            return written
        alert = Alert.objects.select_related("owner", "dashboard").filter(pk=pk).first()
        if alert is None:
            continue
        try:
            written += evaluate_alert(alert, at_ms, renew)
        except Exception:
            logger.exception("alert %s evaluation crashed", pk)
    return written
