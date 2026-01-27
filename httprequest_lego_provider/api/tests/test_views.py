# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""

# imported-auth-user has to be disable as the conflicting import is needed for typing
# pylint:disable=imported-auth-user

import base64
import json
import secrets
from unittest.mock import patch

import pytest
from api.dns import DnsSourceUpdateError
from api.forms import FQDN_PREFIX
from api.models import AccessLevel, Domain, DomainUserPermission
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_post_present_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL.
    assert: a 401 is returned.
    """
    response = client.post("/present")

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_auth_header_empty(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL with an empty authorization header.
    assert: a 401 is returned.
    """
    response = client.post("/present", headers={"AUTHORIZATION": ""})

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_auth_header_invalid(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the present URL with an invalid authorization header.
    assert: a 401 is returned.
    """
    auth_token = base64.b64encode(bytes("invalid:invalid", "utf-8")).decode("utf-8")
    response = client.post("/present", headers={"AUTHORIZATION": f"Basic {auth_token}"})

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_fqdn(client: Client, user_auth_token: str, fqdn: str):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/present",
        data={"fqdn": f"{FQDN_PREFIX}{fqdn}", "value": value},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_no_permission(
    client: Client, user_auth_token: str, domain: Domain
):
    """
    arrange: log in a non-admin user and insert a domain in the database.
    act: submit a POST request for the present URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/present",
        data={"fqdn": f"{FQDN_PREFIX}{domain.fqdn}", "value": value},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission_domain_access_level(
    client: Client, user_auth_token: str, domain_user_permission_domain: DomainUserPermission
):
    """
    arrange: mock the write_dns_record method, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the present URL containing an fdqn with domain level access.
    assert: a 204 is returned.
    """
    with patch("api.views.write_dns_record") as mocked_dns_write:
        fqdn = f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}"
        value = secrets.token_hex()
        response = client.post(
            "/present",
            data={
                "fqdn": fqdn,
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_write.assert_called_once_with(fqdn, value)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission_subdomain_access_level(
    client: Client, user_auth_token: str, domain_user_permission_subdomain: DomainUserPermission
):
    """
    arrange: mock the write_dns_record method, log in a user and give him permissions on a FQDN.
    act: ubmit a POST request for the present URL containing an fdqn with subdomain level access.
    assert: a 204 is returned.
    """
    with patch("api.views.write_dns_record") as mocked_dns_write:
        value = secrets.token_hex()
        subdomain_fqdn = f"{FQDN_PREFIX}test.{domain_user_permission_subdomain.domain.fqdn}"
        response = client.post(
            "/present",
            data={"fqdn": subdomain_fqdn, "value": value},
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_write.assert_called_once_with(subdomain_fqdn, value)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_present_when_logged_in_and_permission_with_trailing_dot(
    client: Client, user_auth_token: str, domain_user_permission_domain: DomainUserPermission
):
    """
    arrange: mock the write_dns_record method, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 204 is returned.
    """
    with patch("api.views.write_dns_record") as mocked_dns_write:
        fqdn = f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}"
        value = secrets.token_hex()
        response = client.post(
            "/present",
            data={
                "fqdn": f"{fqdn}.",
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_write.assert_called_once_with(fqdn, value)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_present_when_logged_in_and_fqdn_invalid(client: Client, user_auth_token: str):
    """
    arrange: mock the write_dns_record method and log in a user.
    act: submit a POST request for the present URL containing an invalid FQDN.
    assert: a 400 is returned.
    """
    with patch("api.views.write_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/present",
            data={"fqdn": f"{FQDN_PREFIX}example-.com", "value": value},
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )

        assert response.status_code == 400


@pytest.mark.django_db
def test_get_present_when_logged_in(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a GET request for the present URL.
    assert: a 405 is returned.
    """
    response = client.get("/present", headers={"AUTHORIZATION": f"Basic {user_auth_token}"})

    assert response.status_code == 405


@pytest.mark.django_db
def test_post_cleanup_when_not_logged_in(client: Client):
    """
    arrange: do nothing.
    act: submit a POST request for the cleanup URL.
    assert: a 401 is returned.
    """
    response = client.post("/cleanup")

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_fqdn(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/cleanup",
        data={"fqdn": f"{FQDN_PREFIX}example.com", "value": value},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_no_permission(
    client: Client, user_auth_token: str, domain: Domain
):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the cleanup URL.
    assert: a 403 is returned.
    """
    value = secrets.token_hex()
    response = client.post(
        "/cleanup",
        data={"fqdn": f"{FQDN_PREFIX}{domain.fqdn}", "value": value},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission_access_level_domain(
    client: Client, user_auth_token: str, domain_user_permission_domain: DomainUserPermission
):
    """
    arrange: mock the dns module, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the cleanup URL containing an fqdn with domain level access.
    assert: a 200 is returned.
    """
    with patch("api.views.remove_dns_record") as mocked_dns_remove:
        fqdn = f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}"
        value = secrets.token_hex()
        response = client.post(
            "/cleanup",
            data={
                "fqdn": fqdn,
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_remove.assert_called_once_with(fqdn)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission_access_level_subdomain(
    client: Client, user_auth_token: str, domain_user_permission_subdomain: DomainUserPermission
):
    """
    arrange: mock the dns module, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the cleanup URL containing an fqdn with subdomain level access.
    assert: a 200 is returned.
    """
    with patch("api.views.remove_dns_record") as mocked_dns_remove:
        value = secrets.token_hex()
        subdomain_fqdn = f"{FQDN_PREFIX}test.{domain_user_permission_subdomain.domain.fqdn}"
        response = client.post(
            "/cleanup",
            data={"fqdn": subdomain_fqdn, "value": value},
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_remove.assert_called_once_with(subdomain_fqdn)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_permission_with_trailing_dot(
    client: Client, user_auth_token: str, domain_user_permission_domain: DomainUserPermission
):
    """
    arrange: mock the dns module, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the cleanup URL containing the fqdn above.
    assert: a 200 is returned.
    """
    with patch("api.views.remove_dns_record") as mocked_dns_remove:
        fqdn = f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}"
        value = secrets.token_hex()
        response = client.post(
            "/cleanup",
            data={
                "fqdn": f"{fqdn}.",
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )
        mocked_dns_remove.assert_called_once_with(fqdn)

        assert response.status_code == 204


@pytest.mark.django_db
def test_post_cleanup_when_logged_in_and_fqdn_invalid(client: Client, user_auth_token: str):
    """
    arrange: mock the dns module and log in a user.
    act: submit a POST request for the cleanup URL containing an invalid FQDN.
    assert: a 400 is returned.
    """
    with patch("api.views.remove_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/cleanup",
            data={"fqdn": "example-.com", "value": value},
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )

        assert response.status_code == 400


@pytest.mark.django_db
def test_get_cleanup_when_logged_in(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a GET request for the cleanup URL.
    assert: a 405 is returned.
    """
    response = client.get("/present", headers={"AUTHORIZATION": f"Basic {user_auth_token}"})

    assert response.status_code == 405


@pytest.mark.django_db
def test_test_jwt_token_login(
    client: Client,
    username: str,
    user_password: str,
    domain_user_permission_domain: DomainUserPermission,
):
    """
    arrange: mock the write_dns_record method, log in a user and give him permissions on a FQDN.
    act: submit a POST request for the present URL containing the fqdn above.
    assert: a 204 is returned.
    """
    response = client.post(
        "/api/v1/auth/token/",
        data={"username": username, "password": user_password},
    )
    token = json.loads(response.content)["access"]

    with patch("api.views.write_dns_record"):
        value = secrets.token_hex()
        response = client.post(
            "/present",
            data={
                "fqdn": f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}",
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == 204


@pytest.mark.django_db
def test_get_domain_when_logged_in_as_non_admin_user(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a GET request for the domain URL.
    assert: a 403 is returned
    """
    response = client.get(
        "/api/v1/domains/",
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_get_domain_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, domains: list
):
    """
    arrange: log in an admin user.
    act: submit a GET request for the domain URL.
    assert: a 200 is returned and the domains are all returned.
    """
    assert len(Domain.objects.all()) != 0
    response = client.get(
        "/api/v1/domains/",
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert response.status_code == 200
    assert len(json) == len(domains)


@pytest.mark.django_db
def test_get_domain_with_fqdn_filter(client: Client, admin_user_auth_token: str, domains: list):
    """
    arrange: log in an admin user.
    act: submit a GET request for the domain URL.
    assert: a 200 is returned and the domain matching FQDN is returned.
    """
    response = client.get(
        "/api/v1/domains/?fqdn=example2.com",
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert response.status_code == 200
    assert len(json) == 1
    assert json[0]["fqdn"] == "example2.com"


@pytest.mark.django_db
def test_post_domain_when_logged_in_as_non_admin_user(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the domain URL.
    assert: a 403 is returned and the domain is not inserted in the database.
    """
    response = client.post(
        "/api/v1/domains/",
        data={"fqdn": "example.com"},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    with pytest.raises(Domain.DoesNotExist):
        Domain.objects.get(fqdn="example.com")
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_domain_when_logged_in_as_admin_user(client: Client, admin_user_auth_token: str):
    """
    arrange: log in an admin user.
    act: submit a POST request for the domain URL.
    assert: a 201 is returned and the domain is inserted in the database.
    """
    response = client.post(
        "/api/v1/domains/",
        data={"fqdn": "example.com"},
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    assert Domain.objects.get(fqdn="example.com") is not None
    assert response.status_code == 201


@pytest.mark.django_db
def test_post_domain_when_logged_in_as_admin_user_and_domain_invalid(
    client: Client, admin_user_auth_token: str
):
    """
    arrange: log in a admin user.
    act: submit a POST request with an invalid value for the domain URL.
    assert: a 400 is returned.
    """
    response = client.post(
        "/api/v1/domains/",
        data={"fqdn": "invalid-value"},
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    with pytest.raises(Domain.DoesNotExist):
        Domain.objects.get(fqdn="invalid-value")
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_domain_user_permission_when_logged_in_as_non_admin_user(
    client: Client, user_auth_token: str, domain: Domain, user: User
):
    """
    arrange: log in a non-admin user.
    act: submit a GET request for the domain user permission URL.
    assert: a 403 is returned
    """
    response = client.get(
        "/api/v1/domain-user-permissions/",
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_get_domain_user_permission_when_logged_in_as_admin_user(
    client: Client,
    admin_user_auth_token: str,
    user: User,
    domain_user_permissions: list,
):
    """
    arrange: log in an admin user.
    act: submit a GET request for the domain user permission URL for a existing domain.
    assert: a 200 is returned, the json result does not contain unwanted domain-user-permissions.
    """
    assert len(DomainUserPermission.objects.all()) != 0
    response = client.get(
        "/api/v1/domain-user-permissions/",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert response.status_code == 200
    assert len(json) == len(DomainUserPermission.objects.all())


@pytest.mark.django_db
def test_get_domain_user_permission_with_filters(
    client: Client,
    admin_user_auth_token: str,
    user: User,
    domain_user_permissions: list,
):
    """
    arrange: log in an admin user.
    act: submit a GET request for the domain user permission URL for a existing domain.
    assert: a 200 is returned, the json result does not contain unwanted domain-user-permissions.
    """
    assert len(DomainUserPermission.objects.filter()) != 0
    response = client.get(
        "/api/v1/domain-user-permissions/",
        data={"fqdn": "example2.com", "username": user.username},
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert response.status_code == 200
    assert len(json) > 0

    for entry in json:
        assert entry["domain"] == Domain.objects.get(fqdn="example2.com").id
        assert entry["user"] == User.objects.get(username=user.username).id


@pytest.mark.django_db
def test_post_domain_user_permission_when_logged_in_as_non_admin_user(
    client: Client, user_auth_token: str, domain: Domain, user: User
):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the domain user permission URL.
    assert: a 403 is returned and the domain is not inserted in the database.
    """
    response = client.post(
        "/api/v1/domain-user-permissions/",
        data={
            "domain": domain.id,
            "user": user.id,
            "text": "whatever",
            "access_level": AccessLevel.DOMAIN,
        },
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert not DomainUserPermission.objects.filter(
        user=user, domain=domain, access_level=AccessLevel.DOMAIN
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_post_domain_user_permission_with_invalid_domain_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, user: User
):
    """
    arrange: log in an admin user.
    act: submit a POST request for the domain user permission URL for a non existing domain.
    assert: a 400 is returned and the domain is not inserted in the database.
    """
    response = client.post(
        "/api/v1/domain-user-permissions/",
        data={
            "domain": 1,
            "user": user.id,
            "text": "whatever",
            "access_level": AccessLevel.DOMAIN,
        },
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    assert not DomainUserPermission.objects.filter(
        user=user, domain=1, access_level=AccessLevel.DOMAIN
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_post_domain_user_permission_with_invalid_user_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, domain: Domain
):
    """
    arrange: log in an admin user.
    act: submit a POST request for the domain user permission URL for a non existing user.
    assert: a 400 is returned and the domain is not inserted in the database.
    """
    response = client.post(
        "/api/v1/domain-user-permissions/",
        data={
            "domain": domain.id,
            "user": 99,
            "text": "whatever",
            "access_level": AccessLevel.DOMAIN,
        },
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    assert not DomainUserPermission.objects.filter(
        user=99, domain=domain, access_level=AccessLevel.DOMAIN
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_post_domain_user_permission_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, user: User, domain: Domain
):
    """
    arrange: log in an admin user.
    act: submit a POST request for the domain user permission URL for a existing domain.
    assert: a 201 is returned and the domain user permission is inserted in the database.
    """
    response = client.post(
        "/api/v1/domain-user-permissions/",
        data={
            "domain": domain.id,
            "user": user.id,
            "text": "whatever",
            "access_level": AccessLevel.DOMAIN,
        },
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    assert (
        DomainUserPermission.objects.filter(
            user=user.id, domain=domain, access_level=AccessLevel.DOMAIN
        )
        is not None
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_post_subdomain_user_permission_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, user: User, domain: Domain
):
    """
    arrange: log in an admin user.
    act: submit a POST request for the domain user permission URL for a existing domain.
    assert: a 201 is returned and the domain user permission is inserted in the database.
    """
    response = client.post(
        "/api/v1/domain-user-permissions/",
        data={
            "domain": domain.id,
            "user": user.id,
            "text": "whatever",
            "access_level": AccessLevel.SUBDOMAIN,
        },
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    assert (
        DomainUserPermission.objects.filter(
            user=user.id, domain=domain, access_level=AccessLevel.SUBDOMAIN
        )
        is not None
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_get_user_when_logged_in_as_non_admin_user(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a GET request for the user URL.
    assert: a 403 is returned.
    """
    response = client.get(
        "/api/v1/users/",
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_get_user_when_logged_in_as_admin_user(
    client: Client, admin_user_auth_token: str, user: User
):
    """
    arrange: log in an admin user.
    act: submit a GET request for the user URL.
    assert: a 200 is returned and the json result does not contain passwords.
    """
    response = client.get(
        "/api/v1/users/",
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert len(User.objects.all()) > 0
    assert response.status_code == 200
    assert len(json) == len(User.objects.all())
    for entry in json:
        assert "password" not in entry


@pytest.mark.django_db
def test_get_user_with_username_filter(client: Client, admin_user_auth_token: str, user: User):
    """
    arrange: log in an admin user.
    act: submit a GET request for the user URL.
    assert: a 200 is returned and the json result matches the requested username.
    """
    response = client.get(
        "/api/v1/users/",
        data={"username": user.username},
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )
    json = response.json()

    assert len(User.objects.all()) > 0
    assert response.status_code == 200
    assert len(json) == 1
    for entry in json:
        assert entry["username"] == user.username


@pytest.mark.django_db
def test_post_user_when_logged_in_as_non_admin_user(client: Client, user_auth_token: str):
    """
    arrange: log in a non-admin user.
    act: submit a POST request for the user URL.
    assert: a 403 is returned and the user is not inserted in the database.
    """
    response = client.post(
        "/api/v1/users/",
        data={"username": "non-existing-user"},
        format="json",
        headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
    )

    assert response.status_code == 403
    with pytest.raises(User.DoesNotExist):
        User.objects.get(username="non-existing-user")


@pytest.mark.django_db
def test_post_user_when_logged_in_as_admin_user(client: Client, admin_user_auth_token: str):
    """
    arrange: log in an admin user.
    act: submit a POST request for the user URL.
    assert: a 201 is returned and the user is inserted in the database.
    """
    password = secrets.token_hex()
    response = client.post(
        "/api/v1/users/",
        data={"username": "new-user", "password": password},
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    assert response.status_code == 201
    newu = User.objects.get(username="new-user")
    assert newu is not None
    assert check_password(password, newu.password) is True


@pytest.mark.django_db
def test_post_user_when_logged_in_as_admin_user_and_user_invalid(
    client: Client, admin_user_auth_token: str
):
    """
    arrange: log in a admin user.
    act: submit a POST request with an invalid value for the user URL.
    assert: a 400 is returned.
    """
    existing = User.objects.all()[0]
    response = client.post(
        "/api/v1/users/",
        data={"username": existing.username},
        format="json",
        headers={"AUTHORIZATION": f"Basic {admin_user_auth_token}"},
    )

    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint,mock_target,needs_value",
    [
        pytest.param("/present", "api.views.write_dns_record", True, id="Test '/present'"),
        pytest.param("/cleanup", "api.views.remove_dns_record", False, id="Test '/cleanup'"),
    ],
)
def test_post_when_write_dns_fails(
    client: Client,
    user_auth_token: str,
    domain_user_permission_domain: DomainUserPermission,
    endpoint,
    mock_target,
    needs_value,
):
    """
    assert: mock target to raise DnsSourceUpdateError method, log in a user and give him
    permissions on a FQDN.
    act: submit a POST request for the required endpoint containing the fqdn above.
    assert: a 500 is returned with the expected response content.

    """
    exception_msg = (
        "test.domain file not found in git repository. Is this site configured for DNS?"
    )

    with patch(mock_target) as mocked_dns_func:
        mocked_dns_func.side_effect = DnsSourceUpdateError(exception_msg)

        fqdn = f"{FQDN_PREFIX}{domain_user_permission_domain.domain.fqdn}"
        value = secrets.token_hex()
        response = client.post(
            endpoint,
            data={
                "fqdn": f"{fqdn}.",
                "value": value,
            },
            format="json",
            headers={"AUTHORIZATION": f"Basic {user_auth_token}"},
        )

        if needs_value:
            mocked_dns_func.assert_called_once_with(fqdn, value)
        else:
            mocked_dns_func.assert_called_once_with(fqdn)

        assert response.status_code == 500
        assert (
            response.content.decode("utf-8")
            == f"{exception_msg} Check httprequest-lego-provider for more details."
        )
