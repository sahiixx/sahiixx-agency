"""Validation helpers for T3MP3ST target scoping."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
_DEFAULT_BLOCKED_NETWORKS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
]


def _host_from_target(target: str) -> str:
    """Extract a hostname from a target that may be a URL, IP, or plain host."""
    stripped = target.strip()
    if "//" not in stripped:
        stripped = f"//{stripped}"
    parsed = urlparse(stripped)
    host = parsed.hostname or stripped.lstrip("/")
    return host.lower()


def _is_blocked_host(host: str, allow_local: bool) -> bool:
    if allow_local:
        return False
    return host in _BLOCKED_HOSTS


def _is_blocked_network(host: str, networks: list[str], allow_local: bool) -> bool:
    if allow_local:
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    for net_str in networks:
        network = ipaddress.ip_network(net_str, strict=False)
        if addr in network:
            return True
    return False


def validate_target(
    target: str,
    *,
    allow_local: bool = False,
    blocked_networks: list[str] | None = None,
) -> str | None:
    """Validate a T3MP3ST target.

    Returns an error code string or ``None`` if the target is acceptable.
    """
    if not target or not target.strip():
        return "missing_target"

    host = _host_from_target(target)
    if not host:
        return "invalid_target"

    if _is_blocked_host(host, allow_local):
        return "blocked_target"

    networks = blocked_networks or _DEFAULT_BLOCKED_NETWORKS
    if _is_blocked_network(host, networks, allow_local):
        return "blocked_target"

    return None
