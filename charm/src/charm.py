#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import logging
import typing

import actions
import ops
import paas_app_charmer.django

logger = logging.getLogger(__name__)


DJANGO_USER = "_daemon_"
DJANGO_GROUP = "_daemon_"
KNOWN_HOSTS_PATH = "/var/lib/pebble/default/.ssh/known_hosts"
RSA_PATH = "/var/lib/pebble/default/.ssh/id_rsa"


class DjangoCharm(paas_app_charmer.django.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.actions_observer = actions.Observer(self)
        self.framework.observe(self.on.collect_app_status, self._on_collect_app_status)

    def _on_config_changed(self, _event: ops.ConfigChangedEvent) -> None:
        """Config changed handler.

        Args:
            _event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_config_changed(_event)

    def _on_pebble_ready(self, _event: ops.PebbleReadyEvent) -> None:
        """Pebble ready handler.

        Args:
            _event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_pebble_ready(_event)

    def _copy_files(self) -> None:
        """Copy files needed by git."""
        if not self._container.can_connect():
            return
        if not self.config.get("git-repo") or not self.config.get("git-ssh-key"):
            return
        hostname = self.config.get("git-repo").split("@")[1].split("/")[0]
        process = self._container.exec(["ssh-keyscan", "-t", "rsa", hostname])
        output, _ = process.wait_output()
        self._container.push(
            KNOWN_HOSTS_PATH,
            output,
            encoding="utf-8",
            make_dirs=True,
            user=DJANGO_USER,
            group=DJANGO_GROUP,
            permissions=0o600,
        )
        self._container.push(
            RSA_PATH,
            self.config.get("git-ssh-key"),
            encoding="utf-8",
            make_dirs=True,
            user=DJANGO_USER,
            group=DJANGO_GROUP,
            permissions=0o600,
        )

    def _on_collect_app_status(self, _: ops.CollectStatusEvent) -> None:
        """Handle the status changes."""
        if not self.config.get("git-repo"):
            self.unit.status = ops.WaitingStatus("Config git-repo is required")
            return
        if not self.config.get("git-ssh-key"):
            self.unit.status = ops.WaitingStatus("Config git-ssh-key is required")
            return


if __name__ == "__main__":  # pragma: no cover
    ops.main.main(DjangoCharm)
