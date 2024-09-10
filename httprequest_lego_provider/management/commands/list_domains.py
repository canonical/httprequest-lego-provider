# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""List domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from httprequest_lego_provider.models import DomainUserPermission


class Command(BaseCommand):
    """Command to list the domains a user has access to.

    Attrs:
        help: help message to display.
    """

    help = "List domains a user has access to. Use '*' for all users."

    def add_arguments(self, parser):
        """Argument parser.

        Args:
            parser: the cmd line parser.
        """
        parser.add_argument("username", nargs=None, type=str)

    def handle(self, *args, **options):
        """Command handler.

        Args:
            args: args.
            options: options.

        Raises:
            CommandError: if the user is not found.
        """
        username = options["username"]
        if username == "*":
            output = []
            for user in User.objects.iterator():
                output.append(f"{user}:")
                dups = DomainUserPermission.objects.filter(user=user)
                output.append(", ".join([dup.domain.fqdn for dup in dups]))
            self.stdout.write(self.style.SUCCESS("\n".join(output)))
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f'User "{username}" does not exist') from exc
            dups = DomainUserPermission.objects.filter(user=user)

            self.stdout.write(self.style.SUCCESS(", ".join([dup.domain.fqdn for dup in dups])))
