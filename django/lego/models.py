# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Models."""

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models

audit_log_status_choices = (
    ("created", "created"),
    ("updated", "updated"),
    ("deleted", "deleted"),
)


class Domain(models.Model):
    """DNS domain.

    Attributes:
        fqdn: fully-qualified domain name.
    """

    fqdn = models.CharField(
        max_length=200,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)',
                message="Enter a valid FQDN.",
                code="invalid_fqdn",
            ),
        ],)


class DomainUserPermission(models.Model):
    """Relation between the user and the domains each user can manage.

    Attributes:
        domain: domain.
        user: user.
        text: details.
    """

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()


# class AuditLog(models.Model):
#     """Audit log representation."""

#     # We may not need this since it can be derived from domainuserpermission.

#     user = models.ForeignKey(User, on_delete=models.RESTRICT)
#     domain = models.ForeignKey(Domain, on_delete=models.RESTRICT)
#     now = datetime.now().time()
#     created_at = models.DateTimeField(default=now)
#     status = models.CharField(choices=audit_log_status_choices, max_length=20, default="created")
#     details = models.TextField()
