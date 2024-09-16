# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import pathlib
import typing
from unittest.mock import patch

import ops.testing
import pytest

import chrony
import keychain
from charm import ChronyCharm


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--charm-file", action="store")
    parser.addoption("--httprequest-lego-provider-image", action="store")
