# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import os
import secrets
import textwrap
import typing
from collections.abc import Generator

import jubilant
import pytest

APP_NAME = "httprequest-lego-provider"
POSTGRESQL_APP_NAME = "postgresql-k8s"

@pytest.fixture(scope="module", name="charm")
def charm_fixture(pytestconfig: pytest.Config):
    """Get value from parameter charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if not use_existing:
        assert charm, "--charm-file must be set"
    return charm


@pytest.fixture(scope="session", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.temp_model`."""
    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        return


@pytest.fixture(scope="module", name="httprequest_lego_provider_image")
def httprequest_lego_provider_image_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter httprequest-lego-provider-image."""
    image = pytestconfig.getoption("--httprequest-lego-provider-image")
    if not image:
        raise ValueError("the following arguments are required: --httprequest-lego-provider-image")
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
            log=False,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise
    try:
        juju.deploy(
            POSTGRESQL_APP_NAME,
            channel="14/edge",
            trust=True,
            log=False,
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
        timeout=10 * 60,
    )
    yield APP_NAME
