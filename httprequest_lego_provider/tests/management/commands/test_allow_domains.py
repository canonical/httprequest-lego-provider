# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the allow_domains module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import DomainUserPermission


@pytest.mark.django_db
def test_allow_domains(user: User, fqdns: list[str]):
    """
    arrange: given a user.
    act: call the allow_domains command.
    assert: new domains are created an associated to the user.
    """
    mixed_prefix_fqdns = fqdns.copy()
    mixed_prefix_fqdns[0] = f"{FQDN_PREFIX}{fqdns[0]}"
    call_command("allow_domains", user.username, *mixed_prefix_fqdns)

    dups = DomainUserPermission.objects.filter(user=user)
    assert [dup.domain.fqdn for dup in dups] == [f"{FQDN_PREFIX}{fqdn}" for fqdn in fqdns]


@pytest.mark.django_db
def test_allow_domains_raises_exception(fqdns: list[str]):
    """
    arrange: do nothing.
    act: call the allow_domains command for a non existing user.
    assert: a CommandError exception is raised.
    """
    with pytest.raises(CommandError):
        call_command("allow_domains", "non-existing-user", *fqdns)
