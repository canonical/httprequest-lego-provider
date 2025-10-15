# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""DNS utiilities."""

import io
import logging
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple

from git import GitCommandError, Repo

from .settings import GIT_REPO_URL

logger = logging.getLogger(__name__)

FILENAME_TEMPLATE = "{domain}.domain"
RECORD_CONTENT = "{record} 600 IN TXT \042{value}\042\n"


class DnsSourceUpdateError(Exception):
    """Exception for DNS update errors."""


def parse_repository_url(repository_url: str) -> Tuple[str, str, str | None]:
    """Get the parsed connection details from the repository connection string.

    Args:
        repository_url: the repository's connection string.

    Returns:
        the repository user, url and branch.
    """
    splitted_url = repository_url.split("@")
    user = splitted_url[0].split("//")[1]
    base_url = "@".join(splitted_url[:2])
    branch = splitted_url[2] if len(splitted_url) > 2 else None
    return user, base_url, branch


def _get_domain_and_subdomain_from_fqdn(fqdn: str) -> Tuple[str, str]:
    """Get the domain and subdomain for the FQDN record provided.

    Args:
        fqdn: Fully qualified domain name.

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
        line: the line in bind9 format.
        subdomain: the subdomain to compare with.

    Returns:
        true if the subdomain matches the line.
    """
    return not line.strip().startswith(";") and bool(line.split()) and line.split()[0] == subdomain


def _remove_subdomain_entries_from_file_content(
    content: Iterable[str], subdomain: str
) -> List[str]:
    """Remove from the file the entries matching a subdomain.

    Args:
        content: the file content.
        subdomain: the subdomain for which to filter out the entries.

    Returns:
        the content excluding the entries for the  subdomain.
    """
    new_content = []
    for line in content:
        if not _line_matches_subdomain(line, subdomain):
            new_content.append(line)
        else:
            logging.error("Subdomain %s already present as a DNS record.", subdomain)
    return new_content


def write_dns_record(fqdn: str, value: str) -> None:  # pylint: disable=too-many-locals
    """Write a DNS record.

    Args:
        fqdn: the FQDN for which to add a record.
        value: ACME challenge for DNS record to add.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    user, base_url, branch = parse_repository_url(GIT_REPO_URL)
    with TemporaryDirectory() as tmp_dir:
        try:
            repo = Repo.clone_from(base_url, tmp_dir, branch=branch)
            config_writer = repo.config_writer()
            config_writer.set_value("user", "name", user)
            config_writer.release()
            domain, subdomain = _get_domain_and_subdomain_from_fqdn(fqdn)
            filename = FILENAME_TEMPLATE.format(domain=domain)
            dns_record_file = Path(f"{repo.working_tree_dir}/{filename}")
            content = dns_record_file.read_text("utf-8")
            new_content = _remove_subdomain_entries_from_file_content(
                io.StringIO(content), subdomain
            )
            new_content.append(RECORD_CONTENT.format(record=subdomain, value=value))
            dns_record_file.write_text("".join(new_content), encoding="utf-8")
            repo.index.add([filename])
            repo.git.commit("-m", f"Add {fqdn} record")
            repo.remote(name="origin").push()
        except FileNotFoundError as exc:
            raise DnsSourceUpdateError(
                f"{filename} file not found in git repository. Is this site configured for DNS?"
            ) from exc
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError(str(ex)) from ex


def remove_dns_record(fqdn: str) -> None:
    """Delete a DNS record if it exists.

    Args:
        fqdn: the FQDN for which to delete the record.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    user, base_url, branch = parse_repository_url(GIT_REPO_URL)
    with TemporaryDirectory() as tmp_dir:
        try:
            repo = Repo.clone_from(base_url, tmp_dir, branch=branch)
            config_writer = repo.config_writer()
            config_writer.set_value("user", "name", user)
            config_writer.release()
            domain, subdomain = _get_domain_and_subdomain_from_fqdn(fqdn)
            filename = FILENAME_TEMPLATE.format(domain=domain)
            dns_record_file = Path(f"{repo.working_tree_dir}/{filename}")
            content = dns_record_file.read_text("utf-8")
            new_content = _remove_subdomain_entries_from_file_content(
                io.StringIO(content), subdomain
            )
            dns_record_file.write_text("".join(new_content), encoding="utf-8")
            repo.index.add([filename])
            repo.git.commit("-m", f"Remove {fqdn} record")
            repo.remote(name="origin").push()
        except FileNotFoundError as exc:
            raise DnsSourceUpdateError(
                f"{filename} file not found in git repository. Is this site configured for DNS?"
            ) from exc
        except (GitCommandError, ValueError) as ex:
            raise DnsSourceUpdateError(str(ex)) from ex
