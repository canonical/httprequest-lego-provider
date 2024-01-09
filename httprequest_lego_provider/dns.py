# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""DNS utiilities."""

import io
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple

from git import Git, GitCommandError, Repo

from .settings import DNS_REPOSITORY_URL, SSH_IDENTITY_FILE

FILENAME_TEMPLATE = "{domain}.domain"
SPLIT_DNS_REPOSITORY_URL = DNS_REPOSITORY_URL.rsplit("@", 1)
REPOSITORY_BASE_URL = SPLIT_DNS_REPOSITORY_URL[0]
REPOSITORY_BRANCH = SPLIT_DNS_REPOSITORY_URL[1] if len(SPLIT_DNS_REPOSITORY_URL) > 1 else None
RECORD_CONTENT = "{record} 600 IN TXT \042{value}\042\n"
SSH_EXECUTABLE = f"ssh -i {SSH_IDENTITY_FILE}"


class DnsSourceUpdateError(Exception):
    """Exception for DNS update errors."""


def _get_domain_and_subdomain_from_fqdn(fqdn: str) -> Tuple[str, str]:
    """Get the domain and subdomain for the FQDN record provided.

    Args:
        fqdn: Fully quallified domain name.

    Returns:
        the domain and subdomain for the FQDN provided.
    """
    splitted_record = fqdn.split(".")
    return (
        ".".join(splitted_record[-2:]),
        ".".join(splitted_record[:-2]) if len(splitted_record) > 2 else ".",
    )


def _line_matches_subdomain(line: str, subdomain: str) -> bool:
    """Check if the line in bind9 format corresponds to a given subdomain.

    Args:
        line: the line in binbd9 format.
        subdomain: the subdomain to compare with.

    Returns:
        true if the subdomain matches the line.
    """
    return not line.strip().startswith(";") and bool(line.split()) and line.split()[0] == subdomain


def write_dns_record(fqdn: str, value: str) -> None:
    """Write a DNS record following the canonical-is-dns-configs specs if it doesn't exist.

    Args:
        fqdn: the FQDN for which to add a record.
        value: ACME challenge for DNS record to add.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    with TemporaryDirectory() as tmp_dir, Git().custom_environment(GIT_SSH_COMMAND=SSH_EXECUTABLE):
        try:
            repo = Repo.clone_from(REPOSITORY_BASE_URL, tmp_dir, branch=REPOSITORY_BRANCH)
            domain, subdomain = _get_domain_and_subdomain_from_fqdn(fqdn)
            filename = FILENAME_TEMPLATE.format(domain=domain)
            dns_record_file = Path(f"{repo.working_tree_dir}/{filename}")
            content = dns_record_file.read_text("utf-8")
            new_content = []
            for line in io.StringIO(content):
                if not _line_matches_subdomain(line, subdomain):
                    new_content.append(line)
            new_content.append(RECORD_CONTENT.format(record=subdomain, value=value))
            dns_record_file.write_text("".join(new_content), encoding="utf-8")
            repo.index.add([filename])
            repo.git.commit("-m", f"Add {fqdn} record")
            repo.remote(name="origin").push()
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError from ex


def remove_dns_record(fqdn: str) -> None:
    """Delete a DNS record following the canonical-is-dns-configs specs if it exists.

    Args:
        fqdn: the FQDN for which to delete the record.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    with TemporaryDirectory() as tmp_dir, Git().custom_environment(GIT_SSH_COMMAND=SSH_EXECUTABLE):
        try:
            repo = Repo.clone_from(REPOSITORY_BASE_URL, tmp_dir, branch=REPOSITORY_BRANCH)
            domain, subdomain = _get_domain_and_subdomain_from_fqdn(fqdn)
            filename = FILENAME_TEMPLATE.format(domain=domain)
            dns_record_file = Path(f"{repo.working_tree_dir}/{filename}")
            content = dns_record_file.read_text("utf-8")
            new_content = []
            for line in io.StringIO(content):
                if not _line_matches_subdomain(line, subdomain):
                    new_content.append(line)
            dns_record_file.write_text("".join(new_content), encoding="utf-8")
            repo.index.add([filename])
            repo.git.commit("-m", f"Remove {fqdn} record")
            repo.remote(name="origin").push()
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError from ex
