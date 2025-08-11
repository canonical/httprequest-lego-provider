# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""List domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from api.models import AccessLevel, DomainUserPermission
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


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

        def format_list_user(user):
            """Format the list user output.

            Args:
                user: the username.

            Returns:
                str: formatted output.
            """
            domain_access = []
            dups = DomainUserPermission.objects.filter(user=user, access_level=AccessLevel.DOMAIN)
            for dup in dups:
                domain_access.append(dup.domain.fqdn)

            subdomain_access = []
            dups = DomainUserPermission.objects.filter(
                user=user, access_level=AccessLevel.SUBDOMAIN
            )
            for dup in dups:
                subdomain_access.append(dup.domain.fqdn)

            output = [f"\n{user.username}:"]
            if domain_access:
                output.append("    domains:")
                output.append(f"        {', '.join(sorted(domain_access))}")
            if subdomain_access:
                output.append("    subdomains:")
                output.append(f"        {', '.join(sorted(subdomain_access))}")
            return "\n".join(output)

        if username == "*":
            output = []
            for user in User.objects.iterator():
                output.append(format_list_user(user))
            self.stdout.write(self.style.SUCCESS("\n".join(output)))
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f'User "{username}" does not exist') from exc
            self.stdout.write(self.style.SUCCESS(format_list_user(user)))
