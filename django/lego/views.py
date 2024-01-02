# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Views."""

from typing import Optional

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .dns import remove_dns_record, write_dns_record
from .forms import CleanupForm, PresentForm
from .models import Domain, DomainUserPermission


@login_required
def handle_present(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the present form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.

    Raises:
        PermissionDenied: if the user is not allowed to perform the operation.
    """
    if request.method == "POST":
        form = PresentForm(request.POST)
        if not form.is_valid():
            return HttpResponse(form.errors.as_json())
        user = request.user
        domain = Domain.objects.get(fqdn=form.cleaned_data["fqdn"])
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            # audit_log = AuditLog()
            # audit_log.status = "created"
            # audit_log.user = user
            # audit_log.domain = domain
            # audit_log.save()
            write_dns_record(domain)
            return HttpResponse(status=204)
        raise PermissionDenied
    form = PresentForm()
    return render(request, "present.html", {"form": form})


@login_required
def handle_cleanup(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the cleanup form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.

    Raises:
        PermissionDenied: if the user is not allowed to perform the operation.
    """
    if request.method == "POST":
        form = CleanupForm(request.POST)
        if not form.is_valid():
            return HttpResponse(form.errors.as_json())
        user = request.user
        domain = Domain.objects.get(fqdn=form.cleaned_data["fqdn"])
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            # audit_log = AuditLog()
            # audit_log.status = "deleted"
            # audit_log.user = user
            # audit_log.domain = domain
            # audit_log.save()
            remove_dns_record(domain)
            return HttpResponse(status=204)
        raise PermissionDenied
    form = CleanupForm()
    return render(request, "cleanup.html", {"form": form})
