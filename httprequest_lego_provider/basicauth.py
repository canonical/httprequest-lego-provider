# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Inspired by https://github.com/m7v8/django-basic-authentication-decorator
"""Basic authentication."""

import base64
from functools import wraps

from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse


def basicauth(func) -> HttpResponse:
    """Validate HTTP_AUTHORIZATION header.

    Usage:

    @basicauth
    def your_view:
        ...

    Args:
        func: the view function.

    Returns:
        an HTTP response containing the view if authentication succeeds, 401 otherwise.
    """

    @wraps(func)
    def _wrapped_view_func(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Validate HTTP_AUTHORIZATION header.

        Args:
            request: the HTTP request.
            args: additional arguments.
            kwargs: additional keyword arguments.

        Returns:
            an HTTP response containing the view if authentication succeeds, 401 otherwise.
        """
        if "HTTP_AUTHORIZATION" in request.META:
            auth = request.META["HTTP_AUTHORIZATION"].split()
            if len(auth) == 2 and auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).decode("ascii").split(":", 1)
                user = authenticate(username=uname, password=passwd)
                if user is not None and user.is_active:
                    login(request, user)
                    request.user = user
                    return func(request, *args, **kwargs)
        return HttpResponse(status=401)

    return _wrapped_view_func
