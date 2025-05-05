# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the dns module."""

import subprocess
from unittest.mock import MagicMock

from api.dns import remove_dns_record, write_dns_record


def test_write_dns_record_success(monkeypatch, caplog):
    """Test successful execution of write_dns_record."""
    mock_check_output = MagicMock(return_value=b"Success")
    monkeypatch.setattr("subprocess.check_output", mock_check_output)

    write_dns_record("example.com", "some_rdata")

    mock_check_output.assert_called_once_with(
        [
            "/usr/bin/pebble",
            "notify",
            "dns.local/write",
            "fqdn='example.com'",
            "rdata='some_rdata'",
        ],
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    assert "Pebble command executed successfully: Success" in caplog.text


def test_remove_dns_record_success(monkeypatch, caplog):
    """Test successful execution of remove_dns_record."""
    mock_check_output = MagicMock(return_value=b"Success")
    monkeypatch.setattr("subprocess.check_output", mock_check_output)

    remove_dns_record("example.com")

    mock_check_output.assert_called_once_with(
        ["/usr/bin/pebble", "notify", "dns.local/remove", "fqdn='example.com'"],
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    assert "Pebble command executed successfully: Success" in caplog.text
