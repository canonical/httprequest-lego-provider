# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Allow domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=duplicate-code,imported-auth-user

from api.forms import FQDN_PREFIX
from api.models import Domain, DomainUserPermission
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Command to grant access to domains to a user.

    Attrs:
        help: help message to display.
    """

    help = "Grant user access to domains."

    def add_arguments(self, parser):
        """Argument parser.

        Args:
            parser: the cmd line parser.
        """
        parser.add_argument("username", nargs=None, type=str)
        parser.add_argument("domains", nargs="+", type=str)

    def handle(self, *args, **options):
        """Command handler.

        Args:
            args: args.
            options: options.

        Raises:
            CommandError: if the user is not found.
        """
        username = options["username"]
        domains = options["domains"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'User "{username}" does not exist') from exc
        for domain_name in domains:
            fqdn = (
                domain_name
                if domain_name.startswith(FQDN_PREFIX)
                else f"{FQDN_PREFIX}{domain_name}"
            )
            domain, _ = Domain.objects.get_or_create(fqdn=fqdn)
            DomainUserPermission.objects.get_or_create(domain=domain, user=user)

        self.stdout.write(self.style.SUCCESS(f'Granted "{", ".join(domains)}" for "{username}"'))
