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

The selected proxy applies to Git clone and push operations, including SSH host-key
verification, for all Git hosts. `Ncat` opens an HTTP CONNECT tunnel to the repository
host on SSH port 22. The repository URL retains the original
`git+ssh://username@host/path@branch` format without a custom port.
The proxy must allow that destination; the charm does not switch GitHub connections
to port 443.

`JUJU_CHARM_NO_PROXY` excludes destinations from the proxy. It accepts
comma-separated host names, domain suffixes, optional ports, literal IP addresses,
IP networks in CIDR notation, or `*` for all destinations. IP network exclusions
apply only when the repository URL uses a literal IP address, not a DNS name.
Without a selected proxy, the charm uses direct SSH connections. Removing a proxy
or adding an exclusion replaces any previous SSH proxy command.

### Host-key acceptance and verification

The charm writes a host-specific SSH configuration under `/etc/ssh/ssh_config.d/`
so Git uses the selected proxy route, workload SSH key, and
`/var/lib/pebble/default/.ssh/known_hosts`. Connection attempts have a 10-second
timeout. There is no separate host-key scan, local relay, or GitHub API lookup,
and no direct fallback after a proxy failure.

OpenSSH uses `StrictHostKeyChecking accept-new`: the first connection automatically
records a previously unknown host key, and later connections reject a changed key.
This is trust on first use (TOFU), not independent authentication of the initial
key. A compromised proxy or network could substitute a key on that first
connection. Verify fingerprints through an independent trusted channel before use,
or pre-populate `known_hosts` with verified keys.

The charm ensures the `_daemon_` workload user can update the SSH directory and
`known_hosts` file. Configuration changes and workload-ready hooks preserve existing
trusted keys rather than refreshing or replacing them. A legitimate host-key change
requires an operator to verify the new key independently and update the stored entry.
The protection against changed keys lasts only while `known_hosts` is retained:
if the file is lost, for example when the workload container is replaced, the next
connection trusts the first observed key again. Do not assume that this workload
file persists across container or unit replacement.


> Read more about configurations in the Juju docs: [Configuration](https://documentation.ubuntu.com/juju/3.6/reference/configuration/)
