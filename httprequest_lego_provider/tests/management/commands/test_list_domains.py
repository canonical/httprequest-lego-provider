# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the list_domains module."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

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
    for dup in domain_user_permissions:
        assert dup.domain.fqdn in out.getvalue()


@pytest.mark.django_db
def test_list_domains_raises_exception(fqdns: list[str]):
    """
    arrange: do nothing.
    act: call the list_domains command for a non existing user.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError):
        call_command("allow_domains", "non-existing-user", *fqdns)
