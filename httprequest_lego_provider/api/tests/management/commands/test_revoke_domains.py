# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the revoke_domains module."""

import pytest
from api.models import DomainUserPermission
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_domains_only(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given a user.
    act: call the revoke_domains command for a subset of the allowed domains only.
    assert: the domains are revoked for the user and the rest are still allowed.
    """
    fqdns = [dup.domain.fqdn for dup in domain_user_permissions]
    revoke_fqdns = [fqdns[0], fqdns[1]]
    allowed_fqdns = fqdns[2:]
    call_command(
        "revoke_domains",
        domain_user_permissions[0].user.username,
        "--domains",
        ",".join(revoke_fqdns),
    )

    dups = DomainUserPermission.objects.filter(user=domain_user_permissions[0].user)
    assert [dup.domain.fqdn for dup in dups] == allowed_fqdns


@pytest.mark.django_db
def test_subdomains_only(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given a user.
    act: call the revoke_domains command for a subset of the allowed subdomains only.
    assert: the domains are revoked for the user and the rest are still allowed.
    """
    fqdns = [dup.domain.fqdn for dup in domain_user_permissions]
    revoke_fqdns = [fqdns[3], fqdns[4]]
    allowed_fqdns = fqdns[0:3] + fqdns[5:]
    call_command(
        "revoke_domains",
        domain_user_permissions[0].user.username,
        "--subdomains",
        ",".join(revoke_fqdns),
    )

    dups = DomainUserPermission.objects.filter(user=domain_user_permissions[0].user)
    assert [dup.domain.fqdn for dup in dups] == allowed_fqdns


@pytest.mark.django_db
def test_domains_and_subdomains(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given a user.
    act: call the revoke_domains command for the remaining allowed domains and subdomains.
    assert: the domains are revoked for the user.
    """
    fqdns = [dup.domain.fqdn for dup in domain_user_permissions]
    revoke_domains = ",".join([fqdns[0], fqdns[1]])
    revoke_subdomains = ",".join([fqdns[3], fqdns[4]])
    call_command(
        "revoke_domains",
        domain_user_permissions[0].user.username,
        "--domains",
        revoke_domains,
        "--subdomains",
        revoke_subdomains,
    )

    dups = DomainUserPermission.objects.filter(user=domain_user_permissions[0].user)
    assert [dup.domain.fqdn for dup in dups] == [fqdns[2], fqdns[5]]


@pytest.mark.django_db
def test_revoke_domains_raises_exception(fqdns: list[str]):
    """
    arrange: do nothing.
    act: call the revoke_domains command for a non existing user.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError):
        call_command("revoke_domains", "non-existing-user", *fqdns)


@pytest.mark.django_db
def test_revoke_domains_fails(domain_user_permissions):
    """
    arrange: do nothing.
    act: call the revoke_domains command for a existing user and non existing domain.
    assert: the command fails.
    """
    with pytest.raises(CommandError):
        call_command(
            "revoke_domains",
            domain_user_permissions[0].user.username,
            "--domains",
            "non-existing-domain.co.uk",
        )
