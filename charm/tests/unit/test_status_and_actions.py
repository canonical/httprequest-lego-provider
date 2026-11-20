# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the httprequest-lego-provider charm's collect-status and actions."""

import os
import pathlib
import sys
import ops
import pytest

CHARM_DIR = pathlib.Path(__file__).parents[2]
sys.path.insert(0, str(CHARM_DIR / "lib"))
sys.path.insert(0, str(CHARM_DIR / "src"))

os.environ["SCENARIO_SKIP_CONSISTENCY_CHECKS"] = "1"

from ops import testing  # noqa: E402

import charm  # noqa: E402


class TestCollectAppStatus:
    """Test the collect-app-status handler for missing config."""

    def test_missing_git_repo_sets_waiting(self):
        """When git-repo is not set, unit status should be WaitingStatus."""
        ctx = testing.Context(charm.DjangoCharm)
        container = testing.Container("django-app", can_connect=True)
        state = testing.State(
            containers={container},
            config={"git-ssh-key": "some-key"},
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert isinstance(state_out.unit_status, ops.WaitingStatus)
        assert "git-repo" in state_out.unit_status.message

    def test_missing_git_ssh_key_sets_waiting(self):
        """When git-ssh-key is not set, unit status should be WaitingStatus."""
        ctx = testing.Context(charm.DjangoCharm)
        container = testing.Container("django-app", can_connect=True)
        state = testing.State(
            containers={container},
            config={"git-repo": "git+ssh://user@host/repo"},
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert isinstance(state_out.unit_status, ops.WaitingStatus)
        assert "git-ssh-key" in state_out.unit_status.message

    def test_both_config_present_no_waiting(self):
        """When both git-repo and git-ssh-key are set, no WaitingStatus."""
        ctx = testing.Context(charm.DjangoCharm)
        container = testing.Container("django-app", can_connect=True)
        state = testing.State(
            containers={container},
            config={
                "git-repo": "git+ssh://user@host/repo",
                "git-ssh-key": "some-key",
            },
            leader=True,
        )
        state_out = ctx.run(ctx.on.collect_app_status(), state)
        assert not isinstance(state_out.unit_status, ops.WaitingStatus)


class TestActions:
    """Test the four custom actions.

    The actions need the secret-storage peer relation (for the secret key)
    and the postgresql relation (a required integration) so that the parent's
    ``is_ready()`` returns True and ``_gen_environment()`` succeeds.
    """

    _MANAGE_PY = ["python3", "manage.py"]

    def _action_state(self, ctx, *, execs=frozenset()):
        """Create a State from context with the relations the parent requires."""
        peer = testing.PeerRelation(
            "secret-storage",
            local_app_data={"django_secret_key": "test-secret-key"},
        )
        postgresql = testing.Relation(
            "postgresql",
            remote_app_data={
                "endpoints": "10.0.0.1:5432",
                "username": "testuser",
                "password": "testpass",
            },
        )
        return testing.State.from_context(
            ctx,
            leader=True,
            relations={peer, postgresql},
            containers={testing.Container(
                "django-app", can_connect=True, execs=execs,
            )},
        )

    def test_create_user_runs_management_command(self):
        """create-user generates a password and runs create_user."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx, execs={testing.Exec(self._MANAGE_PY, stdout="OK")},
        )

        ctx.run(
            ctx.on.action("create-user", params={"username": "testuser"}),
            state,
        )

        cmd = ctx.exec_history["django-app"][0].command
        assert cmd[:3] == ["python3", "manage.py", "create_user"]
        assert cmd[3] == "testuser"
        assert len(cmd[4]) > 0  # generated password

    def test_create_user_sets_result(self):
        """create-user sets results from command output."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx,
            execs={testing.Exec(
                self._MANAGE_PY, stdout="User created with password xyz",
            )},
        )

        ctx.run(
            ctx.on.action("create-user", params={"username": "testuser"}),
            state,
        )

        assert ctx.action_results == {"result": "User created with password xyz"}

    def test_allow_domains_with_both_params(self):
        """allow-domains passes domains and subdomains."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx, execs={testing.Exec(self._MANAGE_PY, stdout="OK")},
        )

        ctx.run(
            ctx.on.action(
                "allow-domains",
                params={
                    "username": "testuser",
                    "domains": "example.com,test.com",
                    "subdomains": "sub.example.com",
                },
            ),
            state,
        )

        cmd = ctx.exec_history["django-app"][0].command
        assert "allow_domains" in cmd
        assert "--domains" in cmd
        assert "example.com,test.com" in cmd
        assert "--subdomains" in cmd
        assert "sub.example.com" in cmd

    def test_allow_domains_fails_without_domains_or_subdomains(self):
        """allow-domains fails if neither domains nor subdomains."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(ctx)

        with pytest.raises(testing.ActionFailed) as exc_info:
            ctx.run(
                ctx.on.action("allow-domains", params={"username": "testuser"}),
                state,
            )

        assert "domains" in exc_info.value.message.lower()

    def test_allow_domains_only_domains(self):
        """allow-domains works with only domains (no subdomains)."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx, execs={testing.Exec(self._MANAGE_PY, stdout="OK")},
        )

        ctx.run(
            ctx.on.action(
                "allow-domains",
                params={"username": "testuser", "domains": "example.com"},
            ),
            state,
        )

        cmd = ctx.exec_history["django-app"][0].command
        assert "--domains" in cmd
        assert "--subdomains" not in cmd

    def test_revoke_domains_action(self):
        """revoke-domains calls revoke_domains management command."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx, execs={testing.Exec(self._MANAGE_PY, stdout="OK")},
        )

        ctx.run(
            ctx.on.action(
                "revoke-domains",
                params={"username": "testuser", "domains": "example.com"},
            ),
            state,
        )

        cmd = ctx.exec_history["django-app"][0].command
        assert "revoke_domains" in cmd
        assert "--domains" in cmd

    def test_revoke_domains_fails_without_domains_or_subdomains(self):
        """revoke-domains fails if neither domains nor subdomains."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(ctx)

        with pytest.raises(testing.ActionFailed):
            ctx.run(
                ctx.on.action("revoke-domains", params={"username": "testuser"}),
                state,
            )

    def test_list_domains_action(self):
        """list-domains calls list_domains and returns output."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx,
            execs={testing.Exec(
                self._MANAGE_PY, stdout="domain1.com\ndomain2.com",
            )},
        )

        ctx.run(
            ctx.on.action("list-domains", params={"username": "testuser"}),
            state,
        )

        cmd = ctx.exec_history["django-app"][0].command
        assert cmd == ["python3", "manage.py", "list_domains", "testuser"]
        assert ctx.action_results == {"result": "domain1.com\ndomain2.com"}

    def test_action_handles_exec_error(self):
        """Actions handle ExecError and fail with stderr message."""
        ctx = testing.Context(charm.DjangoCharm)
        state = self._action_state(
            ctx,
            execs={testing.Exec(
                self._MANAGE_PY, return_code=1, stderr="User already exists",
            )},
        )

        with pytest.raises(testing.ActionFailed) as exc_info:
            ctx.run(
                ctx.on.action("create-user", params={"username": "testuser"}),
                state,
            )

        assert "User already exists" in exc_info.value.message
