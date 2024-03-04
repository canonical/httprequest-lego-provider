from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """Command for user creation."""

    help = "Create an user or update its password."

    def add_arguments(self, parser):
        """Argument parser."""
        parser.add_argument("username", nargs=None, type=str)
        parser.add_argument("password", nargs=None, type=str)

    def handle(self, *args, **options):
        """Command handler."""
        username = options["username"]
        password = options["password"]
        user, _ = User.objects.update_or_create(username=username, password=password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS('Successfully created or updated "%s"' % username)
        )
