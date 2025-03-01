# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Settings."""

import os

GIT_REPO_URL = os.getenv("DJANGO_GIT_REPO", default="")
GIT_SSH_KEY = os.getenv("DJANGO_GIT_SSH_KEY", default="")
LOGIN_REDIRECT_URL = "/"
