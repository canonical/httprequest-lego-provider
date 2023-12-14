# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
"""Unit tests for the views module."""

import pytest
from django.http import HttpRequest
from lego.views import handle_present


@pytest.mark.django_db
def test_handle_present_when_get(client):
    response = client.get('/present')
    request = HttpRequest()
    request.method = "GET"
    response = handle_present(request)
    assert response.status_code == 200
