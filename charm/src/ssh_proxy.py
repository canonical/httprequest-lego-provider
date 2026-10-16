# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Select an SSH proxy and scan host keys through a short-lived Ncat relay."""

# Children are reaped explicitly: Popen context managers can wait indefinitely on exit.
# pylint: disable=consider-using-with
# Subprocesses use fixed executables and validated argument lists, without a shell.

import argparse
import ipaddress
import re
import socket
import subprocess  # nosec B404
import time
from collections.abc import Mapping
from tempfile import TemporaryFile
from typing import TextIO
from urllib.parse import urlsplit

SCAN_TIMEOUT = 30
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
    destination = f"{address}:{port}"
    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        host_ip = None
    for exclusion in no_proxy.split(","):
        exclusion = exclusion.strip().lower().lstrip(".")
        if exclusion == "*" or exclusion in (hostname, address, destination):
            return True
        if host_ip is None:
            if exclusion and (
                hostname.endswith(f".{exclusion}") or destination.endswith(f".{exclusion}")
            ):
                return True
            continue
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
    """Build the same Ncat command for scanning and Git SSH.

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


def _stop_process(process: subprocess.Popen) -> None:
    """Reap a child, terminating it if it is still running.

    Args:
        process: The scan or relay child.
    """
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _serve_scan(
    listener: socket.socket,
    scan: subprocess.Popen,
    command: list[str],
    errors: TextIO,
) -> None:
    """Forward scan connections through Ncat and always reap all children.

    Args:
        listener: The bound loopback listener.
        scan: The running ssh-keyscan process.
        command: The Ncat CONNECT command.
        errors: The file receiving relay diagnostics.

    Raises:
        TimeoutError: If the overall scan deadline expires.
    """
    relays = []
    deadline = time.monotonic() + SCAN_TIMEOUT
    listener.settimeout(0.1)
    try:
        while scan.poll() is None:
            if time.monotonic() >= deadline:
                raise TimeoutError("SSH host-key scan through the HTTP proxy timed out")
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            with connection:
                relay = subprocess.Popen(  # nosec B603
                    command,
                    stdin=connection.fileno(),
                    stdout=connection.fileno(),
                    stderr=errors,
                )
                relays.append(relay)
    finally:
        _stop_process(scan)
        for relay in relays:
            _stop_process(relay)


def _scan_via_proxy(hostname: str, port: int, proxy: str) -> str:
    """Run ssh-keyscan against a private loopback relay.

    Args:
        hostname: The Git host.
        port: The SSH port.
        proxy: The validated HTTP CONNECT proxy address.

    Returns:
        Host keys with the original destination name, not the loopback address.

    Raises:
        RuntimeError: If the scan fails or returns unexpected host keys.
    """
    with (
        socket.socket() as listener,
        TemporaryFile(mode="w+") as output,
        TemporaryFile(mode="w+") as errors,
    ):
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        local_port = listener.getsockname()[1]
        command = [
            "/usr/bin/ssh-keyscan",
            "-T",
            "10",
            "-t",
            "rsa",
            "-p",
            str(local_port),
            "127.0.0.1",
        ]
        scan = subprocess.Popen(command, stdout=output, stderr=errors)  # nosec B603
        _serve_scan(listener, scan, ncat_command(proxy, hostname, str(port)), errors)
        output.seek(0)
        errors.seek(0)
        if scan.returncode:
            raise RuntimeError(f"SSH host-key scan through the HTTP proxy failed: {errors.read()}")
        destination = hostname if port == 22 else f"[{hostname}]:{port}"
        keys = []
        for line in output:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 3 or fields[0] != f"[127.0.0.1]:{local_port}":
                raise RuntimeError("SSH host-key scan returned an unexpected host key")
            keys.append(f"{destination} {fields[1]} {fields[2]}\n")
        return "".join(keys)


def scan_host_keys(hostname: str, port: int, proxy: str) -> str:
    """Discover SSH host keys, without a direct fallback when a proxy is set.

    Args:
        hostname: The Git host.
        port: The SSH port.
        proxy: The HTTP CONNECT proxy address, or an empty string for direct access.

    Returns:
        Nonempty known_hosts file content.

    Raises:
        RuntimeError: If no host keys are discovered or the scan fails.
        ValueError: If the SSH destination is invalid.
    """
    _validate_hostname(hostname)
    if not 1 <= port <= 65535:
        raise ValueError("The Git SSH port must be between 1 and 65535")
    if proxy:
        output = _scan_via_proxy(hostname, port, proxy)
    else:
        result = subprocess.run(  # nosec B603
            ["/usr/bin/ssh-keyscan", "-T", "10", "-t", "rsa", "-p", str(port), hostname],
            capture_output=True,
            text=True,
            timeout=SCAN_TIMEOUT,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Direct SSH host-key scan failed: {result.stderr}")
        output = result.stdout
    if not output.strip():
        raise RuntimeError("SSH host-key scan returned no host keys")
    return output


def main() -> None:
    """Run the workload-side host-key scan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hostname")
    parser.add_argument("port", type=int)
    parser.add_argument("proxy", nargs="?", default="")
    args = parser.parse_args()
    print(scan_host_keys(args.hostname, args.port, args.proxy), end="")


if __name__ == "__main__":
    main()
