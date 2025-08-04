# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the forms module."""

from api.forms import is_fqdn_compliant


def test_is_fqdn_compliant():
    """
    arrange: do nothing.
    act: do nothing.
    assert: FQDN should be valid.
    """
    assert not is_fqdn_compliant("")
    assert not is_fqdn_compliant("com")
    assert not is_fqdn_compliant("ex..ample.com")
    assert not is_fqdn_compliant("-example.com")
    assert not is_fqdn_compliant("example-.com")
    assert not is_fqdn_compliant("exa$mple.com")
    assert not is_fqdn_compliant("*.example.com")
    assert not is_fqdn_compliant("_acme-challenge.*.example.com")
    assert is_fqdn_compliant("smth.example.com")
    assert is_fqdn_compliant("example.com")
    assert is_fqdn_compliant("example.com.")
