[![CharmHub Badge](https://charmhub.io/httprequest-lego-provider/badge.svg)](https://charmhub.io/httprequest-lego-provider)
[![Publish to edge](https://github.com/canonical/httprequest-lego-provider/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/httprequest-lego-provider/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/httprequest-lego-provider/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/httprequest-lego-provider/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

# HTTPRequest Lego Provider

A Juju charm deploying and managing [HTTP request Lego provider as defined by ACME](https://go-acme.github.io/lego/dns/httpreq/)
to manage DNS records. It allows for deployment on
many different Kubernetes platforms, from [MicroK8s](https://microk8s.io) to
[Charmed Kubernetes](https://ubuntu.com/kubernetes) to public cloud Kubernetes
offerings.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. For Charmed HTTP request Lego provider, this includes:
  - Scaling
  - Integration with PostgreSQL

For information about how to deploy, integrate, and manage this charm, see the Official [HTTP request Lego provider Documentation](https://charmhub.io/httprequest-lego-provider/docs).


## Get started

You can follow the tutorial [here](https://charmhub.io/httprequest-lego-provider/docs/tutorial-deploy-the-deploy-the-httprequest-lego-provider-charm-for-the-first-time).

### Basic operations

The following actions are available for this charm:
  - allow-domains: Grant user access to domains.
  - create-superuser: Create a new Django superuser account.
  - create-user: Create a user for the services that will be requesting the domains. If it exists, the password will be updated.
  - list-domains: List the domains an user has access to.
  - revoke-domains: Revoke user access to domains.
  - rotate-secret-key: Rotate the secret key. Users will be forced to log in again. This might be useful if a security breach occurs.

You can check out the [full list of actions here](https://charmhub.io/httprequest-lego-provider/actions).

## Integrations

This charm can be integrated with other Juju charms and services:

  - [Loki](https://charmhub.io/loki-k8s): Loki is a horizontally scalable, highly available, multi-tenant log aggregation system inspired by Prometheus.
  - [Postgresql](https://charmhub.io/postgresql-k8s): PostgreSQL is a powerful, open source object-relational database system. It has more than 15 years of active development and a proven architecture that has earned it a strong reputation for reliability, data integrity, and correctness.

You can find the full list of integrations [here](https://charmhub.io/httprequest-lego-provider/integrations).

## Learn more
* [Read more](https://charmhub.io/httprequest-lego-provider) <!--Link to the charm's official documentation-->
* [Developer documentation](https://go-acme.github.io/lego/dns/httpreq/) <!--Link to any developer documentation-->
* [Official webpage](https://go-acme.github.io/lego/dns/httpreq/) <!--(Optional) Link to official webpage/blog/marketing content-->
* [Troubleshooting](https://matrix.to/#/#charmhub-charmdev:ubuntu.com) <!--(Optional) Link to a page or section about troubleshooting/FAQ-->
## Project and community
* [Issues](https://github.com/canonical/httprequest-lego-provider/issues) <!--Link to GitHub issues (if applicable)-->
* [Contributing](https://charmhub.io/httprequest-lego-provider/docs/how-to-contribute) <!--Link to any contribution guides-->
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com) <!--Link to contact info (if applicable), e.g. Matrix channel-->
