# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the list_domains module."""

from io import StringIO

import pytest
from django.core.management import call_command

from httprequest_lego_provider.models import DomainUserPermission


@pytest.mark.django_db
def test_list_domains(domain_user_permissions: list[DomainUserPermission]):
    """
    arrange: given existing domains allowed for an user.
    act: call the list_domains command.
    assert: the list of associated domains is returned in the stdout.
    """
    out = StringIO()
    call_command("list_domains", domain_user_permissions[0].user.username, stdout=out)
    print(out.getvalue())
    assert out.getvalue() == [dup.domain.fqdn for dup in domain_user_permissions]
