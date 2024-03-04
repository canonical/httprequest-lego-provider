# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the revoke_domains module."""

import pytest
from django.core.management import call_command

from httprequest_lego_provider.models import DomainUserPermission


@pytest.mark.django_db
def test_revoke_domains(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given a user.
    act: call the revoke_domains command.
    assert: the domains are revoked for the user.
    """
    fqdns = [dup.domain.fqdn for dup in domain_user_permissions]
    call_command("revoke_domains", domain_user_permissions[0].user.username, *fqdns)

    assert not DomainUserPermission.objects.filter(user=domain_user_permissions[0].user)
