# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""DNS utiilities."""

import logging
import subprocess  # nosec B404

logger = logging.getLogger(__name__)

FILENAME_TEMPLATE = "{domain}.domain"
RECORD_CONTENT = "{record} 600 IN TXT \042{value}\042\n"


class DnsSourceUpdateError(Exception):
    """Exception for DNS update errors."""


def _get_domain_and_subdomain_from_fqdn(fqdn: str) -> tuple[str, str]:
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


def write_dns_record(fqdn: str, rdata: str) -> None:
    """Write a DNS record.

    Args:
        fqdn: the FQDN for which to add a record.
        rdata: ACME challenge for DNS record to add.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    try:
        # Notify the charm that we need to request a DNS record
        output = subprocess.check_output(
            ["/usr/bin/pebble", "notify", "dns.local/write", f"fqdn='{fqdn}'", f"rdata='{rdata}'"],
            stderr=subprocess.STDOUT,  # nosec B603, B607
            timeout=10,
        )

        if b"Error" in output or b"error" in output:
            raise DnsSourceUpdateError(f"Error executing Pebble command: {output.decode('utf-8')}")
        logger.info("Pebble command executed successfully: %s", output.decode("utf-8"))

    except subprocess.TimeoutExpired as e:
        raise DnsSourceUpdateError(
            f"Timeout executing Pebble command: {e.output.decode('utf-8')}"
        ) from e

    except subprocess.CalledProcessError as e:
        raise DnsSourceUpdateError(
            "Error executing Pebble command (exit code "
            f"{e.returncode}): {e.output.decode('utf-8')}"
        ) from e

    except FileNotFoundError:
        logger.error("Error executing Pebble command: 'pebble' command not found")


def remove_dns_record(fqdn: str) -> None:
    """Delete a DNS record if it exists.

    Args:
        fqdn: the FQDN for which to delete the record.

    Raises:
        DnsSourceUpdateError: if an error while updating the repository occurs.
    """
    try:
        # Notify the charm that we need to remove a DNS record
        output = subprocess.check_output(
            [
                "/usr/bin/pebble",
                "notify",
                "dns.local/remove",
                f"fqdn='{fqdn}'",
            ],
            stderr=subprocess.STDOUT,
            timeout=10,
        )  # nosec B603, B607

        if b"Error" in output or b"error" in output:
            raise DnsSourceUpdateError(f"Error executing Pebble command: {output.decode('utf-8')}")
        logger.info("Pebble command executed successfully: %s", output.decode("utf-8"))

    except subprocess.TimeoutExpired as e:
        raise DnsSourceUpdateError(
            f"Timeout executing Pebble command: {e.output.decode('utf-8')}"
        ) from e

    except subprocess.CalledProcessError as e:
        raise DnsSourceUpdateError(
            "Error executing Pebble command (exit code "
            f"{e.returncode}): {e.output.decode('utf-8')}"
        ) from e

    except FileNotFoundError as e:
        raise DnsSourceUpdateError(
            "Error executing Pebble command: 'pebble' command not found"
        ) from e
