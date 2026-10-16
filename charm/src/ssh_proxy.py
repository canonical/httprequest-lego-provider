# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Select an HTTP CONNECT proxy for Git SSH connections."""

import ipaddress
import re
from collections.abc import Mapping
from urllib.parse import urlsplit
from urllib.request import proxy_bypass_environment  # type: ignore[attr-defined]

CONNECTION_TIMEOUT = 10


def _validate_hostname(hostname: str) -> None:
    """Reject hostnames unsafe for SSH configuration or command arguments.

    Args:
        hostname: The DNS name or IP address to check.

    Raises:
        ValueError: If the hostname is invalid.
    """
    if "%" in hostname:
        raise ValueError("Scoped IP addresses and SSH expansion tokens are unsupported in hosts")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        labels = hostname.rstrip(".").split(".")
        if len(hostname) > 253 or not all(
            re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
            for label in labels
        ):
            raise ValueError("Git and proxy hosts must be DNS names or IP addresses") from None


def _bypass_proxy(hostname: str, port: int, no_proxy: str) -> bool:
    """Match Juju exclusions, including literal IP networks.

    Args:
        hostname: The Git host.
        port: The SSH port.
        no_proxy: Comma-separated Juju proxy exclusions.

    Returns:
        Whether this destination should use a direct connection.
    """
    hostname = hostname.lower().rstrip(".")
    address = f"[{hostname}]" if ":" in hostname else hostname
    exclusions = [item.strip() for item in no_proxy.split(",")]
    if proxy_bypass_environment(f"{address}:{port}", {"no": no_proxy}) or "*" in exclusions:
        return True
    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    # The standard library does not match IP networks or unbracketed IPv6 exclusions.
    for exclusion in exclusions:
        try:
            network = ipaddress.ip_network(exclusion, strict=False)
        except ValueError:
            continue
        if host_ip in network:
            return True
    return False


def select_proxy(hostname: str, port: int, environment: Mapping[str, str]) -> str:
    """Select an unauthenticated HTTP CONNECT proxy from Juju hook settings.

    Args:
        hostname: The Git host.
        port: The SSH port.
        environment: The charm hook environment.

    Returns:
        The proxy host:port, or an empty string for a direct connection.

    Raises:
        ValueError: If the Git hostname is invalid or the applicable proxy URL is unsupported.
    """
    _validate_hostname(hostname)
    if _bypass_proxy(hostname, port, environment.get("JUJU_CHARM_NO_PROXY", "")):
        return ""
    proxy = environment.get("JUJU_CHARM_HTTPS_PROXY") or environment.get("JUJU_CHARM_HTTP_PROXY")
    if not proxy:
        return ""
    return _proxy_address(proxy)


def _proxy_address(proxy: str) -> str:
    """Validate an HTTP proxy URL and extract its address.

    Args:
        proxy: The HTTP proxy URL.

    Returns:
        The proxy hostname and port suitable for Ncat.

    Raises:
        ValueError: If the proxy URL is unsupported or invalid.
    """
    url = urlsplit(proxy)
    if url.scheme != "http" or not url.hostname:
        raise ValueError(
            "SSH requires an http:// CONNECT proxy; other proxy schemes are unsupported"
        )
    if url.username is not None or url.password is not None:
        raise ValueError(
            "SSH proxy authentication is unsupported; use a proxy without credentials"
        )
    if url.path not in ("", "/") or url.query or url.fragment:
        raise ValueError("The SSH proxy URL must not contain a path, query, or fragment")
    _validate_hostname(url.hostname)
    proxy_port = url.port if url.port is not None else 80
    if not proxy_port:
        raise ValueError("The SSH proxy port must be between 1 and 65535")
    address = f"[{url.hostname}]" if ":" in url.hostname else url.hostname
    return f"{address}:{proxy_port}"


def ncat_command(proxy: str, hostname: str, port: str) -> list[str]:
    """Build the Ncat HTTP CONNECT command for Git SSH.

    Args:
        proxy: The validated HTTP proxy address.
        hostname: The destination hostname, or the SSH %h token.
        port: The destination port, or the SSH %p token.

    Returns:
        The Ncat arguments without shell interpolation.
    """
    return [
        "/usr/bin/ncat",
        "--proxy-type",
        "http",
        "--proxy",
        proxy,
        "--wait",
        str(CONNECTION_TIMEOUT),
        hostname,
        port,
    ]
