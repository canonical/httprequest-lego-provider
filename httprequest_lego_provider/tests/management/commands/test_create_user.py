# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the create_user module."""

# pylint:disable=imported-auth-user

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command


@pytest.mark.django_db
def test_create_user(username: str, user_password: str):
    """
    arrange: do nothing.
    act: call the create_username command.
    assert: a new user is inserted in the database.
    """
    out = StringIO()
    call_command("create_user", username, user_password, stdout=out)
    user = User.objects.get(username=username)
    assert user.username == username
    assert user.password == user_password
    assert user.password in out.getvalue()
