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
def username() -> str:
    """Provide a default username."""
    return "test_user"


@pytest.fixture(scope="module")
def user_password() -> str:
    """Provide a default user password."""
    return secrets.token_hex()


@pytest.fixture(scope="function")
def user(username: str, user_password: str) -> User:
    """Provide a default user."""
    return User.objects.create_user(username, password=user_password)


@pytest.fixture(scope="function")
def user_auth_token(username: str, user_password: str, user: User) -> str:
    """Provide the auth_token for the default user."""
    return base64.b64encode(bytes(f"{username}:{user_password}", "utf-8")).decode("utf-8")


@pytest.fixture(scope="module")
def admin_username() -> str:
    """Provide an admin username."""
    return "admin"


@pytest.fixture(scope="module")
def admin_user_password() -> str:
    """Provide an admin user password."""
    return secrets.token_hex()


@pytest.fixture(scope="function")
def admin_user(admin_username: str, admin_user_password: str) -> User:
    """Provide an admin user."""
    return User.objects.create_user(username, password=user_password, is_staff=True)


@pytest.fixture(scope="function")
def admin_user_auth_token(admin_username: str, admin_user_password: str, admin_user: User) -> str:
    """Provide the auth_token for the admin user."""
    return base64.b64encode(bytes(f"{admin_username}:{admin_user_password}", "utf-8")).decode(
        "utf-8"
    )


@pytest.fixture(scope="module")
def fqdn():
    """Provide a valid FQDN."""
    yield f"{FQDN_PREFIX}example.com"


@pytest.fixture(scope="function")
def domain(fqdn: str) -> Domain:
    """Provide a valid domain."""
    return Domain.objects.create(fqdn=fqdn)


@pytest.fixture(scope="function")
def domain_user_permission(domain: Domain, user: User) -> DomainUserPermission:
    """Provide a valid domain."""
    return DomainUserPermission.objects.create(domain=domain, user=user)
