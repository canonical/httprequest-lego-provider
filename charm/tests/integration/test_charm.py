# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm Integration tests."""

import logging
import os
import secrets
import textwrap

import jubilant
import pytest

logger = logging.getLogger(__name__)

APP_NAME = "httprequest-lego-provider"
POSTGRESQL_APP_NAME = "postgresql-k8s"
# renovate: depName="postgresql-k8s"
POSTGRESQL_REVISION = 869

LIST_DOMAINS_OUTPUT = """
test:
    domains:
        example.com, sub.example.com
    subdomains:
        example.com
"""


@pytest.fixture(scope="module", name="httprequest_lego_provider_image")
def httprequest_lego_provider_image_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter httprequest-lego-provider-image."""
    image = pytestconfig.getoption("--httprequest-lego-provider-image")
    if not image:
        raise ValueError(
            "the following arguments are required: --httprequest-lego-provider-image"
        )
    return image


@pytest.fixture(scope="module", name="app")
def app_fixture(
    juju: jubilant.Juju,
    charm: str,
    httprequest_lego_provider_image: str,
):
    """Deploy httprequest-lego-provider with postgresql-k8s.

    Args:
        juju: the Juju object.
        charm: path to the charm file.
        httprequest_lego_provider_image: OCI image for the Django app.

    Yields:
        The application name.
    """
    try:
        juju.deploy(
            os.path.abspath(charm),
            app=APP_NAME,
            config={
                "django-allowed-hosts": "*",
                "django-secret-key": secrets.token_hex(),
                "git-repo": (
                    "git+ssh://git@github.com/canonical/httprequest-lego-provider.git@main"
                ),
                "git-ssh-key": textwrap.dedent(
                    """\
                    -----BEGIN OPENSSH PRIVATE KEY-----
                    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
                    QyNTUxOQAAACB7cf7PF5PMxeMnIX2nd5rbG5207jwuccejra8BxXMXwgAAAKj9XL3Y/Vy9
                    2AAAAAtzc2gtZWQyNTUxOQAAACB7cf7PF5PMxeMnIX2nd5rbG5207jwuccejra8BxXMXwg
                    AAAEBcyinYBm2LSuxuOKJwMfgGO572NedBYeGK8XQDyh3yFHtx/s8Xk8zF4ychfad3mtsb
                    nbTuPC5xx6OtrwHFcxfCAAAAIHdlaWktd2FuZ0B3ZWlpLW1hY2Jvb2stYWlyLmxvY2FsAQ
                    IDBAU=
                    -----END OPENSSH PRIVATE KEY-----
                    """
                ),
            },
            resources={"django-app-image": httprequest_lego_provider_image},
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise
    try:
        juju.deploy(
            POSTGRESQL_APP_NAME,
            channel="14/edge",
            revision=POSTGRESQL_REVISION,
            trust=True,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise
    try:
        juju.integrate(APP_NAME, POSTGRESQL_APP_NAME)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise

    juju.wait(
        lambda status: jubilant.all_active(status, APP_NAME, POSTGRESQL_APP_NAME),
        timeout=1200,
    )
    yield APP_NAME


def test_build_and_deploy(app: str, juju: jubilant.Juju):
    """
    arrange: set up the juju model.
    act: deploy the httprequest-lego-provider charm with the postgresql-k8s charm.
    assert: ensure the application transitions to 'active' status after deployment.

    Args:
        app: the application name.
        juju: the Juju object.
    """
    status = juju.status()
    assert status.apps[app].is_active


def test_actions(app: str, juju: jubilant.Juju):
    """
    arrange: deploy the httprequest-lego-provider charm and relate it to the postgresql-k8s charm.
    act: run charm actions on the httprequest-lego-provider charm.
    assert: httprequest-lego-provider should respond to the actions correctly.

    Args:
        app: the application name.
        juju: the Juju object.
    """
    unit_name = list(juju.status().apps[app].units.keys())[0]

    task = juju.run(unit_name, "create-user", {"username": "test"})
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("create-user result: %s", stdout)
    assert "password" in stdout

    task = juju.run(
        unit_name,
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

    task = juju.run(unit_name, "list-domains", {"username": "test"})
    assert "result" in task.results
    stdout = task.results["result"]
    logger.info("list-domains result: %s", stdout)
    assert LIST_DOMAINS_OUTPUT == stdout

    task = juju.run(
        unit_name,
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
