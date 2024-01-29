# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Urls."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"domains", views.DomainViewSet)
router.register(r"domain-user-permissions", views.DomainUserPermissionViewSet)

urlpatterns = [
    path("api/v1/cleanup/", views.handle_cleanup, name="cleanup"),
    path("api/v1/present/", views.handle_present, name="present"),
    path("api/v1/accounts/", include("django.contrib.auth.urls")),
    path("api/v1/", include(router.urls)),
]
