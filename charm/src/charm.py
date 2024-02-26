#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import logging
import typing

import ops

import xiilib.django

logger = logging.getLogger(__name__)


DJANGO_USER = "_daemon_"
DJANGO_GROUP = "_daemon_"
KNOWN_HOSTS_PATH = "/var/lib/pebble/default/.ssh/known_hosts"
RSA_PATH = "/var/lib/pebble/default/.ssh/id_rsa"

class DjangoCharm(xiilib.django.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.framework.observe(self.on.collect_app_status, self._on_collect_app_status)

    def _on_config_changed(self, _event: ops.ConfigChangedEvent) -> None:
        """"Config changed handler.

        Args:
            event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_config_changed(_event)

    def _on_django_app_pebble_ready(self, _event: ops.PebbleReadyEvent) -> None:
        """"Pebble ready handler.

        Args:
            event: the event triggering the handler.
        """
        self._copy_files()
        super()._on_django_app_pebble_ready(_event)

    def _copy_files(self) -> None:
        """Copy files needed by git."""
        container = self.unit.get_container(self._CONTAINER_NAME)
        if not container.can_connect():
            return
        if not self.config.get("git_repo") or not self.config.get("git_ssh_key"):
            return
        hostname = self.config.get("git_repo").split("@")[1].split("/")[0]
        process = container.exec(["ssh-keyscan", "-t", "rsa", hostname])
        output, _ = process.wait_output()
        container.push(
            KNOWN_HOSTS_PATH,
            output,
            encoding="utf-8",
            make_dirs=True,
            user=DJANGO_USER,
            group=DJANGO_GROUP,
            permissions=0o600,
        )
        container.push(
            RSA_PATH,
            self.config.get("git_ssh_key"),
            encoding="utf-8",
            make_dirs=True,
            user=DJANGO_USER,
            group=DJANGO_GROUP,
            permissions=0o600,
        )
    
    def _on_collect_app_status(self, _: ops.CollectStatusEvent) -> None:
        """"Handle the status changes.

        Args:
            event: the event triggering the handler.
        """
        if not self.config.get("git_repo"):
            self.unit.status = ops.WaitingStatus("Config git_repo is required")
            return
        if not self.config.get("git_ssh_key"):
            self.unit.status = ops.WaitingStatus("Config git_ssh_key is required")
            return


if __name__ == "__main__":
    ops.main.main(DjangoCharm)
