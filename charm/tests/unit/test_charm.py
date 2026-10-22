# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Git SSH configuration."""

import grp
import importlib.util
import os
import pwd
import shutil
import socketserver
import stat
import subprocess
import sys
import threading
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
def charm_fixture():
    """Create a mock charm with a connected workload."""
    charm = MagicMock()
    charm.config = {
        "git-repo": "git+ssh://git@github.com/example/zones.git@main",
        "git-ssh-key": "test-key",
    }
    return charm


@pytest.mark.parametrize("hostname", ["github.com", "git.example.com"])
@pytest.mark.parametrize("bypass", [False, True])
@pytest.mark.parametrize("scheme", ["http", "https"])
def test_git_proxy_configuration(charm_module, charm, monkeypatch, hostname, bypass, scheme):
    """
    arrange: configure Juju proxies and an optional destination exclusion.
    act: copy Git SSH files.
    assert: Git uses the selected route and accepts only previously unknown host keys.
    """
    charm.config["git-repo"] = f"git+ssh://git@{hostname}/example/zones.git@main"
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://http-proxy.example:3128")
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", f"{scheme}://https-proxy.example:3129")
    monkeypatch.setenv("JUJU_CHARM_NO_PROXY", hostname if bypass else "localhost")

    charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_called_once_with(
        [
            "sh",
            "-c",
            "install -d -m 700 -o _daemon_ -g _daemon_ /var/lib/pebble/default/.ssh"
            " && touch /var/lib/pebble/default/.ssh/known_hosts"
            " && chown _daemon_:_daemon_ /var/lib/pebble/default/.ssh/known_hosts"
            " && chmod 600 /var/lib/pebble/default/.ssh/known_hosts",
        ],
        user="root",
        group="root",
        timeout=10,
    )
    charm._container.exec.return_value.wait.assert_called_once_with()
    pushes = {call.args[0]: call for call in charm._container.push.call_args_list}
    assert set(pushes) == {charm_module.SSH_CONFIG_PATH, charm_module.RSA_PATH}
    config = pushes[charm_module.SSH_CONFIG_PATH].args[1]
    assert f"Host {hostname}\n" in config
    assert f"IdentityFile {charm_module.RSA_PATH}\n" in config
    assert f"UserKnownHostsFile {charm_module.KNOWN_HOSTS_PATH}\n" in config
    assert "StrictHostKeyChecking accept-new\n" in config
    assert "ConnectTimeout 10\n" in config
    if bypass:
        assert "ProxyCommand none\n" in config
    elif scheme == "http":
        assert (
            "ProxyCommand /usr/bin/ncat --proxy-type http --proxy "
            "https-proxy.example:3129 --wait 10 %h %p\n"
        ) in config
    else:
        assert (
            "ProxyCommand /usr/bin/proxytunnel --encrypt-proxy --proxy "
            "https-proxy.example:3129 --dest %h:%p\n"
        ) in config
        assert "--no-check-certificate" not in config
    assert pushes[charm_module.SSH_CONFIG_PATH].kwargs["permissions"] == 0o644
    assert pushes[charm_module.RSA_PATH].kwargs == {
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

    config_call = next(
        call
        for call in charm._container.push.call_args_list
        if call.args[0] == charm_module.SSH_CONFIG_PATH
    )
    assert "ProxyCommand none\n" in config_call.args[1]
    assert "ncat" not in config_call.args[1]


def test_known_hosts_setup_failure_is_explicit(charm_module, charm):
    """
    arrange: preparing writable host-key storage fails.
    act: copy Git SSH files.
    assert: the failure propagates before changing the SSH configuration or identity.
    """
    charm._container.exec.return_value.wait.side_effect = RuntimeError("Permission denied")

    with pytest.raises(RuntimeError, match="Permission denied"):
        charm_module.DjangoCharm._copy_files(charm)

    charm._container.push.assert_not_called()


@pytest.mark.parametrize("existing", [False, True])
def test_known_hosts_survives_hooks(charm_module, charm, monkeypatch, tmp_path, existing):
    """
    arrange: SSH storage is absent or contains trusted keys from an earlier deployment.
    act: prepare storage and repeat configuration and workload-ready hooks.
    assert: keys survive and the directory and file remain private and writable.
    """
    directory = tmp_path / ".ssh"
    known_hosts = directory / "known_hosts"
    original = "github.com ssh-ed25519 AAAA\nold.example ssh-rsa BBBB\n"
    if existing:
        directory.mkdir(mode=0o755)
        known_hosts.write_text(original)
        known_hosts.chmod(0o644)
    monkeypatch.setattr(charm_module, "KNOWN_HOSTS_PATH", str(known_hosts))
    monkeypatch.setattr(charm_module, "DJANGO_USER", pwd.getpwuid(os.getuid()).pw_name)
    monkeypatch.setattr(charm_module, "DJANGO_GROUP", grp.getgrgid(os.getgid()).gr_name)

    def execute(command, **_kwargs):
        subprocess.run(command, check=True, capture_output=True, timeout=5)
        return MagicMock()

    charm._container.exec.side_effect = execute
    copy_files = charm_module.DjangoCharm._copy_files
    charm._copy_files.side_effect = lambda: copy_files(charm)
    copy_files(charm)
    assert known_hosts.read_text() == (original if existing else "")
    with known_hosts.open("a") as stream:
        stream.write("new.example ssh-ed25519 CCCC\n")
    expected = known_hosts.read_bytes()

    for hook in ("_on_config_changed", "_on_pebble_ready"):
        charm.config["git-ssh-key"] = f"updated-key-for-{hook}"
        monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://updated-proxy.example:3128")
        base_hook = MagicMock()
        monkeypatch.setattr(ops.CharmBase, hook, base_hook, raising=False)
        # Use the actual subclass so super() in the hook resolves the mocked base.
        instance = object.__new__(charm_module.DjangoCharm)
        monkeypatch.setattr(
            charm_module.DjangoCharm, "_copy_files", lambda _self: charm._copy_files()
        )
        event = MagicMock()
        getattr(instance, hook)(event)
        base_hook.assert_called_once_with(event)
        assert known_hosts.read_bytes() == expected

    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(known_hosts.stat().st_mode) == 0o600
    assert directory.stat().st_uid == known_hosts.stat().st_uid == os.getuid()
    assert directory.stat().st_gid == known_hosts.stat().st_gid == os.getgid()
    assert os.access(directory, os.W_OK)
    assert os.access(known_hosts, os.W_OK)
    assert all(call.args[0] != str(known_hosts) for call in charm._container.push.call_args_list)


def test_invalid_proxy_does_not_write_files(charm_module, charm, monkeypatch):
    """
    arrange: an unsupported authenticated proxy is configured.
    act: copy Git SSH files.
    assert: an explicit error is raised before changing files.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "http://user:password@proxy.example:3128")

    with pytest.raises(ValueError, match="authentication is unsupported"):
        charm_module.DjangoCharm._copy_files(charm)

    charm._container.exec.assert_not_called()
    charm._container.push.assert_not_called()


@pytest.mark.parametrize("proxy", ["", "http://[2001:db8::1]:3128", "https://[2001:db8::1]:3129"])
def test_generated_ssh_config(charm_module, charm, monkeypatch, tmp_path, proxy):
    """
    arrange: configure the standard SSH port and an optional IPv6 proxy.
    act: generate the system SSH include and read it with OpenSSH.
    assert: Git SSH sees accept-new verification, the correct files, and the selected route.
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
    assert "stricthostkeychecking accept-new\n" in result.stdout
    assert "port 22\n" in result.stdout
    if proxy.startswith("https://"):
        assert (
            "proxycommand /usr/bin/proxytunnel --encrypt-proxy --proxy "
            "[2001:db8::1]:3129 --dest %h:%p\n"
        ) in result.stdout
    elif proxy:
        assert (
            "proxycommand /usr/bin/ncat --proxy-type http --proxy [2001:db8::1]:3128 "
            "--wait 10 %h %p\n"
        ) in result.stdout
    else:
        assert "proxycommand" not in result.stdout


@pytest.mark.parametrize(
    "proxy,normalized",
    [
        ("http://proxy.example", "http://proxy.example:80"),
        ("https://proxy.example", "https://proxy.example:443"),
        ("http://proxy.example:443", "http://proxy.example:443"),
        ("https://proxy.example:80", "https://proxy.example:80"),
        ("https://proxy.example:8443/", "https://proxy.example:8443"),
        ("https://[2001:db8::1]", "https://[2001:db8::1]:443"),
    ],
)
def test_proxy_ports(charm_module, charm, monkeypatch, proxy, normalized):
    """
    arrange: a proxy URL has an explicit port or relies on its scheme's default.
    act: validate the URL and generate the SSH configuration.
    assert: the selected transport uses the correct explicit port.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", proxy)
    assert charm_module._select_proxy("github.com", 22, os.environ) == normalized

    charm_module.DjangoCharm._copy_files(charm)

    config = next(
        call.args[1]
        for call in charm._container.push.call_args_list
        if call.args[0] == charm_module.SSH_CONFIG_PATH
    )
    assert f"--proxy {normalized.split('://', 1)[1]} " in config
    assert ("--encrypt-proxy" in config) == proxy.startswith("https://")


@pytest.mark.parametrize(
    "proxy",
    [
        "socks5://proxy.example",
        "https://user:password@proxy.example",
        "https://proxy.example/path",
        "https://proxy.example?query",
        "https://proxy.example#fragment",
        "https://proxy.example:0",
        "https://proxy.example:65536",
        "https://%h",
    ],
)
def test_unsupported_proxy(charm_module, charm, monkeypatch, proxy):
    """
    arrange: a proxy uses unsupported or unsafe configuration.
    act: prepare the Git SSH files.
    assert: invalid input fails before any workload changes.
    """
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", proxy)
    with pytest.raises(ValueError):
        charm_module.DjangoCharm._copy_files(charm)
    charm._container.exec.assert_not_called()
    charm._container.push.assert_not_called()


def test_accept_new_host_keys(charm_module, charm, monkeypatch, tmp_path):
    """
    arrange: a local SSH server offers an initial host key and later a replacement.
    act: connect using the generated accept-new configuration before and after the change.
    assert: first use is recorded, repeat host verification succeeds, and changed keys fail.
    """
    sshd = shutil.which("sshd")
    if not sshd:
        pytest.skip("OpenSSH server is required for the real host-key exchange")
    keys = [tmp_path / "first_key", tmp_path / "replacement_key"]
    for key in keys:
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True,
            capture_output=True,
            timeout=5,
        )
    known_hosts = tmp_path / "known_hosts"
    monkeypatch.setattr(charm_module, "KNOWN_HOSTS_PATH", str(known_hosts))
    charm.config["git-repo"] = "git+ssh://git@127.0.0.1/zones.git@main"
    charm_module.DjangoCharm._copy_files(charm)
    config_call = next(
        call
        for call in charm._container.push.call_args_list
        if call.args[0] == charm_module.SSH_CONFIG_PATH
    )
    config = tmp_path / "ssh_config"
    config.write_text(config_call.args[1])
    server_config = tmp_path / "sshd_config"
    server_config.write_text(
        "UsePAM no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n"
        "AuthorizedKeysFile none\nLogLevel ERROR\n"
    )

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            subprocess.run(
                [sshd, "-i", "-e", "-f", str(server_config), "-h", str(self.server.host_key)],
                stdin=self.request,
                stdout=self.request,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        server.host_key = keys[0]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        command = [
            "ssh",
            "-F",
            str(config),
            "-p",
            str(server.server_address[1]),
            "-o",
            "BatchMode=yes",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
            "-o",
            "HostKeyAlgorithms=ssh-ed25519",
            "127.0.0.1",
            "true",
        ]
        try:
            first = subprocess.run(command, capture_output=True, text=True, timeout=10)
            assert "Permanently added" in first.stderr, first.stderr
            recorded = known_hosts.read_bytes()
            public_key = keys[0].with_suffix(".pub").read_text().split()[1]
            assert public_key.encode() in recorded
            repeat = subprocess.run(command, capture_output=True, text=True, timeout=10)
            # No authorized client key is needed to exercise host verification.
            assert "Permission denied" in repeat.stderr, repeat.stderr
            assert "Permanently added" not in repeat.stderr
            assert known_hosts.read_bytes() == recorded
            server.host_key = keys[1]
            changed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            assert changed.returncode == 255
            assert "REMOTE HOST IDENTIFICATION HAS CHANGED" in changed.stderr
            assert "Host key verification failed" in changed.stderr
            assert known_hosts.read_bytes() == recorded
        finally:
            server.shutdown()
            thread.join(timeout=5)


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
