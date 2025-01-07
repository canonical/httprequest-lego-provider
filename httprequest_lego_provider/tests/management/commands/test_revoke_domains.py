# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the revoke_domains module."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import DomainUserPermission


@pytest.mark.django_db
def test_revoke_domains(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given a user.
    act: call the revoke_domains command for a subset of the allowed domains.
    assert: the domains are revoked for the user and the rest are still allowed.
    """
    fqdns = [dup.domain.fqdn for dup in domain_user_permissions]
    prefix_index = len(FQDN_PREFIX)
    revoke_fqdns = [fqdns[0][prefix_index:], fqdns[1]]
    allowed_fqdns = fqdns[2:]
    call_command("revoke_domains", domain_user_permissions[0].user.username, *revoke_fqdns)

    dups = DomainUserPermission.objects.filter(user=domain_user_permissions[0].user)
    assert [dup.domain.fqdn for dup in dups] == allowed_fqdns


@pytest.mark.django_db
def test_revoke_domains_raises_exception(fqdns: list[str]):
    """
    arrange: do nothing.
    act: call the revoke_domains command for a non existing user.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError):
        call_command("revoke_domains", "non-existing-user", *fqdns)
