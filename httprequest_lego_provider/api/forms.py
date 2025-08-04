# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Forms."""

import re

from django.core.exceptions import ValidationError
from django.forms import CharField, Form


def is_fqdn_compliant(fqdn: str) -> bool:
    """Check if the argument is a valid FQDN.

    Args:
        fqdn: the FQDN to validate.

    Returns:
        if the FQDN is valid.
    """
    return bool(
        re.match(
            (
                r"^(?!.{255}|.{253}[^.])([a-z0-9](?:[-a-z-0-9]{0,61}[a-z0-9])?\.)+"
                r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?[.]?$"
            ),
            fqdn,
            re.IGNORECASE,
        )
    )


class FQDNField(CharField):
    """FQDN field class."""

    def validate(self, value) -> None:
        """Check if value consists only of a valid FQDNs.

        Args:
            value: field value.

        Raises:
            ValidationError: if the value is invalid.
        """
        # Use the parent's handling of required fields, etc.
        super().validate(value)
        if not is_fqdn_compliant(value):
            raise ValidationError(
                message="Please provide a valid FQDN", code="invalid", params={"value": value}
            )

    def to_python(self, value) -> str:
        """Remove the trailing dot from the FQDN if present.

        Args:
            value: field value.

        Returns:
            the FQDN without a trailing dot.
        """
        value = str(value)
        return value.rstrip(".")


class PresentForm(Form):
    """Form for the present endpoint.

    Attributes:
        fqdn: Fully qualified domain name.
        value: Authorization signature for Let's Encrypt.
    """

    fqdn = FQDNField(label="FQDN")
    value = CharField(label="value")


class CleanupForm(Form):
    """Form for the cleanup endpoint.

    Attributes:
        fqdn: Fully qualified domain name.
        value: Authorization signature for Let's Encrypt.
    """

    fqdn = FQDNField(label="FQDN")
    value = CharField(label="value")
