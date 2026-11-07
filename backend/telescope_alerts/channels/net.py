"""HTTP delivery: private-target refusal, no redirects, retries with exponential backoff."""

import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import certifi
import urllib3

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


def check_url(url: str, allow_private: bool) -> str:
    """Refuses non-http(s) URLs and, unless allowed, non-public hosts; returns the address to dial."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise DeliveryError("URL must be http(s) with a host")
    if allow_private:
        return parsed.hostname
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
    return infos[0][4][0]


def _pool(parsed, address: str):
    """A connection pool to `address`; TLS still checks the certificate against the URL's host."""
    if parsed.scheme == "http":
        return urllib3.HTTPConnectionPool(address, parsed.port or 80, retries=False)
    return urllib3.HTTPSConnectionPool(
        address,
        parsed.port or 443,
        retries=False,
        cert_reqs="CERT_REQUIRED",
        ca_certs=certifi.where(),
        server_hostname=parsed.hostname,
        assert_hostname=parsed.hostname,
    )


def post(url: str, body, headers: dict, allow_private: bool):
    # The connection goes to the address check_url validated, never through an env proxy.
    address = check_url(url, allow_private)
    parsed = urlparse(url)
    data = body if isinstance(body, (str, bytes)) else json.dumps(body)
    if isinstance(data, str):
        data = data.encode()
    host = parsed.netloc.rpartition("@")[2]
    headers = {"Content-Type": "application/json", **(headers or {}), "Host": host}
    if parsed.username is not None:
        auth = f"{parsed.username}:{parsed.password or ''}"
        headers.update(urllib3.make_headers(basic_auth=auth))
    path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
    error = None
    with _pool(parsed, address) as pool:
        for attempt in range(RETRIES + 1):
            if attempt:
                time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
            try:
                response = pool.urlopen(
                    "POST",
                    path,
                    body=data,
                    headers=headers,
                    redirect=False,
                    timeout=urllib3.Timeout(TIMEOUT_SECONDS),
                )
            except urllib3.exceptions.HTTPError as err:
                error = DeliveryError(f"request failed: {err}")
                continue
            status = response.status
            if 300 <= status < 400:
                raise DeliveryError(f"HTTP {status}: redirects are not followed")
            if status < 300:
                return response
            text = response.data[:200].decode(errors="replace")
            error = DeliveryError(f"HTTP {status}: {text}".strip())
            if status not in RETRY_STATUSES:
                raise error
    raise error
