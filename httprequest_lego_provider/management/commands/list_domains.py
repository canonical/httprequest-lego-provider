"""List domains module."""

# pylint:disable=imported-auth-user

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from httprequest_lego_provider.models import DomainUserPermission


class Command(BaseCommand):
    """Command to list the domains an user has access to.

    Attrs:
        help: help message to display.
    """

    help = "Create an user or update its password."

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
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'User "{username}" does not exist') from exc
        dups = DomainUserPermission.objects.filter(user=user)

        self.stdout.write(self.style.SUCCESS([dup.domain.fqdn for dup in dups]))
