"""Settings."""

import os

DNS_REPOSITORY_URL=os.getenv("DNS_REPOSITORY_URL", default="")
SSH_IDENTITY_FILE=os.path.expanduser("~/.ssh/id_rsa")
