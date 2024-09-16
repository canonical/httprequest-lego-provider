# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm Integration tests."""
import logging
import os
import textwrap

import pytest
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, pytestconfig: pytest.Config):
    """
    arrange: set up the juju model.
    act: deploy the httprequest-lego-provider charm with the postgresql-k8s charm.
    assert: ensure the application transitions to 'active' status after deployment.
    """
    charm = pytestconfig.getoption("--charm-file")
    if not charm:
        charm = await ops_test.build_charm("./charm")
    assert ops_test.model
    django_image = pytestconfig.getoption("--httprequest-lego-provider-image")
    assert django_image
    await ops_test.model.deploy(
        os.path.abspath(charm),
        config={
            "git-repo": "git+ssh://git@github.com/canonical/httprequest-lego-provider.git@main",
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
        resources={"django-app-image": django_image},
    )
    await ops_test.model.deploy("postgresql-k8s", channel="14/stable", trust=True)
    await ops_test.model.integrate("httprequest-lego-provider", "postgresql-k8s")
    await ops_test.model.wait_for_idle(timeout=1200, status="active", idle_period=60)


async def test_actions(run_action):
    """
    arrange: deploy the httprequest-lego-provider charm and related it to the postgresql-k8s charm.
    act: run charm actions on the httprequest-lego-provider charm.
    assert: httprequest-lego-provider should response to the action correctly.
    """
    result = await run_action("httprequest-lego-provider", "create-user", username="test")
    assert "result" in result
    stdout = result["result"]
    logger.info("create-user result: %s", stdout)
    assert "password" in stdout
    result = await run_action(
        "httprequest-lego-provider", "allow-domains", username="test", domains="example.com"
    )
    assert "result" in result
    stdout = result["result"]
    logger.info("allow-domains result: %s", stdout)
    assert "example.com" in stdout
