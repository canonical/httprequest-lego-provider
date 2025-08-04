# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Revoke domains module."""

# imported-auth-user has to be disabled as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from api.models import AccessLevel, Domain, DomainUserPermission
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class DomainRevokeError(CommandError):
    """Raised when domain revocation fails due to missing or undeleted domains."""

    def __init__(self, not_found=None, failed=None):
        message = []
        if not_found:
            message.append(f"These domains do not exist and were skipped: {', '.join(not_found)}")
        if failed:
            message.append(f"Failed to delete the following domains: {', '.join(failed)}")

        super().__init__("\n".join(message))


class Command(BaseCommand):
    """Command to revoke access to domains to a user.

    Attrs:
        help: help message to display.
    """

    help = "Revoke user access to domains."

    def add_arguments(self, parser):
        """Argument parser.

        Args:
            parser: the cmd line parser.
        """
        parser.add_argument("username", type=str)
        parser.add_argument("--domains", type=str, default=None)
        parser.add_argument("--subdomains", type=str, default=None)

    def handle(self, *args, **options):  # noqa: C901
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

        not_found = []
        failed = []

        def revoke_permission(domain_name, access_level):
            """Revoke access to a domain.

            Args:
                domain_name: the domain name to revoke access from.
                access_level: the access level.
            """
            try:
                domain = Domain.objects.get(fqdn=domain_name)
            except Domain.DoesNotExist:
                not_found.append(domain_name)
                return
            deleted, _ = DomainUserPermission.objects.filter(
                domain=domain, user=user, access_level=access_level
            ).delete()
            if not deleted:
                failed.append(domain_name)

        for domain_name in domains:
            revoke_permission(domain_name, AccessLevel.DOMAIN)

        for subdomain_name in subdomains:
            revoke_permission(subdomain_name, AccessLevel.SUBDOMAIN)

        if not_found or failed:
            raise DomainRevokeError(not_found=not_found, failed=failed)

        self.stdout.write(self.style.SUCCESS("Successfully removed access to the domains."))
