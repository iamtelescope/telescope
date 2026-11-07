import os
import signal
import socket
import time
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telescope.utils import parse_time
from telescope_alerts.scheduler import release_lease, tick


def _stop(signum, frame):
    raise KeyboardInterrupt


class Command(BaseCommand):
    help = "Evaluates alerts every alerts.tick_seconds; a DB lease keeps it to one replica."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="run one tick and exit")
        parser.add_argument(
            "--now",
            help="evaluate as of this time (ms timestamp), for replaying past data; implies --once",
        )
        parser.add_argument("--holder", help="lease holder id (default host:pid)")

    def handle(self, *args, **options):
        config = settings.CONFIG.get("alerts") or {}
        tick_seconds = int(config.get("tick_seconds") or 15)
        lease_seconds = max(120, tick_seconds * 8)
        holder = (
            options["holder"]
            or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        )
        at_ms = None
        if options["now"]:
            at_ms, error = parse_time(options["now"])
            if error:
                raise CommandError(f"--now: {error}")
        if options["once"] or at_ms is not None:
            written = tick(holder, lease_seconds, at_ms)
            self.stdout.write(
                "lease held by another scheduler"
                if written < 0
                else f"{written} windows evaluated"
            )
            return
        self.stdout.write(f"telescope scheduler {holder}, tick {tick_seconds}s")
        # SIGTERM releases the lease so another replica takes over at once.
        signal.signal(signal.SIGTERM, _stop)
        try:
            while True:
                started = time.monotonic()
                if config.get("enabled", True):
                    tick(holder, lease_seconds)
                time.sleep(max(1.0, tick_seconds - (time.monotonic() - started)))
        except KeyboardInterrupt:
            pass
        finally:
            release_lease(holder)
