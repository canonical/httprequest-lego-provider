# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Views."""

from typing import Optional

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from rest_framework.decorators import api_view

from .dns import remove_dns_record, write_dns_record
from .forms import CleanupForm, PresentForm
from .models import Domain, DomainUserPermission


@api_view(["POST"])
def handle_present(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the present form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.

    Raises:
        PermissionDenied: if the user is not allowed to perform the operation.
    """
    print("ENTRO")
    form = PresentForm(request.POST)
    if not form.is_valid():
        return HttpResponse(content=form.errors.as_json(), status=400)
    user = request.user
    try:
        domain = Domain.objects.get(fqdn=form.cleaned_data["fqdn"])
        value = form.cleaned_data["value"]
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            write_dns_record(domain, value)
            return HttpResponse(status=204)
    except Domain.DoesNotExist:
        pass
    raise PermissionDenied


@api_view(["POST"])
def handle_cleanup(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the cleanup form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.

    Raises:
        PermissionDenied: if the user is not allowed to perform the operation.
    """
    form = CleanupForm(request.POST)
    if not form.is_valid():
        return HttpResponse(content=form.errors.as_json(), status=400)
    user = request.user
    try:
        domain = Domain.objects.get(fqdn=form.cleaned_data["fqdn"])
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            remove_dns_record(domain)
            return HttpResponse(status=204)
    except Domain.DoesNotExist:
        pass
    raise PermissionDenied
