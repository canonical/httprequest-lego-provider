from datetime import datetime
from django.contrib.auth.models import User
from django.db import models

audit_log_status_choices = (
    ("created", "created"),
    ("updated", "updated"),
    ("deleted", "deleted"),
)


class Domain(models.Model):
    # We should add validators to ensure this matches expected values. Note
    # that this validation should also be used in the Django form when processing
    # a request.
    fqdn = models.CharField(max_length=200, unique=True)


class DomainUserPermission(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()


class AuditLog(models.Model):
    # We may not need this since it can be derived from domainuserpermission.
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    domain = models.ForeignKey(Domain, on_delete=models.DO_NOTHING)
    now = datetime.now().time()
    created_at = models.DateTimeField(default=now)
    status = models.CharField(choices=audit_log_status_choices, max_length=20, default="created")
    details = models.TextField()
