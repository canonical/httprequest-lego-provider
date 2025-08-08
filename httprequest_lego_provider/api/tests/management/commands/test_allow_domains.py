# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the allow_domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

import pytest
from api.models import AccessLevel, DomainUserPermission
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_domains_only(user: User, fqdns: list[str]):
    """
    arrange: given a user.
    act: call the allow_domains command with domains only.
    assert: new domains are created an associated to the user.
    """
    call_command("allow_domains", user.username, "--domains", ",".join(fqdns))

    dups = DomainUserPermission.objects.filter(user=user)
    assert [dup.domain.fqdn for dup in dups] == [fqdn for fqdn in fqdns]
    assert [dup.access_level for dup in dups] == [AccessLevel.DOMAIN for _ in fqdns]


@pytest.mark.django_db
def test_subdomains_only(user: User, fqdns: list[str]):
    """
    arrange: given a user.
    act: call the allow_domains command with subdomains only.
    assert: user is associated with the right access for the domains.
    """
    call_command("allow_domains", user.username, "--subdomains", ",".join(fqdns))

    dups = DomainUserPermission.objects.filter(user=user)
    assert [dup.domain.fqdn for dup in dups] == [fqdn for fqdn in fqdns]
    assert [dup.access_level for dup in dups] == [AccessLevel.SUBDOMAIN for _ in fqdns]


@pytest.mark.django_db
def test_domains_and_subdomains(user: User, fqdns: list[str]):
    """
    arrange: given a user.
    act: call the allow_domains command with domains and subdomains options.
    assert: user is associated with the right access for the domains.
    """
    call_command(
        "allow_domains",
        user.username,
        "--domains",
        ",".join(fqdns),
        "--subdomains",
        ",".join(fqdns),
    )

    dups = DomainUserPermission.objects.filter(user=user)
    assert [dup.domain.fqdn for dup in dups] == [fqdn for fqdn in fqdns] * 2
    assert [dup.access_level for dup in dups] == [AccessLevel.DOMAIN for _ in fqdns] + [
        AccessLevel.SUBDOMAIN for _ in fqdns
    ]


@pytest.mark.django_db
def test_allow_domains_raises_exception_invalid_user(fqdns: list[str]):
    """
    arrange: do nothing.
    act: call the allow_domains command for a non existing user.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError) as exc_info:
        call_command("allow_domains", "non-existing-user", "--domains", ",".join(fqdns))
    assert 'User "non-existing-user" does not exist' in str(exc_info.value)


@pytest.mark.django_db
def test_allow_domains_raises_exception_invalid_domain(user: User):
    """
    arrange: do nothing.
    act: call the allow_domains command with an invalid domain.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError) as exc_info:
        call_command("allow_domains", user, "--domains", "invalid_fqdn")
    assert "Enter a valid FQDN" in str(exc_info.value)
