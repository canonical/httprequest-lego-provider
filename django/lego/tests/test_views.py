# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""

import pytest
from lego.models import Domain, DomainUserPermission

from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_post_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL.
    assert: the request is redirected to the login page.
    """
    response = client.post("/present/", follow=True)
    assert response.status_code == 200
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_permission(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the present URL.
    assert: a 404 is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.post("present/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 404


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission(client: Client):
    """
    arrange: log in a user a give him permissions on a fqdn.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 200 is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=user.password)
    response = client.post("present/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_get_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a GET request for the present URL.
    assert: the request is redirected to the login page.
    """
    response = client.get("/present", follow=True)
    assert response.status_code == 200
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_get_present_when_logged_in(client: Client):
    """
    arrange: log in a user.
    act: submit a GET request for the present URL.
    assert: the cleanup page is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.get("/present", follow=True)
    assert response.status_code == 200
    assert response.url == "/present/"


@pytest.mark.django_db
def test_post_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the cleanup URL.
    assert: the request is redirected to the login page.
    """
    response = client.post("cleanup/", follow=True)
    assert response.status_code == 200
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_permission(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the cleanup URL.
    assert: a 404 is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.post("cleanup/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 404


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission(client: Client):
    """
    arrange: log in a user a give him permissions on a fqdn.
    act: submit a POST request for the cleanup URL containing the fqdn above.
    assert: a 200 is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=user.password)
    response = client.post("cleanup/", data={"fqdn": "example.com"}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_get_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a GET request for the cleanup URL.
    assert: the request is redirected to the login page.
    """
    response = client.get("cleanup/", follow=True)
    assert response.status_code == 200
    assert response.url == "/accounts/login/"


@pytest.mark.django_db
def test_get_cleanup_when_logged_in(client: Client):
    """
    arrange: log in a user.
    act: submit a GET request for the cleanup URL.
    assert: the cleanup page is returned.
    """
    user = User.objects.create_user("test_user", password="test_user")
    client.login(username=user.username, password=user.password)
    response = client.get("cleanup/", follow=True)
    assert response.status_code == 200
    assert response.url == "/cleanup/"
