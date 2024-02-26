# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Views."""

# Disable too-many-ancestors rule since we can't control inheritance for the ViewSets.
# pylint:disable=too-many-ancestors

from typing import Optional

from django.http import HttpRequest, HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAdminUser

from .dns import remove_dns_record, write_dns_record
from .forms import CleanupForm, PresentForm
from .models import Domain, DomainUserPermission
from .serializers import DomainSerializer, DomainUserPermissionSerializer


@api_view(["POST"])
def handle_present(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the present form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.
    """
    form = PresentForm(request.data)
    if not form.is_valid():
        return HttpResponse(content=form.errors.as_json(), status=400)
    user = request.user
    fqdn = form.cleaned_data["fqdn"]
    try:
        domain = Domain.objects.get(fqdn=fqdn)
        value = form.cleaned_data["value"]
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            write_dns_record(domain, value)
            return HttpResponse(status=204)
    except Domain.DoesNotExist:
        pass
    return HttpResponse(
        status=403,
        content=f"The user {user} does not have permission to manage {fqdn}",
    )


@api_view(["POST"])
def handle_cleanup(request: HttpRequest) -> Optional[HttpResponse]:
    """Handle the submissing of the cleanup form.

    Args:
        request: the HTTP request.

    Returns:
        an HTTP response.
    """
    form = CleanupForm(request.data)
    if not form.is_valid():
        return HttpResponse(content=form.errors.as_json(), status=400)
    user = request.user
    fqdn = form.cleaned_data["fqdn"]
    try:
        domain = Domain.objects.get(fqdn=fqdn)
        if DomainUserPermission.objects.filter(user=user, domain=domain):
            remove_dns_record(domain)
            return HttpResponse(status=204)
    except Domain.DoesNotExist:
        pass
    return HttpResponse(
        status=403,
        content=f"The user {user} does not have permission to manage {fqdn}",
    )


class DomainViewSet(viewsets.ModelViewSet):
    """Views for the Domain.

    Attributes:
        queryset: query for the objects in the model.
        serializer_class: class used for serialization.
        permission_classes: list of classes to match permissions.
    """

    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAdminUser]


class DomainUserPermissionViewSet(viewsets.ModelViewSet):
    """Views for the DomainUserPermission.

    Attributes:
        queryset: query for the objects in the model.
        serializer_class: class used for serialization.
        permission_classes: list of classes to match permissions.
    """

    queryset = DomainUserPermission.objects.all()
    serializer_class = DomainUserPermissionSerializer
    permission_classes = [IsAdminUser]
