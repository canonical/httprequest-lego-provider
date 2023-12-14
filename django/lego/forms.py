# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
"""Forms."""

from django import forms


class PresentForm(forms.Form):
    """Form for the present endpoint.

    Attributes:
        fqdn: Fully qulified domain name.
    """

    fqdn = forms.CharField(label="FQDN", max_length=255)


class CleanupForm(forms.Form):
    """Form for the cleanup endpoint.

    Attributes:
        fqdn: Fully qulified domain name.
    """

    fqdn = forms.CharField(label="FQDN", max_length=255)
