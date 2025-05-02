# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP request LEGO provider charm actions."""

# pylint: disable=protected-access

import logging
import secrets

import ops
import paas_app_charmer.django

logger = logging.getLogger(__name__)


class NotReadyError(Exception):
    """Exception thrown when needed resources are not ready."""


class Observer(ops.Object):
    """Charm actions observer."""

    def __init__(self, charm: paas_app_charmer.django.Charm):
        """Initialize the observer and register actions handlers.

        Args:
            charm: The parent charm to attach the observer to.
        """
        super().__init__(charm, "actions-observer")
        self.charm = charm

        charm.framework.observe(charm.on.create_user_action, self._create_user_action)
        charm.framework.observe(charm.on.allow_domains_action, self._allow_domains)
        charm.framework.observe(charm.on.revoke_domains_action, self._revoke_domains)
        charm.framework.observe(charm.on.list_domains_action, self._list_domains)

    def _generate_password(self) -> str:
        """Generate a new password.

        Returns: the new password.
        """
        return secrets.token_urlsafe(30)

    def _execute_command(self, command: list[str], event: ops.ActionEvent) -> None:
        """Prepare the scripts for exxecution.

        Args:
            command: the management command to execute.
            event: the event triggering the original action.

        Raises:
            ExecError: if an error occurs while executing the script
        """
        if not self.charm.is_ready():
            event.fail("Service not yet ready.")

        process = self.charm._container.exec(
            ["python3", "manage.py"] + command,
            working_dir=str(self.charm._workload_config.base_dir / "app"),
            environment=self.charm._gen_environment(),
        )
        try:
            stdout, _ = process.wait_output()
            event.set_results({"result": stdout})
        except ops.pebble.ExecError as ex:
            logger.exception("Action %s failed: %s %s", ex.command, ex.stdout, ex.stderr)
            event.fail(f"Failed: {ex.stderr!r}")

    def _create_user_action(self, event: ops.ActionEvent) -> None:
        """Handle create-user and update-password actions.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        password = self._generate_password()
        self._execute_command(["create_user", username, password], event)

    def _allow_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        domains = event.params["domains"].split(",")
        self._execute_command(["allow_domains", username] + domains, event)

    def _revoke_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        domains = event.params["domains"].split(",")
        self._execute_command(["revoke_domains", username] + domains, event)

    def _list_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        self._execute_command(["list_domains", username], event)
