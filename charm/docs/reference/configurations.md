# Configurations

See [Configurations](https://charmhub.io/httprequest-lego-provider/configure).

## Proxies and Git SSH host keys

The Django charm framework forwards Juju's `JUJU_CHARM_HTTP_PROXY`,
`JUJU_CHARM_HTTPS_PROXY`, and `JUJU_CHARM_NO_PROXY` hook settings to the workload
as `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY`, including their lowercase equivalents.

For repositories hosted on `github.com`, the charm retrieves SSH host keys from
`https://api.github.com/meta` using those proxy settings, instead of opening a
direct SSH connection for `ssh-keyscan`. Other Git hosts continue to use
`ssh-keyscan`. The proxy settings apply only to this metadata request, not to Git SSH
traffic. The workload still needs SSH access to the Git host.


> Read more about configurations in the Juju docs: [Configuration](https://documentation.ubuntu.com/juju/3.6/reference/configuration/)
