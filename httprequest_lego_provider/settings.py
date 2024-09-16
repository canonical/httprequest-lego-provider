# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Settings."""

import os

GIT_REPO_URL = os.getenv("DJANGO_GIT-REPO", default="")
GIT_SSH_KEY = os.getenv("DJANGO_GIT-SSH-KEY", default="")
LOGIN_REDIRECT_URL = "/"
