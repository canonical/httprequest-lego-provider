#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import logging
import typing
import uuid

import actions
import ops
import paas_app_charmer.django
from charms.bind.v0 import dns_record

logger = logging.getLogger(__name__)

DJANGO_USER = "_daemon_"
DJANGO_GROUP = "_daemon_"
KNOWN_HOSTS_PATH = "/var/lib/pebble/default/.ssh/known_hosts"
RSA_PATH = "/var/lib/pebble/default/.ssh/id_rsa"
CONTAINER_NAME = "django-app"

# the following UUID is used as namespace for the uuidv5 generation
UUID_NAMESPACE = uuid.UUID("72d690d4-7af7-4a2e-868c-ec33aaf643d8")


class DjangoCharm(paas_app_charmer.django.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.actions_observer = actions.Observer(self)
        self.framework.observe(
            self.on[CONTAINER_NAME].pebble_custom_notice, self._on_pebble_custom_notice
        )

    def _on_pebble_custom_notice(self, event: ops.PebbleCustomNoticeEvent) -> None:
        """Handle pebble custom notice event.

        Args:
            event: Pebble custom notice event.
        """
        entries = []
        known_notice = False
        if event.notice.key.startswith("dns.local/write"):
            fqdn = event.notice.last_data["fqdn"].strip("'").strip()
            rdata = event.notice.last_data["rdata"].strip("'").strip()
            entry = dns_record.RequirerEntry(
                host_label=fqdn.split(".")[0],
                domain=fqdn.split(".", 1)[1],
                ttl=600,
                record_class="IN",
                record_type="TXT",
                record_data=rdata,
                uuid=uuid.uuid5(UUID_NAMESPACE, f"{fqdn} {rdata}"),
            )
            logger.debug("DNS record request: %s", entry)
            entries = [entry]
            known_notice = True

        if event.notice.key.startswith("dns.local/remove"):
            # For now, we remove everything
            # since the default is no entries, we have nothing to do here.
            known_notice = True

        if not known_notice:
            # We received an unknown notice, nothing to do with it.
            logger.debug("Unknown notice: %s", event.notice.key)
            return

        dns_record_requirer_data = dns_record.DNSRecordRequirerData(dns_entries=entries)
        if not self.model.unit.is_leader():
            return
        try:
            for relation in self.model.relations[self.dns_record.relation_name]:
                self.dns_record.update_relation_data(relation, dns_record_requirer_data)
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise


if __name__ == "__main__":  # pragma: no cover
    ops.main.main(DjangoCharm)
