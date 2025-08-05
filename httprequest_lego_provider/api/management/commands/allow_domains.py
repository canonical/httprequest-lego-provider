# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Allow domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=duplicate-code,imported-auth-user

from api.models import AccessLevel, Domain, DomainUserPermission
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


def grant_permission(user, domain_name, access_level):
    """Grant permission to a domain.

    Args:
        user: the user.
        domain_name: the domain name to grant access to.
        access_level: the access level.
    """
    try:
        domain = Domain.objects.get(fqdn=domain_name)
    except Domain.DoesNotExist:
        domain = Domain(fqdn=domain_name)
        domain.full_clean()
        domain.save()

    try:
        DomainUserPermission.objects.get(domain=domain, user=user, access_level=access_level)
    except DomainUserPermission.DoesNotExist:
        permission = DomainUserPermission(domain=domain, user=user, access_level=access_level)
        permission.full_clean()
        permission.save()


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
            CommandError: if the command fails.
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
                grant_permission(user, domain_name, access_level)
            except ValidationError as e:
                failed.append(
                    f"[Domain: {domain_name}, Access: {access_level}] "
                    f"ValidationError: {e.messages}"
                )

        if failed:
            error_message = "Failed to grant access to the following domains: \n" + "\n".join(
                failed
            )
            raise CommandError(error_message)

        self.stdout.write(self.style.SUCCESS("Successfully granted access to all domains."))
