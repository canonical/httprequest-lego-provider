# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Revoke domains module."""

# imported-auth-user has to be disabled as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from api.models import AccessLevel, Domain, DomainUserPermission
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class DomainPermissionRevocationError(Exception):
    """Raised when revoking domain permissions fails."""


def revoke_permission(user, domain_name, access_level):
    """Revoke access to a domain.

    Args:
        user: the user.
        domain_name: the domain name to revoke access from.
        access_level: the access level.

    Raises:
        DomainPermissionRevocationError: Raised when revoking domain permissions fails.
    """
    domain = Domain.objects.get(fqdn=domain_name)
    deleted, _ = DomainUserPermission.objects.filter(
        domain=domain, user=user, access_level=access_level
    ).delete()
    if not deleted:
        raise DomainPermissionRevocationError("Failed to delete domain user permission.")


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
        permissions = [(domain_name, AccessLevel.DOMAIN) for domain_name in domains] + [
            (domain_name, AccessLevel.SUBDOMAIN) for domain_name in subdomains
        ]

        for domain_name, access_level in permissions:
            try:
                revoke_permission(user, domain_name, access_level)
            except Domain.DoesNotExist:
                failed.append(
                    f"[Domain: {domain_name}, Access Level: {access_level}] Domain does not exist."
                )
            except DomainPermissionRevocationError:
                failed.append(
                    f"[Domain: {domain_name}, Access Level: {access_level}] "
                    f"Failed to delete domain user permission."
                )

        if failed:
            error_message = "Failed to revoke access to the following domains: \n" + "\n".join(
                failed
            )
            raise CommandError(error_message)

        self.stdout.write(self.style.SUCCESS("Successfully removed access to the domains."))
