"""Settings."""

import os

# "git+ssh://arturo-seijas@git.launchpad.net/~arturo-seijas/canonical-is-dns-configs@main"#"auto-httpreq"
DNS_REPOSITORY_URL=os.environ["DNS_REPOSITORY_URL"]
SSH_IDENTITY_FILE=os.path.expanduser("~/.ssh/id_rsa")