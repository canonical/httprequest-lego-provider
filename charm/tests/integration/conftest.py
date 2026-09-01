# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import jubilant
import pytest


@pytest.fixture(scope="module")
def juju(juju: jubilant.Juju) -> jubilant.Juju:
    """Override juju fixture to set wait_timeout.

    Args:
        juju: The Juju object provided by pytest-jubilant.

    Returns:
        The Juju object with wait_timeout configured.
    """
    juju.wait_timeout = 10 * 60
    return juju


@pytest.fixture(scope="module", name="charm")
def charm_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter charm-file.

    Args:
        pytestconfig: pytest Config object.

    Returns:
        Path to the charm file.
    """
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    return charm


@pytest.fixture(scope="module", name="httprequest_lego_provider_image")
def httprequest_lego_provider_image_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter httprequest-lego-provider-image.

    Args:
        pytestconfig: pytest Config object.

    Returns:
        The OCI image reference for the Django app.
    """
    image = pytestconfig.getoption("--httprequest-lego-provider-image")
    if not image:
        raise ValueError("the following arguments are required: --httprequest-lego-provider-image")
    return image
