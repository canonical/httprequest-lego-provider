# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm Integration tests."""
import logging

import jubilant

logger = logging.getLogger(__name__)

POSTGRESQL_APP_NAME = "postgresql-k8s"

LIST_DOMAINS_OUTPUT = """
test:
    domains:
        example.com, sub.example.com
    subdomains:
        example.com
"""


def test_actions(juju: jubilant.Juju, httprequest_lego_provider: str):
    """Run the HTTP request Lego provider actions.

    arrange: deploy the httprequest-lego-provider charm and relate it to the postgresql-k8s charm.
    act: run charm actions on the httprequest-lego-provider charm.
    assert: httprequest-lego-provider should respond to the actions correctly.
    """
    juju.deploy(POSTGRESQL_APP_NAME, channel="14/stable", trust=True)
    juju.integrate(httprequest_lego_provider, POSTGRESQL_APP_NAME)
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            httprequest_lego_provider,
            POSTGRESQL_APP_NAME,
        ),
        error=jubilant.any_error,
    )

    task = juju.run(
        f"{httprequest_lego_provider}/leader",
        "create-user",
        {"username": "test"},
    )
    result = task.results
    assert "result" in result
    stdout = result["result"]
    logger.info("create-user result: %s", stdout)
    assert "password" in stdout

    task = juju.run(
        f"{httprequest_lego_provider}/leader",
        "allow-domains",
        {
            "username": "test",
            "domains": "example.com,sub.example.com",
            "subdomains": "example.com",
        },
    )
    result = task.results
    assert "result" in result
    stdout = result["result"]
    logger.info("allow-domains result: %s", stdout)
    assert "Successfully granted access to all domains" in stdout

    task = juju.run(
        f"{httprequest_lego_provider}/leader",
        "list-domains",
        {"username": "test"},
    )
    result = task.results
    assert "result" in result
    stdout = result["result"]
    logger.info("list-domains result: %s", stdout)
    assert LIST_DOMAINS_OUTPUT == stdout

    task = juju.run(
        f"{httprequest_lego_provider}/leader",
        "revoke-domains",
        {
            "username": "test",
            "subdomains": "example.com",
        },
    )
    result = task.results
    assert "result" in result
    stdout = result["result"]
    logger.info("revoke-domains result: %s", stdout)
    assert "Successfully removed access to the domains" in stdout
