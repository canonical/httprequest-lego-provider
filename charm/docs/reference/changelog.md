# Changelog

## Upgrade to paas-charm 2.0 on Ubuntu 26.04

- The charm and rock move to Ubuntu 26.04 and `paas-charm` 2.0.
- The workload container is renamed from `django-app` to `app` and the OCI resource from
  `django-app-image` to `app-image`.
- **Remove and redeploy is required.** Because of
  [Juju bug LP#1991955](https://bugs.launchpad.net/juju/+bug/1991955), `juju refresh` cannot
  replace the old container. Use `juju remove-application` and deploy the new revision. See
  [how to upgrade](../how-to/upgrade.md).
- The application secret key is regenerated, which signs out existing sessions. Use the
  secret-typed `app-secret-key` option to keep a key.
- The workload runs as the non-root `_daemon_` user. The charm writes the Git SSH configuration,
  key and `known_hosts` file under `/var/lib/pebble/default/.ssh`.
