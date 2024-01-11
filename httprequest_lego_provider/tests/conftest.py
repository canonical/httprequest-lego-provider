# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for unit tests."""

import base64
import secrets

import pytest
from django.contrib.auth.models import User

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import Domain, DomainUserPermission


@pytest.fixture(scope="module")
def username():
    """Provide a default username."""
    yield "test_user"


@pytest.fixture(scope="module")
def user_password():
    """Provide a default user password."""
    yield secrets.token_hex()


@pytest.fixture(scope="function")
def user(username, user_password):
    """Provide a default user."""
    user = User.objects.create_user(username, password=user_password)
    yield user


@pytest.fixture(scope="function")
def user_auth_token(username, user_password, user):
    """Provide the auth_token for the default user."""
    auth_token = base64.b64encode(bytes(f"{username}:{user_password}", "utf-8")).decode("utf-8")
    yield auth_token


@pytest.fixture(scope="module")
def fqdn():
    """Provide a valid FQDN."""
    yield f"{FQDN_PREFIX}example.com"


@pytest.fixture(scope="function")
def domain(fqdn):
    """Provide a valid domain."""
    domain = Domain.objects.create(fqdn=fqdn)
    yield domain


@pytest.fixture(scope="function")
def domain_user_permission(domain, user):
    """Provide a valid domain."""
    domain_user_permission = DomainUserPermission.objects.create(domain=domain, user=user)
    yield domain_user_permission
