# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Create user module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


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
        parser.add_argument("username", type=str)
        parser.add_argument("password", type=str)

    def handle(self, *args, **options):
        """Command handler.

        Args:
            args: args.
            options: options.

        Raises:
            CommandError: Is user is invalid.
        """
        username = options["username"]
        password = options["password"]

        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'User "{username}" already exists. Skipping.')
        except User.DoesNotExist:
            user = User(username=username)
            user.set_password(password)
            try:
                user.full_clean()
            except ValidationError as e:
                raise CommandError(f"Invalid user '{username}': {e.messages}") from e

        user.save()

        self.stdout.write(
            self.style.SUCCESS(f'Created or updated "{username}" with password "{password}"')
        )
