# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""

import pytest
from django.contrib.auth.models import User
from django.test import Client

from lego.models import Domain, DomainUserPermission


@pytest.mark.django_db
def test_post_present_when_not_logged_in(client: Client):
    response = client.post("present/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_permission(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.post("present/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 204

@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=user.password)
    response = client.post("present/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 204


@pytest.mark.django_db
def test_get_present_when_not_logged_in(client: Client):
    response = client.get("present/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_get_present_when_logged_in(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.get("present/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_post_cleanup_when_not_logged_in(client: Client):
    response = client.post("cleanup/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_permission(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.post("cleanup/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 204

@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=user.password)
    response = client.post("cleanup/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 204


@pytest.mark.django_db
def test_get_cleanup_when_not_logged_in(client: Client):
    response = client.get("cleanup/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_get_cleanup_when_logged_in(client: Client):
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.get("cleanup/", follow=True)
    assert response.status_code == 204
    assert response.url == "/accounts/login/"
