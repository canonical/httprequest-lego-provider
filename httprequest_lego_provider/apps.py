# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""App."""

from django.apps import AppConfig


class HttpRequestLegoProviderConfig(AppConfig):
    """HTTPRequest Lego Provider app configuration.

    Attributes:
        default_auto_field: default auto-field.
        name: name.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "httprequest_lego_provider"
