# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Models."""

from django.contrib import auth
from django.core.validators import RegexValidator
from django.db import models


class Domain(models.Model):
    """DNS domain.

    Attributes:
        fqdn: fully-qualified domain name.
    """

    fqdn = models.CharField(
        max_length=255,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)",
                message="Enter a valid FQDN.",
                code="invalid_fqdn",
            ),
        ],
    )


class AccessLevel(models.TextChoices):
    """Access levels for the user.

    Attributes:
        SUBDOMAIN: subdomain access level.
        DOMAIN: domain access level.
    """

    SUBDOMAIN = "subdomain"
    DOMAIN = "domain"


class DomainUserPermission(models.Model):
    """Relation between the user and the domains each user can manage.

    Attributes:
        domain: domain.
        user: user.
        text: details.
        access_level: levels of access.
    """

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    user = models.ForeignKey(auth.get_user_model(), on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    access_level = models.CharField(choices=AccessLevel.choices)

    class Meta:
        """Meta options for DomainUserPermission.

        Attributes:
            constraints: unique constraint for user, domain, and access level.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["user", "domain", "access_level"], name="unique_user_domain_accesslevel"
            )
        ]
