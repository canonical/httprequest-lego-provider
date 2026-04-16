# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm Integration tests."""

import logging

import jubilant

logger = logging.getLogger(__name__)
from conftest import APP_NAME

UNIT_NAME = f"{APP_NAME}/0"

LIST_DOMAINS_OUTPUT = """
test:
    domains:
        example.com, sub.example.com
    subdomains:
        example.com
"""


def test_actions(app: str, juju: jubilant.Juju):
    """
    arrange: deploy the httprequest-lego-provider charm and relate it to the postgresql-k8s charm.
    act: run charm actions on the httprequest-lego-provider charm.
    assert: httprequest-lego-provider should respond to the actions correctly.

    Args:
        app: the application name.
        juju: the Juju object.
    """
    task = juju.run(UNIT_NAME, "create-user", {"username": "test"})
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("create-user result: %s", stdout)
    assert "password" in stdout

    task = juju.run(
        UNIT_NAME,
        "allow-domains",
        {
            "username": "test",
            "domains": "example.com,sub.example.com",
            "subdomains": "example.com",
        },
    )
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("allow-domains result: %s", stdout)
    assert "Successfully granted access to all domains" in stdout

    task = juju.run(UNIT_NAME, "list-domains", {"username": "test"})
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("list-domains result: %s", stdout)
    assert LIST_DOMAINS_OUTPUT == stdout

    task = juju.run(
        UNIT_NAME,
        "revoke-domains",
        {
            "username": "test",
            "subdomains": "example.com",
        },
    )
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("revoke-domains result: %s", stdout)
    assert "Successfully removed access to the domains" in stdout
