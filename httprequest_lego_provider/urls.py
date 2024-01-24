# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Urls."""

from django.urls import include, path

from . import views

urlpatterns = [
    path("api/v1/cleanup/", views.handle_cleanup, name="cleanup"),
    path("api/v1/present/", views.handle_present, name="present"),
    path("api/v1/accounts/", include("django.contrib.auth.urls")),
]
