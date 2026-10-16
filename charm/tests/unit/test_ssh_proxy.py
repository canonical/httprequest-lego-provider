# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for proxy selection and the managed SSH scan relay."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture(name="ssh_proxy")
def ssh_proxy_fixture():
    """Load the dependency-free module used by both the charm and workload."""
    path = Path(__file__).parents[2] / "src" / "ssh_proxy.py"
    spec = importlib.util.spec_from_file_location("ssh_proxy_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "hostname",
    [
        "bad;host",
        "%h",
        "-oProxyCommand=bad",
        "host:2222",
        "fe80::1%eth0",
        "host\nHost *",
    ],
)
def test_invalid_hostname(ssh_proxy, hostname):
    """
    arrange: an SSH destination is invalid or unsafe in SSH configuration.
    act: select the proxy route.
    assert: it is rejected rather than interpolated into a command.
    """
    with pytest.raises(ValueError):
        ssh_proxy.select_proxy(hostname, 22, {})


@pytest.mark.parametrize(
    "environment,expected",
    [
        ({}, ""),
        ({"HTTP_PROXY": "http://ambient:1", "ALL_PROXY": "socks5://ambient:2"}, ""),
        ({"JUJU_CHARM_HTTP_PROXY": "http://proxy.example:3128"}, "proxy.example:3128"),
        (
            {
                "JUJU_CHARM_HTTP_PROXY": "http://http.example:3128",
                "JUJU_CHARM_HTTPS_PROXY": "http://https.example:3129",
            },
            "https.example:3129",
        ),
        ({"JUJU_CHARM_HTTPS_PROXY": "http://proxy.example/"}, "proxy.example:80"),
        ({"JUJU_CHARM_HTTPS_PROXY": "http://[2001:db8::1]:3128"}, "[2001:db8::1]:3128"),
    ],
)
def test_proxy_selection(ssh_proxy, environment, expected):
    """
    arrange: Juju or unrelated ambient proxy settings are present.
    act: select the SSH proxy.
    assert: Juju HTTPS takes precedence over HTTP, without ambient fallbacks.
    """
    assert ssh_proxy.select_proxy("github.com", 22, environment) == expected


@pytest.mark.parametrize(
    "hostname,port,no_proxy,bypass",
    [
        ("github.com", 22, "*", True),
        ("github.com", 22, "localhost, *", True),
        ("github.com", 22, "localhost, github.com", True),
        ("github.com", 22, ".github.com", True),
        ("github.com", 22, "GitHub.COM", True),
        ("git.example.com", 22, "example.com", True),
        ("git.example.com.", 22, "example.com", True),
        ("git.example.com", 22, ".example.com:22", True),
        ("notexample.com", 22, "example.com", False),
        ("git.example.com", 22, "git.example.com:22", True),
        ("git.example.com", 2222, "git.example.com:22", False),
        ("192.0.2.1", 22, "192.0.2.0/24", True),
        ("192.0.3.1", 22, "192.0.2.0/24", False),
        ("2001:db8::1", 22, "2001:db8::/32", True),
        ("2001:db8::1", 22, "2001:db8::1", True),
        ("2001:db8::1", 22, "2001:DB8::1", True),
        ("2001:db8::1", 22, "[2001:db8::1]:22", True),
        ("2001:db8::1", 2222, "[2001:db8::1]:22", False),
    ],
)
def test_proxy_exclusions(ssh_proxy, hostname, port, no_proxy, bypass):
    """
    arrange: domain, port, wildcard, or IP exclusions are configured.
    act: select the route to the Git destination.
    assert: exclusions apply to the SSH host and port, not an API endpoint.
    """
    environment = {
        "JUJU_CHARM_HTTPS_PROXY": "http://proxy.example:3128",
        "JUJU_CHARM_NO_PROXY": no_proxy,
    }
    assert ssh_proxy.select_proxy(hostname, port, environment) == (
        "" if bypass else "proxy.example:3128"
    )


def test_proxy_exclusions_use_explicit_settings(ssh_proxy, monkeypatch):
    """
    arrange: standard-library proxy matching is available alongside ambient exclusions.
    act: check a destination using Juju exclusions.
    assert: matching delegates to the standard library with explicit host, port, and settings.
    """
    monkeypatch.setenv("NO_PROXY", "*")
    bypass = MagicMock(return_value=True)
    monkeypatch.setattr(ssh_proxy, "proxy_bypass_environment", bypass)

    assert ssh_proxy._bypass_proxy("git.example.com.", 22, ".example.com")

    bypass.assert_called_once_with("git.example.com:22", {"no": ".example.com"})


@pytest.mark.parametrize(
    "proxy,match",
    [
        ("https://proxy.example:3128", "other proxy schemes"),
        ("socks5://proxy.example:1080", "other proxy schemes"),
        ("proxy.example:3128", "other proxy schemes"),
        ("http://user:secret@proxy.example:3128", "authentication"),
        ("http://proxy.example:0", "port"),
        ("http://proxy.example:65536", "Port"),
        ("http://proxy.example/path", "path"),
        ("http://proxy.example?query", "query"),
        ("http://proxy.example#fragment", "fragment"),
        ("http://bad;host:3128", "DNS names"),
        ("http://%h:3128", "expansion tokens"),
    ],
)
def test_unsupported_proxy(ssh_proxy, proxy, match):
    """
    arrange: the selected proxy cannot safely be used by Ncat HTTP CONNECT.
    act: select the SSH route.
    assert: a clear error is raised instead of ignoring the proxy.
    """
    with pytest.raises(ValueError, match=match):
        ssh_proxy.select_proxy("github.com", 22, {"JUJU_CHARM_HTTPS_PROXY": proxy})


def test_exclusion_bypasses_unsupported_proxy(ssh_proxy):
    """
    arrange: an excluded Git host has an otherwise unsupported proxy configured.
    act: select the route.
    assert: the excluded destination still uses direct access.
    """
    assert (
        ssh_proxy.select_proxy(
            "github.com",
            22,
            {"JUJU_CHARM_HTTPS_PROXY": "https://proxy.example", "JUJU_CHARM_NO_PROXY": "*"},
        )
        == ""
    )


def test_direct_keyscan(ssh_proxy, monkeypatch):
    """
    arrange: no proxy applies.
    act: scan host keys.
    assert: ssh-keyscan runs directly with bounded connection and overall timeouts.
    """
    run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="host ssh-rsa AAAA\n"))
    monkeypatch.setattr(ssh_proxy.subprocess, "run", run)

    assert ssh_proxy.scan_host_keys("host", 2222, "") == "host ssh-rsa AAAA\n"

    run.assert_called_once_with(
        ["/usr/bin/ssh-keyscan", "-T", "10", "-t", "rsa", "-p", "2222", "host"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("returncode,output", [(1, ""), (0, "")])
def test_failed_direct_scan(ssh_proxy, monkeypatch, returncode, output):
    """
    arrange: the direct scan fails or returns no keys.
    act: discover host keys.
    assert: an explicit error is raised.
    """
    monkeypatch.setattr(
        ssh_proxy.subprocess,
        "run",
        MagicMock(
            return_value=SimpleNamespace(returncode=returncode, stdout=output, stderr="denied")
        ),
    )
    with pytest.raises(RuntimeError):
        ssh_proxy.scan_host_keys("host", 22, "")


@pytest.mark.parametrize(
    "hostname,port,host_field",
    [
        ("git.example.com", 22, "git.example.com"),
        ("git.example.com", 2222, "[git.example.com]:2222"),
        ("2001:db8::1", 22, "2001:db8::1"),
        ("2001:db8::1", 2222, "[2001:db8::1]:2222"),
    ],
)
def test_proxy_keyscan_rewrites_host(ssh_proxy, monkeypatch, hostname, port, host_field):
    """
    arrange: ssh-keyscan returns keys for a dynamically allocated loopback port.
    act: run a proxied scan.
    assert: only original destination identities are written to known_hosts.
    """
    scan = MagicMock(returncode=0)

    def start_scan(command, stdout, stderr):
        assert command[:6] == ["/usr/bin/ssh-keyscan", "-T", "10", "-t", "rsa", "-p"]
        assert command[-1] == "127.0.0.1"
        stdout.write(f"# comment\n[127.0.0.1]:{command[-2]} ssh-rsa AAAA\n")
        return scan

    serve = MagicMock()
    monkeypatch.setattr(ssh_proxy.subprocess, "Popen", start_scan)
    monkeypatch.setattr(ssh_proxy, "_serve_scan", serve)

    assert ssh_proxy.scan_host_keys(hostname, port, "proxy.example:3128") == (
        f"{host_field} ssh-rsa AAAA\n"
    )

    listener, actual_scan, command, _ = serve.call_args.args
    assert listener.fileno() == -1
    assert actual_scan is scan
    assert command == ssh_proxy.ncat_command("proxy.example:3128", hostname, str(port))


@pytest.mark.parametrize("failure", ["denied", "empty", "wrong-host"])
def test_proxy_scan_failure_has_no_direct_fallback(ssh_proxy, monkeypatch, failure):
    """
    arrange: the proxy scan fails, returns no keys, or has an unexpected host label.
    act: scan through the proxy.
    assert: it raises with diagnostics and never starts a direct scan.
    """
    scan = MagicMock(returncode=1 if failure == "denied" else 0)

    def start_scan(command, stdout, stderr):
        stderr.write("HTTP CONNECT denied")
        if failure == "wrong-host":
            stdout.write("wrong-host ssh-rsa AAAA\n")
        return scan

    run = MagicMock()
    monkeypatch.setattr(ssh_proxy.subprocess, "Popen", start_scan)
    monkeypatch.setattr(ssh_proxy.subprocess, "run", run)
    monkeypatch.setattr(ssh_proxy, "_serve_scan", MagicMock())

    with pytest.raises(
        RuntimeError, match="CONNECT denied" if failure == "denied" else "host key"
    ):
        ssh_proxy.scan_host_keys("host", 22, "proxy.example:3128")

    run.assert_not_called()


def test_relay_lifecycle(ssh_proxy, monkeypatch):
    """
    arrange: a scan connects twice to the already-bound loopback listener.
    act: serve the scan through Ncat.
    assert: each accepted socket is forwarded, then all children and sockets are closed.
    """
    scan = MagicMock()
    scan.poll.side_effect = [None, None, 0, 0]
    listener = MagicMock()
    connections = [MagicMock(), MagicMock()]
    listener.accept.side_effect = [(connection, ("127.0.0.1", 1)) for connection in connections]
    relays = [MagicMock(), MagicMock()]
    for relay in relays:
        relay.poll.return_value = None
    start = MagicMock(side_effect=relays)
    monkeypatch.setattr(ssh_proxy.subprocess, "Popen", start)
    command = ssh_proxy.ncat_command("proxy.example:3128", "host", "22")
    errors = MagicMock()

    ssh_proxy._serve_scan(listener, scan, command, errors)

    for call, connection in zip(start.call_args_list, connections):
        assert call.args == (command,)
        assert call.kwargs == {
            "stdin": connection.fileno(),
            "stdout": connection.fileno(),
            "stderr": errors,
        }
        connection.__exit__.assert_called_once()
    for relay in relays:
        relay.terminate.assert_called_once()
        relay.wait.assert_called_once_with(timeout=1)
    scan.wait.assert_called_once_with(timeout=1)


def test_relay_deadline_cleans_up(ssh_proxy, monkeypatch):
    """
    arrange: a scan hangs beyond its deadline.
    act: serve the scan.
    assert: the timeout is explicit and the scan child is reaped.
    """
    scan = MagicMock()
    scan.poll.return_value = None
    monkeypatch.setattr(ssh_proxy.time, "monotonic", MagicMock(side_effect=[0, 31]))

    with pytest.raises(TimeoutError, match="timed out"):
        ssh_proxy._serve_scan(MagicMock(), scan, [], MagicMock())

    scan.terminate.assert_called_once()
    scan.wait.assert_called_once_with(timeout=1)


def test_relay_waits_for_scan_connection(ssh_proxy):
    """
    arrange: the scan has not connected during the first listener poll.
    act: wait for the scan to finish.
    assert: the short accept timeout does not end the scan or escape cleanup.
    """
    scan = MagicMock()
    scan.poll.side_effect = [None, 0, 0]
    listener = MagicMock()
    listener.accept.side_effect = TimeoutError

    ssh_proxy._serve_scan(listener, scan, [], MagicMock())

    listener.settimeout.assert_called_once_with(ssh_proxy.RELAY_POLL_INTERVAL)
    scan.wait.assert_called_once_with(timeout=1)
    scan.terminate.assert_not_called()


def test_child_start_failure_cleans_up(ssh_proxy, monkeypatch):
    """
    arrange: starting Ncat fails after the scan has started.
    act: accept a relay connection.
    assert: both the accepted socket and scan child are cleaned up.
    """
    scan = MagicMock()
    scan.poll.return_value = None
    listener = MagicMock()
    connection = MagicMock()
    listener.accept.return_value = (connection, ("127.0.0.1", 1))
    monkeypatch.setattr(
        ssh_proxy.subprocess, "Popen", MagicMock(side_effect=OSError("missing ncat"))
    )

    with pytest.raises(OSError, match="missing ncat"):
        ssh_proxy._serve_scan(listener, scan, [], MagicMock())

    connection.__exit__.assert_called_once()
    scan.terminate.assert_called_once()
    scan.wait.assert_called_once_with(timeout=1)


def test_stubborn_child_is_killed(ssh_proxy):
    """
    arrange: a child ignores termination.
    act: stop the child.
    assert: it is killed and reaped after a bounded wait.
    """
    process = MagicMock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("ncat", 1), 0]

    ssh_proxy._stop_process(process)

    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.wait.call_count == 2


@pytest.mark.parametrize(
    "destination,proxy,expected",
    [
        ("ssh://git.example.com", "", ("git.example.com", 22, "")),
        (
            "ssh://git.example.com:2222",
            "proxy.example:3128",
            ("git.example.com", 2222, "proxy.example:3128"),
        ),
        (
            "ssh://[2001:db8::1]:2222",
            "[2001:db8::2]:3128",
            ("2001:db8::1", 2222, "[2001:db8::2]:3128"),
        ),
    ],
)
def test_validate_inputs(ssh_proxy, destination, proxy, expected):
    """
    arrange: the helper receives a combined SSH destination and optional proxy.
    act: parse and validate the inputs separately from scanning.
    assert: the validated hostname, port, and proxy are returned.
    """
    assert ssh_proxy.validate_inputs(destination, proxy) == expected


@pytest.mark.parametrize(
    "destination,proxy",
    [
        ("https://git.example.com:22", ""),
        ("ssh://", ""),
        ("ssh://user@git.example.com", ""),
        ("ssh://git.example.com/path", ""),
        ("ssh://git.example.com?query", ""),
        ("ssh://git.example.com#fragment", ""),
        ("ssh://git.example.com:0", ""),
        ("ssh://git.example.com:65536", ""),
        ("ssh://git.example.com:invalid", ""),
        ("ssh://[invalid]:22", ""),
        ("ssh://bad;host:22", ""),
        ("ssh://%h:22", ""),
        ("ssh://git.example.com:22", "bad;proxy:3128"),
        ("ssh://git.example.com:22", "proxy.example:65536"),
        ("ssh://git.example.com:22", "proxy.example/path"),
        ("ssh://git.example.com:22", "user@proxy.example:3128"),
    ],
)
def test_validate_inputs_rejects_invalid_values(ssh_proxy, destination, proxy):
    """
    arrange: an invalid destination or proxy is supplied to the helper.
    act: validate the inputs.
    assert: no scan starts and invalid input raises an explicit error.
    """
    with pytest.raises(ValueError):
        ssh_proxy.validate_inputs(destination, proxy)


def test_main_validates_scans_and_prints(ssh_proxy, monkeypatch, capsys):
    """
    arrange: the helper receives a valid destination and proxy from the command line.
    act: run the entry point.
    assert: validation completes before scanning and the returned keys are printed unchanged.
    """
    monkeypatch.setattr(
        sys, "argv", ["scan_host_keys.py", "ssh://git.example.com:22", "proxy.example:3128"]
    )
    scan = MagicMock(return_value="git.example.com ssh-rsa AAAA\n")
    monkeypatch.setattr(ssh_proxy, "scan_host_keys", scan)

    ssh_proxy.main()

    scan.assert_called_once_with("git.example.com", 22, "proxy.example:3128")
    assert capsys.readouterr().out == "git.example.com ssh-rsa AAAA\n"


def test_main_does_not_scan_invalid_inputs(ssh_proxy, monkeypatch, capsys):
    """
    arrange: the helper receives an invalid destination port.
    act: run the entry point.
    assert: validation fails before scanning or printing output.
    """
    monkeypatch.setattr(sys, "argv", ["scan_host_keys.py", "ssh://git.example.com:0"])
    scan = MagicMock()
    monkeypatch.setattr(ssh_proxy, "scan_host_keys", scan)

    with pytest.raises(ValueError, match="port"):
        ssh_proxy.main()

    scan.assert_not_called()
    assert capsys.readouterr().out == ""
