# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the allow_domains module."""

# pylint:disable=imported-auth-user

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import DomainUserPermission


@pytest.mark.django_db
def test_allow_domains(user: User, fqdns: list[str]):
    """
    arrange: given a user.
    act: call the allow_domains command.
    assert: new domains are created an associated to the user.
    """
    call_command("allow_domains", user.username, *fqdns)

    dups = DomainUserPermission.objects.filter(user=user)
    assert [dup.domain.fqdn for dup in dups] == [f"{FQDN_PREFIX}{fqdn}" for fqdn in fqdns]
