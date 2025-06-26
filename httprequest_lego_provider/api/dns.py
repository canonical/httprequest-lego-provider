# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""DNS utiilities."""

import logging
import subprocess  # nosec B404

logger = logging.getLogger(__name__)

FILENAME_TEMPLATE = "{domain}.domain"
RECORD_CONTENT = "{record} 600 IN TXT \042{value}\042\n"


class HTTPRequestNotifyOutputError(Exception):
    """if an error while notifying the charm."""


class HTTPRequestNotifyTimeoutError(Exception):
    """if an error while notifying the charm."""


class HTTPRequestNotifyProcessError(Exception):
    """if an error while notifying the charm."""


class HTTPRequestPebbleNotFoundError(Exception):
    """if an error while notifying the charm."""


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
        HTTPRequestNotifyOutputError: if an error while notifying the charm.
        HTTPRequestNotifyTimeoutError: if an error while notifying the charm.
        HTTPRequestNotifyProcessError: if an error while notifying the charm.
        HTTPRequestPebbleNotFoundError: if an error while notifying the charm.
    """
    try:
        # Notify the charm that we need to request a DNS record
        output = subprocess.check_output(
            ["/usr/bin/pebble", "notify", "dns.local/write", f"fqdn='{fqdn}'", f"rdata='{rdata}'"],
            stderr=subprocess.STDOUT,  # nosec B603, B607
            timeout=10,
        )

        if b"Error" in output or b"error" in output:
            raise HTTPRequestNotifyOutputError(
                f"Error executing Pebble command: {output.decode('utf-8')}"
            )

        logger.debug("Pebble command executed successfully: %s", output.decode("utf-8"))

    except subprocess.TimeoutExpired as e:
        raise HTTPRequestNotifyTimeoutError(
            f"Timeout executing Pebble command: {e.output.decode('utf-8')}"
        ) from e

    except subprocess.CalledProcessError as e:
        raise HTTPRequestNotifyProcessError(
            "Error executing Pebble command (exit code "
            f"{e.returncode}): {e.output.decode('utf-8')}"
        ) from e

    except FileNotFoundError as e:
        logger.error("Error executing Pebble command: 'pebble' command not found")
        raise HTTPRequestPebbleNotFoundError(
            "Error executing Pebble command: 'pebble' command not found"
        ) from e


def remove_dns_record(fqdn: str) -> None:
    """Delete a DNS record if it exists.

    Args:
        fqdn: the FQDN for which to delete the record.

    Raises:
        HTTPRequestNotifyOutputError: if an error while notifying the charm.
        HTTPRequestNotifyTimeoutError: if an error while notifying the charm.
        HTTPRequestNotifyProcessError: if an error while notifying the charm.
        HTTPRequestPebbleNotFoundError: if an error while notifying the charm.
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
            raise HTTPRequestNotifyOutputError(
                f"Error executing Pebble command: {output.decode('utf-8')}"
            )

        logger.info("Pebble command executed successfully: %s", output.decode("utf-8"))

    except subprocess.TimeoutExpired as e:
        raise HTTPRequestNotifyTimeoutError(
            f"Timeout executing Pebble command: {e.output.decode('utf-8')}"
        ) from e

    except subprocess.CalledProcessError as e:
        raise HTTPRequestNotifyProcessError(
            "Error executing Pebble command (exit code "
            f"{e.returncode}): {e.output.decode('utf-8')}"
        ) from e

    except FileNotFoundError as e:
        raise HTTPRequestPebbleNotFoundError(
            "Error executing Pebble command: 'pebble' command not found"
        ) from e
