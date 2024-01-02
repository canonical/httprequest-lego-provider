# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the dns module."""

from git import Repo
from unittest.mock import patch, MagicMock
from pathlib import Path
from lego.dns import remove_dns_record, write_dns_record


@patch.object(Path, "exists", False)
@patch.object(Path, "write_text")
@patch.object(Repo, "clone_from")
def test_write_dns_record_if_not_exists(repo_patch, _):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS record doesn't exist.
    act: attempt to write a new DNS record.
    assert: a new file with filename matching the record is committed and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock

    dns_record = "site.example.com"
    write_dns_record(dns_record)

    repo_mock.index.add.assert_called_with([dns_record])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()


@patch.object(Path, "exists", True)
@patch.object(Repo, "clone_from")
def test_write_dns_record_if_exists(repo_patch):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS record exists.
    act: attempt to write a new DNS record.
    assert: no changes are pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock

    dns_record = "site.example.com"
    write_dns_record(dns_record)

    repo_mock.remote(name="origin").push.assert_not_called()


@patch.object(Path, "exists", False)
@patch.object(Repo, "clone_from")
def test_remove_dns_record_if_not_exists(repo_patch):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS doesn't exist.
    act: attempt to delete a new DNS record.
    assert: no changes are pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock

    dns_record = "site.example.com"
    remove_dns_record(dns_record)

    repo_mock.remote(name="origin").push.assert_not_called()


@patch.object(Path, "exists", True)
@patch.object(Path, "unlink")
@patch.object(Repo, "clone_from")
def test_remove_dns_record_if_exists(repo_patch, _):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS exists.
    act: attempt to delete a new DNS record.
    assert: the file with filename matching the record is deleted and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock

    dns_record = "site.example.com"
    remove_dns_record(dns_record)

    repo_mock.index.add.assert_called_with([dns_record])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()