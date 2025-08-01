# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Allow domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=duplicate-code,imported-auth-user

from api.models import AccessLevel, Domain, DomainUserPermission
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
        parser.add_argument("username", type=str)
        parser.add_argument("--domains", type=str, default=None)
        parser.add_argument("--subdomains", type=str, default=None)

    def handle(self, *args, **options):
        """Command handler.

        Args:
            args: args.
            options: options.

        Raises:
            CommandError: if the user is not found.
        """
        username = options["username"]
        domains = options["domains"].split(",") if options["domains"] else []
        subdomains = options["subdomains"].split(",") if options["subdomains"] else []
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'User "{username}" does not exist') from exc

        failed = []

        def grant_permission(domain_name, access_level):
            """Grant permission to a domain.

            Args:
                domain_name: the domain name to grant access to.
                access_level: the access level.
            """
            domain, _ = Domain.objects.get_or_create(fqdn=domain_name)

            _, created = DomainUserPermission.objects.get_or_create(
                domain=domain, user=user, access_level=access_level
            )
            if not created:
                failed.append(f"Domain: {domain_name}, Access Level: {access_level}")

        for domain_name in domains:
            grant_permission(domain_name, AccessLevel.DOMAIN)

        for subdomain_name in subdomains:
            grant_permission(subdomain_name, AccessLevel.SUBDOMAIN)

        if failed:
            raise CommandError(
                f"Failed to grant access to the following domains: {', '.join(failed)}"
            )

        self.stdout.write(self.style.SUCCESS("Successfully granted access to all domains."))
