# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTPRequest LEGO provider charm actions."""

# pylint: disable=protected-access

import logging
import secrets
from typing import AnyStr, Optional, Tuple

import ops
import xiilib.django

logger = logging.getLogger(__name__)


CREATE_OR_UPDATE_USER_TEMPLATE = (
    "from django.contrib.auth.models import User;"
    "User.objects.update_or_create(username='{username}', password='{password}')"
)
GRANT_DOMAIN_USER_PERMISSION_TEMPLATE = (
    "from django.contrib.auth.models import User;"
    "from httprequest_lego_provider.models import Domain;"
    "from httprequest_lego_provider.models import DomainUserPermission;"
    "user = User.objects.get(username='{username}');"
    "domain, _ = Domain.objects.get_or_create(fqdn='_acme-challenge.{domain}')"
    "DomainUserPermission.objects.get_or_create(domain=domain, user=user)"
)
REVOKE_DOMAIN_USER_PERMISSION_TEMPLATE = (
    "from django.contrib.auth.models import User;"
    "from httprequest_lego_provider.models import Domain;"
    "from httprequest_lego_provider.models import DomainUserPermission;"
    "user = User.objects.get(username='{username}');"
    "domain = Domain.objects.get(fqdn='_acme-challenge.{domain}');"
    "DomainUserPermission.objects.filter(domain=domain, user=user).delete()"
)
LIST_DOMAINS_TEMPLATE = (
    "from django.contrib.auth.models import User;"
    "from httprequest_lego_provider.models import Domain;"
    "from httprequest_lego_provider.models import DomainUserPermission;"
    "user = User.objects.get(username='{username}');"
    "dups = DomainUserPermission.objects.filter(user=user);"
    "print([dup.domain.fqdn for dup in dups])"
)


class NotReadyError(Exception):
    """Exception thrown when needed resources are not ready."""


class Observer(ops.Object):
    """Jenkins-k8s charm actions observer."""

    def __init__(self, charm: xiilib.django.Charm):
        """Initialize the observer and register actions handlers.

        Args:
            charm: The parent charm to attach the observer to.
            state: The Jenkins charm state.
        """
        super().__init__(charm, "actions-observer")
        self.charm = charm

        charm.framework.observe(charm.on.create_user_action, self._create_or_update_user)
        charm.framework.observe(charm.on.reset_password_action, self._create_or_update_user)
        charm.framework.observe(charm.on.allow_domains_action, self._allow_domains)
        charm.framework.observe(charm.on.revoke_domains_action, self._revoke_domains)
        charm.framework.observe(charm.on.list_domains_action, self._list_domains)

    def _generate_password(self) -> str:
        """Generate a new password.

        Returns: the new password.
        """
        return secrets.token_urlsafe(30)

    def _execute_script(self, script: str) -> Tuple[AnyStr, Optional[AnyStr]]:
        """Prepare the scripts for exxecution.

        Args:
            script: the script to execute.

        Returns: the output from the execution.

        Raises:
            NotReadyError: if the container or the database are not ready.
            ExecError: if an error occurs while executing the script
        """
        container = self.charm.unit.get_container(self.charm._CONTAINER_NAME)
        if not container.can_connect() or not self.charm._databases.is_ready():
            raise NotReadyError("Container or database not ready.")
        process = container.exec(
            ["python3", "manage.py", "shell" f'--command="{script}"'],
            working_dir=self.charm._BASE_DIR / "app",
            environment=self.charm.gen_env(),
        )
        try:
            stdout, stderr = process.wait_output()
        except ops.pebble.ExecError as ex:
            logger.exception("Action failed: %s", ex.stdout)
            raise
        return stdout, stderr

    def _create_or_update_user(self, event: ops.ActionEvent) -> None:
        """Handle create-user and update-password actions.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        password = self._generate_password()
        script = CREATE_OR_UPDATE_USER_TEMPLATE.format(username=username, password=password)
        try:
            self._execute_script(script)
            event.set_results({"password": password})
        except ops.pebble.ExecError as ex:
            event.fail(f"Failed: {ex.stdout!r}")
        except NotReadyError:
            event.fail("Service not yet ready.")

    def _allow_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        domains = event.params["domains"].split(",")
        for domain in domains:
            script = GRANT_DOMAIN_USER_PERMISSION_TEMPLATE.format(
                username=username, domains=domain
            )
            try:
                self._execute_script(script)
            except ops.pebble.ExecError as ex:
                event.fail(f"Failed: {ex.stdout!r}")
            except NotReadyError:
                event.fail("Service not yet ready.")
            break

    def _revoke_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        domains = event.params["domains"].split(",")
        for domain in domains:
            script = REVOKE_DOMAIN_USER_PERMISSION_TEMPLATE.format(
                username=username, domains=domain
            )
            try:
                self._execute_script(script)
            except ops.pebble.ExecError as ex:
                event.fail(f"Failed: {ex.stdout!r}")
                break
            except NotReadyError:
                event.fail("Service not yet ready.")
                break

    def _list_domains(self, event: ops.ActionEvent) -> None:
        """Handle the allow-domains action.

        Args:
            event: The event fired by the action.
        """
        username = event.params["username"]
        script = LIST_DOMAINS_TEMPLATE.format(username=username)
        try:
            output, _ = self._execute_script(script)
            event.set_results({"result": output})
        except ops.pebble.ExecError as ex:
            event.fail(f"Failed: {ex.stdout!r}")
        except NotReadyError:
            event.fail("Service not yet ready.")
