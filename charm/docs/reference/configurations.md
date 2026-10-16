# Configurations

See [Configurations](https://charmhub.io/httprequest-lego-provider/configure).

## Proxies and Git SSH connections

The Django charm framework forwards Juju's `JUJU_CHARM_HTTP_PROXY`,
`JUJU_CHARM_HTTPS_PROXY`, and `JUJU_CHARM_NO_PROXY` hook settings to the workload
as `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY`, including their lowercase equivalents.

For Git SSH connections, the charm selects `JUJU_CHARM_HTTPS_PROXY` first, with
`JUJU_CHARM_HTTP_PROXY` as a fallback. Both settings must use an unauthenticated
`http://host:port` URL. HTTPS and SOCKS proxy URLs, proxy credentials, and proxy URL
paths are unsupported and cause an explicit configuration error.

The selected proxy applies to both SSH host-key discovery and Git clone and push
operations, for all Git hosts. `Ncat` opens an HTTP CONNECT tunnel to the repository
host on SSH port 22. The repository URL retains the original
`git+ssh://username@host/path@branch` format without a custom port.
The proxy must allow that destination; the charm does not switch GitHub connections
to port 443.

`JUJU_CHARM_NO_PROXY` excludes destinations from both operations. It accepts
comma-separated host names, domain suffixes, optional ports, literal IP addresses,
IP networks in CIDR notation, or `*` for all destinations. IP network exclusions
apply only when the repository URL uses a literal IP address, not a DNS name.
Without a selected proxy, the charm uses direct SSH connections. Removing a proxy
or adding an exclusion replaces any previous SSH proxy command.

### Host-key discovery and verification

Since `ssh-keyscan` cannot use an SSH `ProxyCommand`, the charm starts a temporary
listener on an automatically allocated `127.0.0.1` port in the workload. It forwards
scan connections through `Ncat`, records the keys against the original Git host,
and closes the listener and child processes after the scan. Connection attempts
have a 10-second timeout and the scan has a 30-second overall deadline.

The charm writes a host-specific SSH configuration under `/etc/ssh/ssh_config.d/`
so Git uses the same proxy route and the workload SSH key and `known_hosts` file.
SSH host-key checking remains enabled. A failed scan leaves the existing SSH key,
host keys, and configuration unchanged; there is no direct or GitHub API fallback
after a proxy failure.

The keys collected by `ssh-keyscan` are observed over the network, not authenticated.
This replaces the earlier GitHub API lookup, which authenticated the metadata
source through HTTPS. A compromised proxy or network could substitute a key during
discovery. Verify the collected fingerprints against a trusted source through an
independent channel before use. The charm refreshes the collected host keys when
configuration changes or the workload becomes ready.


> Read more about configurations in the Juju docs: [Configuration](https://documentation.ubuntu.com/juju/3.6/reference/configuration/)
