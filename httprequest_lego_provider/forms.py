# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Forms."""

from django.forms import CharField, Form


class PresentForm(Form):
    """Form for the present endpoint.

    Attributes:
        fqdn: Fully qualified domain name.
    """

    fqdn = CharField(label="FQDN", max_length=255)


class CleanupForm(Form):
    """Form for the cleanup endpoint.

    Attributes:
        fqdn: Fully qualified domain name.
    """

    fqdn = CharField(label="FQDN", max_length=255)
