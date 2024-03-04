"""Revoke domains module."""

# pylint:disable=imported-auth-user

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from httprequest_lego_provider.models import Domain, DomainUserPermission


class Command(BaseCommand):
    """Command to revoke access to domains to an user.

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
            domain, _ = Domain.objects.get_or_create(fqdn=f"_acme-challenge.{domain_name}")
            DomainUserPermission.objects.filter(domain=domain, user=user).delete()

        self.stdout.write(self.style.SUCCESS(f'Revoked "{domains}" for "{username}"'))
