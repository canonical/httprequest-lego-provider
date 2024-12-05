# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the forms module."""

from httprequest_lego_provider.forms import is_fqdn_compliant


def test_is_fqdn_compliant():
    """
    arrange: do nothing.
    act: do nothing.
    assert: FQDN should start with '_acme-challenge' and be valid.
    """
    assert not is_fqdn_compliant("example.com")
    assert not is_fqdn_compliant("smth.example.com")
    assert not is_fqdn_compliant("_acme-challenge.")
    assert not is_fqdn_compliant("com")
    assert not is_fqdn_compliant("_acme-challenge.com")
    assert not is_fqdn_compliant("_acme-challenge1.example.com")
    assert is_fqdn_compliant("_acme-challenge.example.com")
    assert is_fqdn_compliant("_acme-challenge.1example.com")
    assert is_fqdn_compliant("_acme-challenge.example.com.")
