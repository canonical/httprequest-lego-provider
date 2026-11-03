#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import ipaddress
import logging
import os
import re
import typing
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import proxy_bypass_environment  # type: ignore[attr-defined]

import actions
import ops
import paas_app_charmer.django

logger = logging.getLogger(__name__)


DJANGO_USER = "_daemon_"
DJANGO_GROUP = "_daemon_"
KNOWN_HOSTS_PATH = "/var/lib/pebble/default/.ssh/known_hosts"
RSA_PATH = "/var/lib/pebble/default/.ssh/id_rsa"
SSH_CONFIG_PATH = "/etc/ssh/ssh_config.d/httprequest-lego-provider.conf"


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


def _select_proxy(hostname: str, port: int, environment: Mapping[str, str]) -> str:
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


class DjangoCharm(paas_app_charmer.django.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.actions_observer = actions.Observer(self)
        self.framework.observe(self.on.collect_app_status, self._on_collect_app_status)

    def _on_config_changed(self, _event: ops.ConfigChangedEvent) -> None:
        """Config changed handler.

        Args:
            _event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_config_changed(_event)

    def _on_pebble_ready(self, _event: ops.PebbleReadyEvent) -> None:
        """Pebble ready handler.

        Args:
            _event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_pebble_ready(_event)

    def _copy_files(self) -> None:
        """Copy files needed by git."""
        if not self._container.can_connect():
            return
        if not self.config.get("git-repo") or not self.config.get("git-ssh-key"):
            return
        hostname = self.config.get("git-repo").split("@")[1].split("/")[0]
        port = 22
        proxy = _select_proxy(hostname, port, os.environ)
        ssh_directory = str(Path(KNOWN_HOSTS_PATH).parent)
        # Repair ownership on upgrades without replacing any previously trusted keys.
        self._container.exec(
            [
                "sh",
                "-c",
                f"install -d -m 700 -o {DJANGO_USER} -g {DJANGO_GROUP} {ssh_directory}"
                f" && touch {KNOWN_HOSTS_PATH}"
                f" && chown {DJANGO_USER}:{DJANGO_GROUP} {KNOWN_HOSTS_PATH}"
                f" && chmod 600 {KNOWN_HOSTS_PATH}",
            ],
            user="root",
            group="root",
            timeout=10,
        ).wait()
        proxy_command = (
            f"/usr/bin/ncat --proxy-type http --proxy {proxy} --wait 10 %h %p" if proxy else "none"
        )
        self._container.push(
            SSH_CONFIG_PATH,
            f"Host {hostname}\n"
            f"    ProxyCommand {proxy_command}\n"
            f"    IdentityFile {RSA_PATH}\n"
            f"    UserKnownHostsFile {KNOWN_HOSTS_PATH}\n"
            "    StrictHostKeyChecking accept-new\n"
            "    ConnectTimeout 10\n",
            encoding="utf-8",
            make_dirs=True,
            permissions=0o644,
        )
        self._container.push(
            RSA_PATH,
            self.config.get("git-ssh-key"),
            encoding="utf-8",
            make_dirs=True,
            user=DJANGO_USER,
            group=DJANGO_GROUP,
            permissions=0o600,
        )

    def _on_collect_app_status(self, _: ops.CollectStatusEvent) -> None:
        """Handle the status changes."""
        if not self.config.get("git-repo"):
            self.unit.status = ops.WaitingStatus("Config git-repo is required")
            return
        if not self.config.get("git-ssh-key"):
            self.unit.status = ops.WaitingStatus("Config git-ssh-key is required")
            return


if __name__ == "__main__":  # pragma: no cover
    ops.main.main(DjangoCharm)
