# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""
import base64
import secrets
from unittest.mock import patch

import pytest
from django.test import Client

from httprequest_lego_provider.forms import FQDN_PREFIX
from httprequest_lego_provider.models import Domain, DomainUserPermission


@pytest.mark.django_db
def test_post_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL.
    assert: a 401 is returned.
    """
    response = client.post("/present/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_auth_header_empty(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL with an empty authorization header.
    assert: a 401 is returned.
    """
    response = client.post("/present/", headers={"AUTHORIZATION": ""})

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_auth_header_invalid(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL with an invalid authorization header.
    assert: a 401 is returned.
    """
    auth_token = base64.b64encode(bytes("invalid:invalid", "utf-8")).decode("utf-8")
    response = client.post("/present/", headers={"AUTHORIZATION": f"Basic {auth_token}"})

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_fqdn(client: Client, user_auth_token: str, fqdn: str):
    """
    arrange: log in a user.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/present/",
        data={"fqdn": fqdn, "value": value},
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_permission(
    client: Client, user_auth_token: str, domain: Domain
):
    """
    arrange: log in a user and insert a domain in the database.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/present/",
        data={"fqdn": domain.fqdn, "value": value},
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission(
    client: Client, user_auth_token: str, domain_user_permission: DomainUserPermission
):
    """
    arrange: mock the write_dns_recod method, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 204 is returned.
    """
    with patch("httprequest_lego_provider.views.write_dns_record") as mocked_dns_write:
        value = secrets.token_hex()
        response = client.post(
            "/present/",
            data={"fqdn": domain_user_permission.domain.fqdn, "value": value},
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_write.assert_called_once_with(domain_user_permission.domain, value)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_present_when_logged_in_and_fqdn_invalid(client: Client, user_auth_token: str):
    """
    arrange: mock the write_dns_recod method and log in a user.
    act: submit a POST request for the present URL containing an invalid FQDN.
    assert: a 400 is returned.
    """
    with patch("httprequest_lego_provider.views.write_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/present/",
            data={"fqdn": "example.com", "value": value},
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )

        assert response.status_code == 400


@pytest.mark.django_db
def test_get_present_when_logged_in(client: Client, user_auth_token: str):
    """
    arrange: log in a user.
    act: submit a GET request for the present URL.
    assert: a 405 is returned.
    """
    response = client.get("/present/", headers={"AUTHORIZATION": f"Basic {user_auth_token}"})

    assert response.status_code == 405


@pytest.mark.django_db
def test_post_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the cleanup URL.
    assert: a 401 is returned.
    """
    response = client.post("/cleanup/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_fqdn(client: Client, user_auth_token: str):
    """
    arrange: log in a user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/cleanup/",
        data={"fqdn": f"{FQDN_PREFIX}example.com", "value": value},
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_permission(
    client: Client, user_auth_token: str, domain: Domain
):
    """
    arrange: log in a user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/cleanup/",
        data={"fqdn": domain.fqdn, "value": value},
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission(
    client: Client, user_auth_token: str, domain_user_permission: DomainUserPermission
):
    """
    arrange: mock the dns module, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the cleanup URL containing the fqdn above.
    assert: a 200 is returned.
    """
    with patch("httprequest_lego_provider.views.remove_dns_record") as mocked_dns_remove:
        value = secrets.token_hex()
        response = client.post(
            "/cleanup/",
            data={"fqdn": domain_user_permission.domain.fqdn, "value": value},
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_remove.assert_called_once_with(domain_user_permission.domain)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_fqdn_invalid(client: Client, user_auth_token: str):
    """
    arrange: mock the dns module and log in a user.
    act: submit a POST request for the cleanup URL containing an invalid FQDN.
    assert: a 400 is returned.
    """
    with patch("httprequest_lego_provider.views.remove_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/cleanup/",
            data={"fqdn": "example.com", "value": value},
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )

        assert response.status_code == 400


@pytest.mark.django_db
def test_get_cleanup_when_logged_in(client: Client, user_auth_token: str):
    """
    arrange: log in a user.
    act: submit a GET request for the cleanup URL.
    assert: a 405 is returned.
    """
    response = client.get("/present/", headers={"AUTHORIZATION": f"Basic {user_auth_token}"})

    assert response.status_code == 405


@pytest.mark.django_db
def test_test_jwt_token_login(
    client: Client, username: str, user_password: str, domain_user_permission: DomainUserPermission
):
    """
    arrange: mock the write_dns_recod method, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 204 is returned.
    """
    response = client.post(
        "/api/v1/auth/token/",
        data={"username": username, "password": user_password},
    )

    with patch("httprequest_lego_provider.views.write_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/present/",
            data={"fqdn": domain_user_permission.domain.fqdn, "value": value},
            headers={"AUTHORIZATION": f"JWT {response.token}"},
        )

        assert response.status_code == 204
