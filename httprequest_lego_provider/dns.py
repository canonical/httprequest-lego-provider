# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""DNS utiilities."""

from pathlib import Path
from tempfile import TemporaryDirectory

from git import Git, GitCommandError, Repo

from .settings import DNS_REPOSITORY_URL, SSH_IDENTITY_FILE

FILENAME_SUFFIX = ".domain"
SPLIT_DNS_REPOSITORY_URL = DNS_REPOSITORY_URL.rsplit("@", 1)
REPOSITORY_BASE_URL = SPLIT_DNS_REPOSITORY_URL[0]
REPOSITORY_BRANCH = SPLIT_DNS_REPOSITORY_URL[1] if len(SPLIT_DNS_REPOSITORY_URL) > 1 else None
RECORD_CONTENT = ". 600 IN TXT \042{value}\042"
SSH_EXECUTABLE = f"ssh -i {SSH_IDENTITY_FILE}"


class DnsSourceUpdateError(Exception):
    """Exception for DNS update errors."""


def write_dns_record(dns_record: str, value: str) -> None:
    """Write a DNS record following the canonical-is-dns-configs specs if it doesn't exist.

    Args:
        dns_record: the DNS record to add.
        value: signning key for DNS record to add.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    with TemporaryDirectory() as tmp_dir, Git().custom_environment(GIT_SSH_COMMAND=SSH_EXECUTABLE):
        try:
            repo = Repo.clone_from(REPOSITORY_BASE_URL, tmp_dir, branch=REPOSITORY_BRANCH)
            dns_record_file = Path(f"{repo.working_tree_dir}/{dns_record}{FILENAME_SUFFIX}")
            dns_record_file.write_text(RECORD_CONTENT.format(value=value), encoding="utf-8")
            repo.index.add([f"{dns_record}{FILENAME_SUFFIX}"])
            repo.git.commit("-m", f"Add {dns_record} record")
            repo.remote(name="origin").push()
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError from ex


def remove_dns_record(dns_record: str) -> None:
    """Delete a DNS record following the canonical-is-dns-configs specs if it exists.

    Args:
        dns_record: the DNS record to delete.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    with TemporaryDirectory() as tmp_dir, Git().custom_environment(GIT_SSH_COMMAND=SSH_EXECUTABLE):
        try:
            repo = Repo.clone_from(REPOSITORY_BASE_URL, tmp_dir, branch=REPOSITORY_BRANCH)
            dns_record_file = Path(f"{repo.working_tree_dir}/{dns_record}{FILENAME_SUFFIX}")
            if dns_record_file.exists():
                dns_record_file.write_text("", encoding="utf-8")
                repo.index.add([f"{dns_record}{FILENAME_SUFFIX}"])
                repo.git.commit("-m", f"Remove {dns_record} record")
                repo.remote(name="origin").push()
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError from ex
