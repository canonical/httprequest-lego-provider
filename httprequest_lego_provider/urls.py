# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Urls."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("domains", views.DomainViewSet)
router.register("domain-user-permissions", views.DomainUserPermissionViewSet)

urlpatterns = [
    path("cleanup", views.handle_cleanup, name="cleanup"),
    path("present", views.handle_present, name="present"),
    path("api/v1/accounts/", include("django.contrib.auth.urls")),
    path("api/v1/", include(router.urls)),
]
