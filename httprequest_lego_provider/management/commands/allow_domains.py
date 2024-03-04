from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from httprequest_lego_provider.models import Domain
from httprequest_lego_provider.models import DomainUserPermission

class Command(BaseCommand):
    """Command to grant access to domains to an user."""

    help = "Grant user access to domains."

    def add_arguments(self, parser):
        """Argument parser."""
        parser.add_argument("username", nargs=None, type=str)
        parser.add_argument("domains", nargs="+", type=str, action=lambda t: [s.strip() for s in t.split(',')])

    def handle(self, *args, **options):
        """Command handler."""
        username = options["username"]
        domains = options["domains"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % username)
        for domain_name  in domains:
            domain, _ = Domain.objects.get_or_create(fqdn=f"_acme-challenge.{domain_name}")
            DomainUserPermission.objects.get_or_create(domain=domain, user=user)

        self.stdout.write(
            self.style.SUCCESS('Successfully granted "%s" for %s' % domains, username)
        )
