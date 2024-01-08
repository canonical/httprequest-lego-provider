# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the dns module."""

import secrets
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import GitCommandError, Repo

from httprequest_lego_provider.dns import DnsSourceUpdateError, remove_dns_record, write_dns_record


@patch.object(Path, "write_text")
@patch.object(Repo, "clone_from")
def test_write_dns_record_raises_exception(repo_patch, _):
    """
    arrange: mock the repo so that it raises a GitCommandError.
    act: attempt to write a new DNS record.
    assert: a DnsSourceUpdateError exception is raised.
    """
    repo_patch.side_effect = GitCommandError("Error executing command")

    dns_record = "site.example.com"
    with pytest.raises(DnsSourceUpdateError):
        write_dns_record(dns_record, secrets.token_hex())


@patch.object(Path, "write_text")
@patch.object(Path, "read_text")
@patch.object(Repo, "clone_from")
def test_write_dns_record(repo_patch, read_patch, write_patch):
    """
    arrange: mock the repo.
    act: attempt to write a new DNS record.
    assert: a new file with filename matching the record is committed and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock
    token = secrets.token_hex()
    read_patch.return_value = (
        "site 600 IN TXT \042sometoken\042\n"
        "site1 600 IN TXT \042sometoken\042\n"
        "site3 600 IN TXT \042sometoken\042\n"
    )

    dns_record = "site.example.com"
    write_dns_record(dns_record, token)

    write_patch.assert_called_once_with(
        (
            "site1 600 IN TXT \042sometoken\042\n"
            "site3 600 IN TXT \042sometoken\042\n"
            "site 600 IN TXT \042{token}\042\n"
        ).format(token=token),
        encoding="utf-8",
    )
    repo_mock.index.add.assert_called_with(["example.com.domain"])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()


@patch.object(Path, "write_text")
@patch.object(Repo, "clone_from")
def test_remove_dns_record_raises_exception(repo_patch, _):
    """
    arrange: mock the repo so that it raises a GitCommandError.
    act: attempt to remove a DNS record.
    assert: a DnsSourceUpdateError exception is raised.
    """
    repo_patch.side_effect = GitCommandError("Error executing command")

    dns_record = "site.example.com"
    with pytest.raises(DnsSourceUpdateError):
        remove_dns_record(dns_record)


@patch.object(Path, "write_text")
@patch.object(Path, "read_text")
@patch.object(Repo, "clone_from")
def test_remove_dns_record(repo_patch, read_patch, write_patch):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS exists.
    act: attempt to delete a new DNS record.
    assert: the file with filename matching the record is emptied and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock
    read_patch.return_value = (
        "site1 600 IN TXT \042sometoken\042\n"
        "site 600 IN TXT \042sometoken\042\n"
        "site3 600 IN TXT \042sometoken\042\n"
    )

    dns_record = "site.example.com"
    remove_dns_record(dns_record)

    write_patch.assert_called_once_with(
        "site1 600 IN TXT \042sometoken\042\nsite3 600 IN TXT \042sometoken\042\n",
        encoding="utf-8",
    )
    repo_mock.index.add.assert_called_with(["example.com.domain"])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()
