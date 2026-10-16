# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Git SSH configuration."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import ops
import pytest


@pytest.fixture(name="charm_module")
def charm_module_fixture(monkeypatch):
    """Load charm-specific code without build-time framework charm libraries."""
    framework = ModuleType("paas_app_charmer")
    django = ModuleType("paas_app_charmer.django")
    django.Charm = ops.CharmBase
    framework.django = django
    monkeypatch.setitem(sys.modules, "paas_app_charmer", framework)
    monkeypatch.setitem(sys.modules, "paas_app_charmer.django", django)
    path = Path(__file__).parents[2] / "src" / "charm.py"
    monkeypatch.syspath_prepend(str(path.parent))
    spec = importlib.util.spec_from_file_location("charm_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scheme in ("HTTP", "HTTPS", "NO"):
        monkeypatch.delenv(f"JUJU_CHARM_{scheme}_PROXY", raising=False)
    return module


@pytest.fixture(name="charm")
def charm_fixture(charm_module):
    """Create a mock charm with a connected workload."""
    charm = MagicMock()
    charm.config = {
        "git-repo": "git+ssh://git@github.com/example/zones.git@main",
        "git-ssh-key": "test-key",
    }
    charm._container.exec.return_value.wait_output.return_value = (
        "github.com ssh-rsa AAAA\n",
        "",
    )
    return charm


@pytest.mark.parametrize("hostname", ["github.com", "git.example.com"])
@pytest.mark.parametrize("bypass", [False, True])
def test_scan_and_git_use_same_proxy(charm_module, charm, monkeypatch, hostname, bypass):
    """
    arrange: configure Juju proxies and an optional destination exclusion.
    act: copy Git SSH files.
    assert: scanning and subsequent Git SSH use the same route for any host.
    """
    charm.config["git-repo"] = f"git+ssh://git@{hostname}/example/zones.git@main"
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://http-proxy.example:3128")
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://https-proxy.example:3129")
    monkeypatch.setenv("JUJU_CHARM_NO_PROXY", hostname if bypass else "localhost")

    charm_module.DjangoCharm._copy_files(charm)

    proxy = "" if bypass else "https-proxy.example:3129"
    charm._container.exec.assert_called_once_with(
        ["python3", charm_module.SCAN_SCRIPT_PATH, f"ssh://{hostname}:22", proxy],
        user=charm_module.DJANGO_USER,
        group=charm_module.DJANGO_GROUP,
        timeout=45,
    )
    pushes = {call.args[0]: call for call in charm._container.push.call_args_list}
    config = pushes[charm_module.SSH_CONFIG_PATH].args[1]
    assert f"Host {hostname}\n" in config
    assert f"IdentityFile {charm_module.RSA_PATH}\n" in config
    assert f"UserKnownHostsFile {charm_module.KNOWN_HOSTS_PATH}\n" in config
    assert "StrictHostKeyChecking yes\n" in config
    assert "ConnectTimeout 10\n" in config
    if bypass:
        assert "ProxyCommand none\n" in config
    else:
        assert (
            "ProxyCommand /usr/bin/ncat --proxy-type http --proxy "
            "https-proxy.example:3129 --wait 10 %h %p\n"
        ) in config
    assert pushes[charm_module.SSH_CONFIG_PATH].kwargs["permissions"] == 0o644
    for path in (charm_module.KNOWN_HOSTS_PATH, charm_module.RSA_PATH):
        assert pushes[path].kwargs == {
            "encoding": "utf-8",
            "make_dirs": True,
            "user": charm_module.DJANGO_USER,
            "group": charm_module.DJANGO_GROUP,
            "permissions": 0o600,
        }
    assert pushes[charm_module.RSA_PATH].args[1] == "test-key"


def test_proxy_removal_restores_direct_ssh(charm_module, charm, monkeypatch):
    """
    arrange: a proxy is configured and then removed.
    act: regenerate the SSH files after each configuration change.
    assert: the previously configured ProxyCommand is replaced with direct access.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://proxy.example:3128")
    charm_module.DjangoCharm._copy_files(charm)
    monkeypatch.delenv("JUJU_CHARM_HTTPS_PROXY")
    charm._container.reset_mock()

    charm_module.DjangoCharm._copy_files(charm)

    assert charm._container.exec.call_args.args[0][-1] == ""
    config_call = next(
        call
        for call in charm._container.push.call_args_list
        if call.args[0] == charm_module.SSH_CONFIG_PATH
    )
    assert "ProxyCommand none\n" in config_call.args[1]
    assert "ncat" not in config_call.args[1]


@pytest.mark.parametrize("failure", ["scan-error", "empty-keys"])
def test_scan_failure_preserves_ssh_files(charm_module, charm, monkeypatch, failure):
    """
    arrange: a proxied scan fails or returns no keys.
    act: copy Git SSH files.
    assert: only the scan helper is written, with no API or direct fallback.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://proxy.example:3128")
    if failure == "scan-error":
        charm._container.exec.return_value.wait_output.side_effect = RuntimeError("CONNECT denied")
    else:
        charm._container.exec.return_value.wait_output.return_value = ("", "")

    with pytest.raises(RuntimeError):
        charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_called_once()
    assert [call.args[0] for call in charm._container.push.call_args_list] == [
        charm_module.SCAN_SCRIPT_PATH
    ]


def test_invalid_proxy_does_not_write_files(charm_module, charm, monkeypatch):
    """
    arrange: an unsupported authenticated proxy is configured.
    act: copy Git SSH files.
    assert: an explicit error is raised before starting a scan or changing files.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://user:password@proxy.example:3128")

    with pytest.raises(ValueError, match="authentication is unsupported"):
        charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_not_called()
    charm._container.push.assert_not_called()


@pytest.mark.parametrize("proxy", ["", "http://[2001:db8::1]:3128"])
def test_generated_ssh_config(charm_module, charm, monkeypatch, tmp_path, proxy):
    """
    arrange: configure the standard SSH port and an optional IPv6 proxy.
    act: generate the system SSH include and read it with OpenSSH.
    assert: Git SSH sees strict verification, the correct files, and the selected route.
    """
    charm.config["git-repo"] = "git+ssh://git@git.example.com/zones.git@main"
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", proxy)
    charm_module.DjangoCharm._copy_files(charm)
    config_call = next(
        call
        for call in charm._container.push.call_args_list
        if call.args[0] == charm_module.SSH_CONFIG_PATH
    )
    included = tmp_path / "managed.conf"
    included.write_text(config_call.args[1])
    config = tmp_path / "ssh_config"
    config.write_text(f"Include {included}\nHost *\n")

    result = subprocess.run(
        ["ssh", "-G", "-F", str(config), "git.example.com"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )

    assert f"identityfile {charm_module.RSA_PATH}\n" in result.stdout
    assert f"userknownhostsfile {charm_module.KNOWN_HOSTS_PATH}\n" in result.stdout
    assert "stricthostkeychecking true\n" in result.stdout
    assert "port 22\n" in result.stdout
    if proxy:
        assert (
            "proxycommand /usr/bin/ncat --proxy-type http --proxy [2001:db8::1]:3128 "
            "--wait 10 %h %p\n"
        ) in result.stdout
    else:
        assert "proxycommand" not in result.stdout
    assert charm._container.exec.call_args.args[0][2] == "ssh://git.example.com:22"


@pytest.mark.parametrize("missing", ["container", "git-repo", "git-ssh-key"])
def test_copy_files_not_ready(charm_module, charm, missing):
    """
    arrange: the container or required configuration is unavailable.
    act: attempt to copy Git SSH files.
    assert: no commands run and no files are written.
    """
    if missing == "container":
        charm._container.can_connect.return_value = False
    else:
        charm.config[missing] = ""

    charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_not_called()
    charm._container.push.assert_not_called()
