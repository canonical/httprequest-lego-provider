# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for SSH proxy selection."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(name="ssh_proxy")
def ssh_proxy_fixture():
    """Load the dependency-free charm module."""
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
        ("http://user:password@proxy.example:3128", "authentication"),
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


def test_ncat_command(ssh_proxy):
    """
    arrange: select a validated HTTP CONNECT proxy.
    act: build the Git SSH proxy command.
    assert: Ncat uses the original SSH destination tokens and a bounded timeout.
    """
    assert ssh_proxy.ncat_command("proxy.example:3128", "%h", "%p") == [
        "/usr/bin/ncat",
        "--proxy-type",
        "http",
        "--proxy",
        "proxy.example:3128",
        "--wait",
        "10",
        "%h",
        "%p",
    ]
