# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for integration tests."""

import logging
import secrets
import textwrap
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import jubilant
import pytest

if TYPE_CHECKING:
    from opcli.pytest_plugin import CharmPathList

JUJU_WAIT_TIMEOUT = 20 * 60

HTTPREQUEST_LEGO_PROVIDER_APP_NAME = "httprequest-lego-provider"
HTTPREQUEST_LEGO_PROVIDER_IMAGE_NAME = "httprequest-lego-provider"


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", name="charm")
def charm_fixture(charm_paths: dict[str, CharmPathList]) -> Path:
    """Get the built httprequest-lego-provider charm path.

    Returns:
        Path to the built charm.
    """
    return Path(charm_paths[HTTPREQUEST_LEGO_PROVIDER_APP_NAME].path)


@pytest.fixture(scope="session", name="image")
def image_fixture(resource_images: dict[str, str]) -> str:
    """Get the application OCI image."""
    return resource_images[HTTPREQUEST_LEGO_PROVIDER_IMAGE_NAME]


@pytest.fixture(scope="module", name="juju")
def juju_model_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Create a temporary Juju model for testing."""
    if model := request.config.getoption("--model"):
        juju_model = jubilant.Juju(model=model)
        juju_model.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju_model
        return

    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju_model:
        juju_model.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju_model

        if request.session.testsfailed:
            log = juju_model.debug_log(limit=1000)
            logger.debug(log)


@pytest.fixture(scope="module", name="httprequest_lego_provider")
def httprequest_lego_provider_fixture(juju: jubilant.Juju, charm: Path, image: str) -> str:
    """Deploy httprequest-lego-provider."""
    juju.deploy(
        charm,
        app=HTTPREQUEST_LEGO_PROVIDER_APP_NAME,
        config={
            "django-allowed-hosts": "*",
            "django-secret-key": secrets.token_hex(),
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
        resources={"django-app-image": image},
    )
    return HTTPREQUEST_LEGO_PROVIDER_APP_NAME
