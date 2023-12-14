"""Forms."""

from django import forms


class PresentForm(forms.Form):
    """Form for the present endpoint."""

    fqdn = forms.CharField(label="FQDN", max_length=255)


class CleanupForm(forms.Form):
    """Form for the cleanup endpoint."""

    fqdn = forms.CharField(label="FQDN", max_length=255)