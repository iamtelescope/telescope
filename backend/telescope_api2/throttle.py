import threading
import time

from cachetools import TTLCache
from rest_framework.throttling import BaseThrottle

RATE_LIMIT_PER_MINUTE = 600
WINDOW_SECONDS = 60

# Fixed one-minute windows per user, counted in this process only.
_hits = TTLCache(maxsize=100_000, ttl=2 * WINDOW_SECONDS)
_lock = threading.Lock()


class TokenRateThrottle(BaseThrottle):
    def allow_request(self, request, view):
        window = int(time.time() // WINDOW_SECONDS)
        key = (request.user.pk or self.get_ident(request), window)
        with _lock:
            count = _hits.get(key, 0) + 1
            _hits[key] = count
        return count <= RATE_LIMIT_PER_MINUTE

    def wait(self):
        return WINDOW_SECONDS - time.time() % WINDOW_SECONDS
