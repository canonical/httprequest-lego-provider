# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the httprequest-lego-provider charm's custom functionality.

Tests cover the custom code added on top of the django-framework extension:
- SSH key file copying on config-changed and pebble-ready
- collect-app-status handler (missing git-repo / git-ssh-key config)
- Four custom actions: create-user, allow-domains, revoke-domains, list-domains
"""

import os
import pathlib
import sys
import unittest.mock

import ops
import pytest
import yaml

# Mock the paas_app_charmer dependency before importing charm code.
mock_paas = unittest.mock.MagicMock()
mock_paas.django.Charm = ops.CharmBase
sys.modules["paas_app_charmer"] = mock_paas
sys.modules["paas_app_charmer.django"] = mock_paas.django

# Add charm src/ to path.
CHARM_DIR = pathlib.Path(__file__).parents[2]
sys.path.insert(0, str(CHARM_DIR / "src"))

os.environ["SCENARIO_SKIP_CONSISTENCY_CHECKS"] = "1"

import actions  # noqa: E402
import charm  # noqa: E402
import ops.testing  # noqa: E402

# Load metadata from charmcraft.yaml for passing explicitly to Context.
# We must manually merge extension data since autoload won't run for
# _TestDjangoCharm (defined outside the charm source tree).
_raw = yaml.safe_load((CHARM_DIR / "charmcraft.yaml").read_text())

# django-framework extension metadata (from ops PR 2367)
_DJANGO_EXT_META = {
    "assumes": ["k8s-api"],
    "containers": {"django-app": {"resource": "django-app-image"}},
    "peers": {"secret-storage": {"interface": "secret-storage"}},
    "provides": {
        "grafana-dashboard": {"interface": "grafana_dashboard"},
        "metrics-endpoint": {"interface": "prometheus_scrape"},
    },
    "requires": {
        "ingress": {"interface": "ingress", "limit": 1},
        "logging": {"interface": "loki_push_api"},
    },
    "resources": {
        "django-app-image": {"description": "django application image.", "type": "oci-image"}
    },
}

_META = {k: v for k, v in _raw.items() if k not in ("config", "actions", "extensions")}
# Merge extension metadata (extension provides defaults, local overrides).
for key, ext_value in _DJANGO_EXT_META.items():
    if key not in _META:
        _META[key] = ext_value
    elif isinstance(ext_value, dict) and isinstance(_META[key], dict):
        merged = dict(ext_value)
        merged.update(_META[key])
        _META[key] = merged

_CONFIG = _raw.get("config")
_ACTIONS = _raw.get("actions")


class _TestDjangoCharm(charm.DjangoCharm):
    """Test subclass that registers observers the parent class would.

    The real paas_app_charmer.django.Charm registers config_changed and
    pebble_ready observers and provides _on_config_changed / _on_pebble_ready
    base methods.  Since we mock the parent as CharmBase (which lacks those),
    we register our own handlers that exercise only the custom _copy_files logic.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(
            self.on.config_changed, self._test_on_config_changed
        )
        self.framework.observe(
            self.on.django_app_pebble_ready, self._test_on_pebble_ready
        )

    def _test_on_config_changed(self, _event):
        self._copy_files()

    def _test_on_pebble_ready(self, _event):
        self._copy_files()


def _patch_parent_attrs(mgr, container_name="django-app"):
    """Patch attributes that normally come from paas_app_charmer.django.Charm."""
    container_obj = mgr.charm.unit.get_container(container_name)
    mgr.charm._container = container_obj
    mgr.charm._workload_config = unittest.mock.MagicMock()
    mgr.charm._workload_config.base_dir = pathlib.PurePosixPath("/srv")
    mgr.charm._workload_config.app_dir = pathlib.PurePosixPath("/srv/app")
    mgr.charm._gen_environment = unittest.mock.MagicMock(return_value={})
    mgr.charm.is_ready = unittest.mock.MagicMock(return_value=True)
    return container_obj


class TestCollectAppStatus:
    """Test the collect-app-status handler for missing config."""

    def test_missing_git_repo_sets_waiting(self):
        """When git-repo is not set, unit status should be WaitingStatus."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={"git-ssh-key": "some-key"},
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert isinstance(state_out.unit_status, ops.WaitingStatus)
        assert "git-repo" in state_out.unit_status.message

    def test_missing_git_ssh_key_sets_waiting(self):
        """When git-ssh-key is not set, unit status should be WaitingStatus."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={"git-repo": "git+ssh://user@host/repo"},
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert isinstance(state_out.unit_status, ops.WaitingStatus)
        assert "git-ssh-key" in state_out.unit_status.message

    def test_both_config_present_no_waiting(self):
        """When both git-repo and git-ssh-key are set, no WaitingStatus."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://user@host/repo",
                "git-ssh-key": "some-key",
            },
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert not isinstance(state_out.unit_status, ops.WaitingStatus)


class TestCopyFiles:
    """Test SSH key copying on config-changed and pebble-ready."""

    def test_config_changed_runs_ssh_keyscan(self):
        """On config-changed with container connected, ssh-keyscan is run."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://git@github.com/canonical/repo@main",
                "git-ssh-key": "-----BEGIN RSA PRIVATE KEY-----\nfakekey",
            },
            leader=True,
        )

        with ctx(ctx.on.config_changed(), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = (
                "github.com ssh-rsa AAAA...",
                "",
            )
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            container_obj.push = unittest.mock.MagicMock()
            mgr.run()

            container_obj.exec.assert_called_once()
            exec_args = container_obj.exec.call_args[0][0]
            assert exec_args == ["ssh-keyscan", "-t", "rsa", "github.com"]

    def test_config_changed_pushes_known_hosts_and_key(self):
        """Config-changed pushes both known_hosts and id_rsa to container."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://git@github.com/canonical/repo@main",
                "git-ssh-key": "my-private-key",
            },
            leader=True,
        )

        with ctx(ctx.on.config_changed(), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = ("github.com ssh-rsa ...", "")
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            container_obj.push = unittest.mock.MagicMock()
            mgr.run()

            push_calls = container_obj.push.call_args_list
            assert len(push_calls) == 2
            assert push_calls[0][0][0] == charm.KNOWN_HOSTS_PATH
            assert push_calls[0][1]["permissions"] == 0o600
            assert push_calls[0][1]["user"] == charm.DJANGO_USER
            assert push_calls[0][1]["group"] == charm.DJANGO_GROUP
            assert push_calls[1][0][0] == charm.RSA_PATH
            assert push_calls[1][0][1] == "my-private-key"
            assert push_calls[1][1]["permissions"] == 0o600

    def test_config_changed_skips_without_git_config(self):
        """On config-changed without git config, _copy_files does nothing."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container}, config={}, leader=True,
        )

        with ctx(ctx.on.config_changed(), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            container_obj.exec = unittest.mock.MagicMock()
            mgr.run()
            container_obj.exec.assert_not_called()

    def test_pebble_ready_copies_files(self):
        """On pebble-ready with config, SSH files are pushed."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://git@gitlab.com/org/repo",
                "git-ssh-key": "fakekey",
            },
            leader=True,
        )

        with ctx(ctx.on.pebble_ready(container), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = ("gitlab.com ssh-rsa ...", "")
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            container_obj.push = unittest.mock.MagicMock()
            mgr.run()
            container_obj.exec.assert_called_once()
            exec_args = container_obj.exec.call_args[0][0]
            assert "gitlab.com" in exec_args

    def test_copy_files_skips_when_container_not_connected(self):
        """When container cannot connect, _copy_files returns early."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=False)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://git@github.com/repo",
                "git-ssh-key": "fakekey",
            },
            leader=True,
        )

        with ctx(ctx.on.config_changed(), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            container_obj.exec = unittest.mock.MagicMock()
            mgr.run()
            container_obj.exec.assert_not_called()

    def test_hostname_extraction_from_git_repo(self):
        """The hostname is correctly extracted from git-repo config."""
        ctx = ops.testing.Context(
            _TestDjangoCharm,
            meta=_META,
            config=_CONFIG,
            actions=_ACTIONS,
        )
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://deploy@bitbucket.org/myorg/myrepo@main",
                "git-ssh-key": "key",
            },
            leader=True,
        )

        with ctx(ctx.on.config_changed(), state) as mgr:
            container_obj = _patch_parent_attrs(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = ("bitbucket.org ...", "")
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            container_obj.push = unittest.mock.MagicMock()
            mgr.run()
            exec_args = container_obj.exec.call_args[0][0]
            assert exec_args[-1] == "bitbucket.org"


class TestActions:
    """Test the four custom actions."""

    def _setup_action(self, mgr):
        """Set up common mocks for action tests."""
        container_obj = _patch_parent_attrs(mgr)
        mock_process = unittest.mock.MagicMock()
        mock_process.wait_output.return_value = ("OK", "")
        container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
        return container_obj

    def test_create_user_runs_management_command(self):
        """create-user generates a password and runs create_user."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action("create-user", params={"username": "testuser"}),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mgr.run()

            call_args = container_obj.exec.call_args[0][0]
            assert call_args[:3] == ["python3", "manage.py", "create_user"]
            assert call_args[3] == "testuser"
            assert len(call_args[4]) > 0  # generated password

    def test_create_user_sets_result(self):
        """create-user sets results from command output."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action("create-user", params={"username": "testuser"}),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = (
                "User created with password xyz",
                "",
            )
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            mgr.run()

        assert ctx.action_results == {"result": "User created with password xyz"}

    def test_allow_domains_with_both_params(self):
        """allow-domains passes domains and subdomains."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action(
                "allow-domains",
                params={
                    "username": "testuser",
                    "domains": "example.com,test.com",
                    "subdomains": "sub.example.com",
                },
            ),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mgr.run()

            call_args = container_obj.exec.call_args[0][0]
            assert "allow_domains" in call_args
            assert "--domains" in call_args
            assert "example.com,test.com" in call_args
            assert "--subdomains" in call_args
            assert "sub.example.com" in call_args

    def test_allow_domains_fails_without_domains_or_subdomains(self):
        """allow-domains fails if neither domains nor subdomains."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with pytest.raises(ops.testing.ActionFailed) as exc_info:
            with ctx(
                ctx.on.action("allow-domains", params={"username": "testuser"}),
                state,
            ) as mgr:
                self._setup_action(mgr)
                mgr.run()

        assert "domains" in exc_info.value.message.lower()

    def test_allow_domains_only_domains(self):
        """allow-domains works with only domains (no subdomains)."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action(
                "allow-domains",
                params={"username": "testuser", "domains": "example.com"},
            ),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mgr.run()

            call_args = container_obj.exec.call_args[0][0]
            assert "--domains" in call_args
            assert "--subdomains" not in call_args

    def test_revoke_domains_action(self):
        """revoke-domains calls revoke_domains management command."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action(
                "revoke-domains",
                params={"username": "testuser", "domains": "example.com"},
            ),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mgr.run()

            call_args = container_obj.exec.call_args[0][0]
            assert "revoke_domains" in call_args
            assert "--domains" in call_args

    def test_revoke_domains_fails_without_domains_or_subdomains(self):
        """revoke-domains fails if neither domains nor subdomains."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with pytest.raises(ops.testing.ActionFailed):
            with ctx(
                ctx.on.action("revoke-domains", params={"username": "testuser"}),
                state,
            ) as mgr:
                self._setup_action(mgr)
                mgr.run()

    def test_list_domains_action(self):
        """list-domains calls list_domains and returns output."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with ctx(
            ctx.on.action("list-domains", params={"username": "testuser"}),
            state,
        ) as mgr:
            container_obj = self._setup_action(mgr)
            mock_process = unittest.mock.MagicMock()
            mock_process.wait_output.return_value = (
                "domain1.com\ndomain2.com",
                "",
            )
            container_obj.exec = unittest.mock.MagicMock(return_value=mock_process)
            mgr.run()

            call_args = container_obj.exec.call_args[0][0]
            assert call_args == ["python3", "manage.py", "list_domains", "testuser"]

        assert ctx.action_results == {"result": "domain1.com\ndomain2.com"}

    def test_action_handles_exec_error(self):
        """Actions handle ExecError and fail with stderr message."""
        ctx = ops.testing.Context(charm.DjangoCharm, charm_root=CHARM_DIR)
        container = ops.testing.Container("django-app", can_connect=True)
        state = ops.testing.State(containers={container}, leader=True)

        with pytest.raises(ops.testing.ActionFailed) as exc_info:
            with ctx(
                ctx.on.action("create-user", params={"username": "testuser"}),
                state,
            ) as mgr:
                container_obj = _patch_parent_attrs(mgr)
                mock_process = unittest.mock.MagicMock()
                mock_process.wait_output.side_effect = ops.pebble.ExecError(
                    command=["python3", "manage.py", "create_user"],
                    exit_code=1,
                    stdout="",
                    stderr="User already exists",
                )
                container_obj.exec = unittest.mock.MagicMock(
                    return_value=mock_process
                )
                mgr.run()

        assert "User already exists" in exc_info.value.message
