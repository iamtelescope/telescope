"""HTTP delivery: private-target refusal, no redirects, retries with exponential backoff."""

import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import requests

TIMEOUT_SECONDS = 10
RETRIES = 3
BACKOFF_SECONDS = 1.0
RETRY_STATUSES = {429, 500, 502, 503, 504}


class DeliveryError(Exception):
    pass


def _is_public(addr) -> bool:
    if getattr(addr, "ipv4_mapped", None):
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def check_url(url: str, allow_private: bool):
    """Refuses non-http(s) URLs and, unless allowed, hosts resolving to a non-public address."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise DeliveryError("URL must be http(s) with a host")
    if allow_private:
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as err:
        raise DeliveryError(f"cannot resolve {parsed.hostname}: {err}")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0].split("%")[0])
        if not _is_public(addr):
            raise DeliveryError(
                f"{parsed.hostname} resolves to a private or loopback address ({addr}); "
                "set alerts.allow_private_webhook_targets to allow it"
            )


def post(url: str, body, headers: dict, allow_private: bool) -> requests.Response:
    check_url(url, allow_private)
    data = body if isinstance(body, (str, bytes)) else json.dumps(body)
    if isinstance(data, str):
        data = data.encode()
    headers = {"Content-Type": "application/json", **(headers or {})}
    error = None
    for attempt in range(RETRIES + 1):
        if attempt:
            time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
        try:
            response = requests.post(
                url,
                data=data,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException as err:
            error = DeliveryError(f"request failed: {err}")
            continue
        if 300 <= response.status_code < 400:
            raise DeliveryError(
                f"HTTP {response.status_code}: redirects are not followed"
            )
        if response.status_code < 300:
            return response
        error = DeliveryError(
            f"HTTP {response.status_code}: {response.text[:200]}".strip()
        )
        if response.status_code not in RETRY_STATUSES:
            raise error
    raise error
