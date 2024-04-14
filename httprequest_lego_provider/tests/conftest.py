# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for unit tests."""

# pylint:disable=unused-argument

import base64
import secrets

import pytest
from django.contrib.auth.models import User

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import Domain, DomainUserPermission


@pytest.fixture(scope="module", name="username")
def username_fixture() -> str:
    """Provide a default username."""
    return "test_user"


@pytest.fixture(scope="module", name="user_password")
def user_password_fixture() -> str:
    """Provide a default user password."""
    return secrets.token_hex()


@pytest.fixture(scope="function", name="user")
def user_fixture(username: str, user_password: str) -> User:
    """Provide a default user."""
    return User.objects.create_user(username, password=user_password)


@pytest.fixture(scope="module", name="other_username")
def other_username_fixture() -> str:
    """Provide another user username."""
    return "other_user"


@pytest.fixture(scope="function", name="other_user")
def other_user_fixture(other_username: str) -> User:
    """Provide another user."""
    return User.objects.create_user(other_username, password=None)


@pytest.fixture(scope="function", name="user_auth_token")
def user_auth_token_fixture(username: str, user_password: str, user: User) -> str:
    """Provide the auth_token for the default user."""
    return base64.b64encode(bytes(f"{username}:{user_password}", "utf-8")).decode("utf-8")


@pytest.fixture(scope="module", name="admin_username")
def admin_username_fixture() -> str:
    """Provide an admin username."""
    return "test_admin_user"


@pytest.fixture(scope="module", name="admin_user_password")
def admin_user_password_fixture() -> str:
    """Provide an admin user password."""
    return secrets.token_hex()


@pytest.fixture(scope="function", name="admin_user")
def admin_user_fixture(admin_username: str, admin_user_password: str) -> User:
    """Provide an admin user."""
    return User.objects.create_user(admin_username, password=admin_user_password, is_staff=True)


@pytest.fixture(scope="function", name="admin_user_auth_token")
def admin_user_auth_token_fixture(
    admin_username: str, admin_user_password: str, admin_user: User
) -> str:
    """Provide the auth_token for the admin user."""
    return base64.b64encode(bytes(f"{admin_username}:{admin_user_password}", "utf-8")).decode(
        "utf-8"
    )


@pytest.fixture(scope="module", name="fqdn")
def fqdn_fixture() -> str:
    """Provide a valid FQDN."""
    return "example.com"


@pytest.fixture(scope="function", name="domain")
def domain_fixture(fqdn: str) -> Domain:
    """Provide a valid domain."""
    return Domain.objects.create(fqdn=f"{FQDN_PREFIX}{fqdn}")


@pytest.fixture(scope="function", name="domains")
def domains_fixture(fqdns: list) -> list:
    """Create all domains and return the list of Domain objects."""
    domains = []
    for fqdn in fqdns:
        domains.append(Domain.objects.create(fqdn=f"{FQDN_PREFIX}{fqdn}"))
    return domains


@pytest.fixture(scope="function", name="domain_user_permission")
def domain_user_permission_fixture(domain: Domain, user: User) -> DomainUserPermission:
    """Provide a valid domain user permission."""
    return DomainUserPermission.objects.create(domain=domain, user=user)


@pytest.fixture(scope="module", name="fqdns")
def fqdns_fixture() -> list[str]:
    """Provide a list of valid FQDNs."""
    return ["some.com", "example2.com", "example.es"]


@pytest.fixture(scope="function", name="domain_user_permissions")
def domain_user_permissions_fixture(fqdns: list[str], user: User) -> list[DomainUserPermission]:
    """Provide list of valid domain user permissions."""
    domains = []
    for fqdn in fqdns:
        domain = Domain.objects.create(fqdn=f"{FQDN_PREFIX}{fqdn}")
        domains.append(domain)
    dups = []
    for domain in domains:
        dup = DomainUserPermission.objects.create(domain=domain, user=user)
        dups.append(dup)
    return dups
