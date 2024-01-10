# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""
import secrets
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client

from httprequest_lego_provider.models import Domain, DomainUserPermission


@pytest.mark.django_db
def test_post_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL.
    assert: the request is redirected to the login page.
    """
    response = client.post("/present/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_fqdn(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    client.login(username=user.username, password=test_password)
    value = secrets.token_hex()
    response = client.post("/present/", data={"fqdn": "example.com", "value": value})
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_permission(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    Domain.objects.create(fqdn="example.com")
    client.login(username=user.username, password=test_password)
    value = secrets.token_hex()
    response = client.post("/present/", data={"fqdn": "example.com", "value": value})
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission(client: Client):
    """
    arrange: mock the write_dns_recod method, log in a user a give him permissions on a fqdn.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 204 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=test_password)
    with patch("httprequest_lego_provider.views.write_dns_record") as mocked_dns_write:
        value = secrets.token_hex()
        response = client.post("/present/", data={"fqdn": "example.com", "value": value})
        mocked_dns_write.assert_called_once_with(domain, value)
        assert response.status_code == 204


@pytest.mark.django_db
def test_get_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a GET request for the present URL.
    assert: the request is redirected to the login page.
    """
    response = client.get("/present/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_get_present_when_logged_in(client: Client):
    """
    arrange: log in a user.
    act: submit a GET request for the present URL.
    assert: the cleanup page is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    client.login(username=user.username, password=test_password)
    response = client.get("/present/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_post_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the cleanup URL.
    assert: the request is redirected to the login page.
    """
    response = client.post("/cleanup/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_fqdn(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    client.login(username=user.username, password=test_password)
    value = secrets.token_hex()
    response = client.post("/cleanup/", data={"fqdn": "example.com", "value": value})
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_permission(client: Client):
    """
    arrange: log in a user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    Domain.objects.create(fqdn="example.com")
    client.login(username=user.username, password=test_password)
    value = secrets.token_hex()
    response = client.post("/cleanup/", data={"fqdn": "example.com", "value": value})
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission(client: Client):
    """
    arrange: mock the dns module, log in a user a give him permissions on a fqdn.
    act: submit a POST request for the cleanup URL containing the fqdn above.
    assert: a 200 is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    domain = Domain.objects.create(fqdn="example.com")
    DomainUserPermission.objects.create(domain=domain, user=user)
    client.login(username=user.username, password=test_password)
    with patch("httprequest_lego_provider.views.remove_dns_record") as mocked_dns_remove:
        value = secrets.token_hex()
        response = client.post("/cleanup/", data={"fqdn": "example.com", "value": value})
        mocked_dns_remove.assert_called_once_with(domain)
        assert response.status_code == 204


@pytest.mark.django_db
def test_get_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a GET request for the cleanup URL.
    assert: the request is redirected to the login page.
    """
    response = client.get("/cleanup/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_get_cleanup_when_logged_in(client: Client):
    """
    arrange: log in a user.
    act: submit a GET request for the cleanup URL.
    assert: the cleanup page is returned.
    """
    test_password = secrets.token_hex()
    user = User.objects.create_user("test_user", password=test_password)
    client.login(username=user.username, password=test_password)
    response = client.get("/cleanup/")
    assert response.status_code == 200
