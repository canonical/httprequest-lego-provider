from django import forms


class PresentForm(forms.Form):
    fqdn = forms.CharField(label="FQDN", max_length=255)

class CleanupForm(forms.Form):
    fqdn = forms.CharField(label="FQDN", max_length=255)