# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the create_user module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_create_user(username: str, user_password: str):
    """
    arrange: do nothing.
    act: call the create_user command.
    assert: a new user is inserted in the database.
    """
    out = StringIO()
    call_command("create_user", username, user_password, stdout=out)
    user = User.objects.get(username=username)
    assert user.username == username
    assert user.check_password(user_password)
    assert user_password in out.getvalue()


@pytest.mark.django_db
def test_create_user_invalid_username(user_password: str):
    """
    arrange: do nothing.
    act: call the create_user command with invalid username.
    assert: CommandError is raised.
    """
    with pytest.raises(CommandError) as exc_info:
        call_command("create_user", "", user_password)

    assert "Invalid user" in str(exc_info.value)
