# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Settings."""

import os

DNS_REPOSITORY_URL = os.getenv("DJANGO_DNS_REPOSITORY_URL", default="")
SSH_KEY = os.getenv("DJANGO_SSH_KEY", default="")
LOGIN_REDIRECT_URL = "/"
