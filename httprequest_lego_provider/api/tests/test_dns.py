# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the dns module."""

from api.dns import (
    parse_repository_url,
)


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
