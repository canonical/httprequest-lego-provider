from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from httprequest_lego_provider.models import Domain
from httprequest_lego_provider.models import DomainUserPermission

class Command(BaseCommand):
    """Command to list the domains an user has access to."""

    help = "Create an user or update its password."

    def add_arguments(self, parser):
        """Argument parser."""
        parser.add_argument("username", nargs=None, type=str)

    def handle(self, *args, **options):
        """Command handler."""
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % username)
        dups = DomainUserPermission.objects.filter(user=user)

        self.stdout.write(
            self.style.SUCCESS([dup.domain.fqdn for dup in dups])
        )
