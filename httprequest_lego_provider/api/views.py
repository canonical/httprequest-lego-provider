# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Views."""

# Disable too-many-ancestors rule since we can't control inheritance for the ViewSets.
# pylint:disable=too-many-ancestors

from typing import Optional

# imported-auth-user has to be disabled as the import is needed for UserViewSet
# pylint:disable=imported-auth-user
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAdminUser

from .dns import remove_dns_record, write_dns_record
from .forms import CleanupForm, PresentForm
from .models import AccessLevel, Domain, DomainUserPermission
from .serializers import DomainSerializer, DomainUserPermissionSerializer, UserSerializer

FQDN_PREFIX = "_acme-challenge."


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
    fqdn: str = form.cleaned_data["fqdn"]
    fqdn_without_prefix = fqdn.removeprefix(FQDN_PREFIX)
    value = form.cleaned_data["value"]

    dups = DomainUserPermission.objects.filter(user=user)
    for dup in dups:
        domain_fqdn = dup.domain.fqdn
        if dup.access_level == AccessLevel.DOMAIN and fqdn_without_prefix == domain_fqdn:
            write_dns_record(fqdn, value)
            return HttpResponse(status=204)
        if dup.access_level == AccessLevel.SUBDOMAIN and fqdn_without_prefix.endswith(
            f".{domain_fqdn}"
        ):
            write_dns_record(fqdn, value)
            return HttpResponse(status=204)

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
    fqdn: str = form.cleaned_data["fqdn"]
    fqdn_without_prefix = fqdn.removeprefix(FQDN_PREFIX)
    dups = DomainUserPermission.objects.filter(user=user)
    for dup in dups:
        domain_fqdn = dup.domain.fqdn
        if dup.access_level == AccessLevel.DOMAIN and fqdn_without_prefix == domain_fqdn:
            remove_dns_record(fqdn)
            return HttpResponse(status=204)
        if dup.access_level == AccessLevel.SUBDOMAIN and fqdn_without_prefix.endswith(
            "." + domain_fqdn
        ):
            remove_dns_record(fqdn)
            return HttpResponse(status=204)

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

    def get_queryset(self):
        """Optionally restricts the returned object list to a given domain.

        Returns:
            a filtered queryset against a `fqdn` query parameter in the URL.
        """
        queryset = self.queryset
        fqdn = self.request.query_params.get("fqdn")
        if fqdn is not None:
            queryset = queryset.filter(fqdn=fqdn)
        return queryset


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

    def get_queryset(self):
        """Optionally restricts the returned object list to a given user/domain.

        Returns:
            A filtered queryset against `username` / `fqdn` query parameters in the URL.
        """
        queryset = self.queryset
        username = self.request.query_params.get("username")
        if username is not None:
            queryset = queryset.filter(user__username=username)
        fqdn = self.request.query_params.get("fqdn")
        if fqdn is not None:
            queryset = queryset.filter(domain__fqdn=fqdn)
        return queryset


class UserViewSet(viewsets.ModelViewSet):
    """Views for the User.

    Attributes:
        queryset: query for the objects in the model.
        serializer_class: class used for serialization.
        permission_classes: list of classes to match permissions.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """Optionally restricts the returned object list to a given user.

        Returns:
            A filtered queryset against a `username` query parameter in the URL.
        """
        queryset = self.queryset
        username = self.request.query_params.get("username")
        if username is not None:
            queryset = queryset.filter(username=username)
        return queryset
