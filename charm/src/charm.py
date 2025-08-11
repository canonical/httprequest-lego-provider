#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import logging
import typing

import actions
import ops
import paas_app_charmer.django
from charms.dns_record.v0 import dns_record

logger = logging.getLogger(__name__)

DJANGO_USER = "_daemon_"
DJANGO_GROUP = "_daemon_"
KNOWN_HOSTS_PATH = "/var/lib/pebble/default/.ssh/known_hosts"
RSA_PATH = "/var/lib/pebble/default/.ssh/id_rsa"
CONTAINER_NAME = "django-app"


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
        if not self.model.unit.is_leader():
            return
        entries = self.dns_record.get_relation_data()
        known_notice = False

        if event.notice.key.startswith("dns.local/write"):
            fqdn = event.notice.last_data["fqdn"].strip("'").strip()
            rdata = event.notice.last_data["rdata"].strip("'").strip()

            try:
                host_label = fqdn.split(".")[0]
                domain = fqdn.split(".", 1)[1]
            except IndexError:
                logger.error("Faulty write notice received: %s, FQDN: %s", event.notice.key, fqdn)
                return

            entry = self.dns_record.create_record_request(
                [host_label, domain, 600, "IN", "TXT", rdata]
            )
            entries.append(entry)
            logger.debug("DNS record request: %s", entry)
            known_notice = True

        if event.notice.key.startswith("dns.local/remove"):
            fqdn = event.notice.last_data["fqdn"].strip("'").strip()
            known_notice = True
            # remove entries with the same fqdn
            entries = [e for e in entries if fqdn != f"{entry.host_label}.{entry.domain}"]

        if not known_notice:
            # We received an unknown notice, nothing to do with it.
            logger.debug("Unknown notice: %s", event.notice.key)
            return
        try:
            for relation in self.model.relations[self.dns_record.relation_name]:
                self.dns_record.update_relation_data(relation, entries)
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise


if __name__ == "__main__":  # pragma: no cover
    ops.main.main(DjangoCharm)
