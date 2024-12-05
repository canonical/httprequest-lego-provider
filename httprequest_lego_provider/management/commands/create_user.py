# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Create user module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Command for user creation.

    Attrs:
        help: help message to display.
    """

    help = "Create a user or update its password."

    def add_arguments(self, parser):
        """Argument parser.

        Args:
            parser: the cmd line parser.
        """
        parser.add_argument("username", nargs=None, type=str)
        parser.add_argument("password", nargs=None, type=str)

    def handle(self, *args, **options):
        """Command handler.

        Args:
            args: args.
            options: options.
        """
        username = options["username"]
        password = options["password"]
        user, _ = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f'Created or updated "{username}" with password "{password}"')
        )
