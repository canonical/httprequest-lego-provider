# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the dns module."""

import secrets
from pathlib import Path
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
from api.dns import (
    DnsSourceUpdateError,
    parse_repository_url,
    remove_dns_record,
    write_dns_record,
)
from git import GitCommandError, Repo


@patch.object(Path, "write_text")
@patch.object(Repo, "clone_from")
@patch("api.dns.GIT_REPO_URL", "git+ssh://user@git.server/repo_name")
def test_write_dns_record_raises_exception(repo_patch: Mock, _):
    """
    arrange: mock the repo so that it raises a GitCommandError.
    act: attempt to write a new DNS record.
    assert: a DnsSourceUpdateError exception is raised.
    """
    repo_patch.side_effect = GitCommandError("Error executing command")

    fqdn = "site.example.com"

    with pytest.raises(DnsSourceUpdateError):
        write_dns_record(fqdn, secrets.token_hex())


@pytest.mark.parametrize(
    "fqdn,record",
    [
        ("site.example.com", "site 600 IN TXT \042{token}\042\n"),
        ("sïte.example.com", "sïte 600 IN TXT \042{token}\042\n"),
        ("example.com", ". 600 IN TXT \042{token}\042\n"),
        ("some.other.site.example.com", "some.other.site 600 IN TXT \042{token}\042\n"),
    ],
)
@patch.object(Path, "write_text")
@patch.object(Path, "read_text")
@patch.object(Repo, "clone_from")
@patch("api.dns.GIT_REPO_URL", "git+ssh://user@git.server/repo_name@lego")
def test_write_dns_record(
    repo_patch: Mock, read_patch: Mock, write_patch: Mock, fqdn: str, record: str
):
    """
    arrange: mock the repo.
    act: attempt to write a new DNS record.
    assert: a new file with filename matching the record is committed and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock
    token = secrets.token_hex()
    read_patch.return_value = (
        "site2 600 IN TXT \042sometoken\042\n"
        "sïte1 600 IN TXT \042sometoken\042\n"
        "site3 600 IN TXT \042sometoken\042\n"
    )
    write_dns_record(fqdn, token)

    repo_patch.assert_called_once_with("git+ssh://user@git.server/repo_name", ANY, branch="lego")
    repo_mock.config_writer().set_value.assert_called_once_with("user", "name", "user")
    write_patch.assert_called_once_with(
        (
            "site2 600 IN TXT \042sometoken\042\n"
            "sïte1 600 IN TXT \042sometoken\042\n"
            "site3 600 IN TXT \042sometoken\042\n" + record
        ).format(token=token),
        encoding="utf-8",
    )
    repo_mock.index.add.assert_called_with(["example.com.domain"])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()


@patch.object(Path, "write_text")
@patch.object(Repo, "clone_from")
@patch("api.dns.GIT_REPO_URL", "git+ssh://user@git.server/repo_name")
def test_remove_dns_record_raises_exception(repo_patch: Mock, _):
    """
    arrange: mock the repo so that it raises a GitCommandError.
    act: attempt to remove a DNS record.
    assert: a DnsSourceUpdateError exception is raised.
    """
    repo_patch.side_effect = GitCommandError("Error executing command")

    fqdn = "site.example.com"

    with pytest.raises(DnsSourceUpdateError):
        remove_dns_record(fqdn)


@pytest.mark.parametrize(
    "fqdn,record",
    [
        ("site.example.com", "site 600 IN TXT \042{token}\042\n"),
        ("sïte.example.com", "sïte 600 IN TXT \042{token}\042\n"),
        ("example.com", ". 600 IN TXT \042{token}\042\n"),
        ("some.other.site.example.com", "some.other.site 600 IN TXT \042{token}\042\n"),
    ],
)
@patch.object(Path, "write_text")
@patch.object(Path, "read_text")
@patch.object(Repo, "clone_from")
@patch("api.dns.GIT_REPO_URL", "git+ssh://user@git.server/repo_name")
def test_remove_dns_record(
    repo_patch: Mock, read_patch: Mock, write_patch: Mock, fqdn: str, record: str
):
    """
    arrange: mock the repo and filesystem so that the file matching a DNS exists.
    act: attempt to delete a new DNS record.
    assert: the file with filename matching the record is emptied and pushed to the repository.
    """
    repo_mock = MagicMock(spec=Repo)
    repo_patch.return_value = repo_mock
    read_patch.return_value = (
        "site1 600 IN TXT \042sometoken\042\n" + record + "site3 600 IN TXT \042sometoken\042\n"
    )

    remove_dns_record(fqdn)

    repo_patch.assert_called_once_with("git+ssh://user@git.server/repo_name", ANY, branch=None)
    repo_mock.config_writer().set_value.assert_called_once_with("user", "name", "user")
    write_patch.assert_called_once_with(
        "site1 600 IN TXT \042sometoken\042\nsite3 600 IN TXT \042sometoken\042\n",
        encoding="utf-8",
    )
    repo_mock.index.add.assert_called_with(["example.com.domain"])
    repo_mock.git.commit.assert_called_once()
    repo_mock.remote(name="origin").push.assert_called_once()


def test_parse_repository_url():
    """
    arrange: do nothing.
    act: given a set of valid repository connection strings.
    assert: the connection strings are parsed successfully.
    """
    user, url, branch = parse_repository_url("git+ssh://user@git.server/repo_name")
    assert user == "user"
    assert url == "git+ssh://user@git.server/repo_name"
    assert branch is None
    user, url, branch = parse_repository_url("git+ssh://user1@git.server:8080/repo_name@main")
    assert user == "user1"
    assert url == "git+ssh://user1@git.server:8080/repo_name"
    assert branch == "main"
