# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Git SSH configuration."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import ops
import pytest
import requests


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
    return module


@pytest.fixture(name="charm")
def charm_fixture(charm_module):
    """Create a mock charm with a connected workload."""
    charm = MagicMock()
    charm.config = {
        "git-repo": "git+ssh://git@github.com/example/zones.git@main",
        "git-ssh-key": "test-key",
    }
    return charm


@pytest.mark.parametrize("bypass", [False, True])
def test_github_known_hosts_uses_proxy(charm_module, charm, monkeypatch, bypass):
    """
    arrange: configure Juju proxies and GitHub metadata.
    act: copy Git SSH files.
    assert: HTTPS replaces ssh-keyscan and respects proxy exclusions.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://proxy.example:3128")
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://proxy.example:3129")
    monkeypatch.setenv("JUJU_CHARM_NO_PROXY", "api.github.com" if bypass else "localhost")
    response = MagicMock()
    response.json.return_value = {"ssh_keys": ["ssh-rsa AAAA", "ssh-ed25519 BBBB"]}
    get = MagicMock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    charm._container.exec.side_effect = AssertionError("Direct SSH must not be used for GitHub")

    charm_module.DjangoCharm._copy_files(charm)

    get.assert_called_once_with(
        "https://api.github.com/meta",
        proxies=(
            {"http": "", "https": "", "all": ""}
            if bypass
            else {
                "http": "http://proxy.example:3128",
                "https": "http://proxy.example:3129",
                "all": "",
            }
        ),
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()
    assert charm._container.push.call_args_list[0].args == (
        charm_module.KNOWN_HOSTS_PATH,
        "github.com ssh-rsa AAAA\ngithub.com ssh-ed25519 BBBB\n",
    )
    assert charm._container.push.call_args_list[1].args == (
        charm_module.RSA_PATH,
        "test-key",
    )


def test_github_without_proxy(charm_module, charm, monkeypatch):
    """
    arrange: configure GitHub without Juju proxies.
    act: copy Git SSH files.
    assert: HTTPS works without proxy settings.
    """
    for scheme in ("HTTP", "HTTPS", "NO"):
        monkeypatch.delenv(f"JUJU_CHARM_{scheme}_PROXY", raising=False)
    response = MagicMock()
    response.json.return_value = {"ssh_keys": ["ssh-ed25519 BBBB"]}
    get = MagicMock(return_value=response)
    monkeypatch.setattr(requests, "get", get)

    charm_module.DjangoCharm._copy_files(charm)

    get.assert_called_once_with(
        "https://api.github.com/meta",
        proxies={"http": "", "https": "", "all": ""},
        timeout=30,
    )
    charm._container.exec.assert_not_called()


@pytest.mark.parametrize("failure", ["http", "empty-keys"])
def test_github_metadata_failure(charm_module, charm, monkeypatch, failure):
    """
    arrange: GitHub returns an HTTP error or no host keys.
    act: copy Git SSH files.
    assert: no SSH files are overwritten and there is no direct SSH fallback.
    """
    response = MagicMock()
    response.json.return_value = {"ssh_keys": []}
    if failure == "http":
        response.raise_for_status.side_effect = requests.HTTPError("Service unavailable")
    monkeypatch.setattr(requests, "get", MagicMock(return_value=response))

    with pytest.raises(requests.HTTPError if failure == "http" else ValueError):
        charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_not_called()
    charm._container.push.assert_not_called()


def test_other_hosts_use_keyscan(charm_module, charm):
    """
    arrange: configure a non-GitHub repository.
    act: copy Git SSH files.
    assert: the existing keyscan behavior and file permissions are retained.
    """
    charm.config["git-repo"] = "git+ssh://git@git.example.com/zones.git"
    charm._container.exec.return_value.wait_output.return_value = ("host-key\n", "")

    charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_called_once_with(["ssh-keyscan", "-t", "rsa", "git.example.com"])
    charm._container.push.assert_any_call(
        charm_module.KNOWN_HOSTS_PATH,
        "host-key\n",
        encoding="utf-8",
        make_dirs=True,
        user=charm_module.DJANGO_USER,
        group=charm_module.DJANGO_GROUP,
        permissions=0o600,
    )


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
