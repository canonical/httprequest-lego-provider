# Charm architecture

The HTTPRequest lego provider is, at its core, a Juju charm deploying and managing [HTTPRequest Lego provider as defined by ACME](https://go-acme.github.io/lego/dns/httpreq/) to manage DNS records.

It leverages the [12-factor](https://canonical-12-factor-app-support.readthedocs-hosted.com/en/latest/) support to pack a [Django](https://www.djangoproject.com/) application providing the functionality as defined by the standard.

For a complete view on the architecture of a 12-factor charm, refer to the [12-factor architecture documentation](https://canonical-12-factor-app-support.readthedocs-hosted.com/en/latest/explanation/charm-architecture/). Below are detailed the HTTPRequest LEGO provider specifics.

## OCI images

We use [Rockcraft's Django framework extension](https://documentation.ubuntu.com/rockcraft/en/stable/reference/extensions/django-framework.html) to build OCI Images for HTTPRequest LEGO provider. 
The images are defined in [HTTPRequest LEGO provider rock](https://github.com/canonical/httprequest-lego-provider/blob/main/rockcraft.yaml).
They are published to [Charmhub](https://charmhub.io/), the official repository of charms.

> See more: [How to publish your charm on Charmhub](https://juju.is/docs/sdk/publishing)

 
## Juju events

For this charm, in addition to the event handling provided by the framework, the following Juju events are observed:

1. [pebble_ready](https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#container-pebble-ready): fired on Kubernetes charms when the requested container is ready. Action: copy the necessary configuration files and trigger the default handler as defined by the framework.
2. [config_changed](https://canonical-juju.readthedocs-hosted.com/en/latest/user/reference/hook/#config-changed):  usually fired in response to a configuration change using the CLI. Action: copy the necessary configuration files and trigger the default handler as defined by the framework.

> See more in the Juju docs: [Hook](https://juju.is/docs/sdk/event)

## Charm code overview

The `src/charm.py` is the default entry point for a charm and has the DjangoCharm Python class which inherits from paas_app_charmer.django.Charm, the base class 
from which all Django 12-factor charms are formed, defined by [the Django framework extension for Charmcraft](https://documentation.ubuntu.com/rockcraft/en/stable/reference/extensions/django-framework.html).

> See more in the Charmcraft docs: [Django framework extension](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/reference/extensions/django-framework-extension/)

The `__init__` method guarantees that the charm observes all events relevant to its operation and handles them.

Take, for example, when a configuration is changed by using the CLI.

1. User runs the configuration command:
```bash
juju config git-repo=https://example.repository.git
```
2. A `config-changed` event is emitted.
3. In the `__init__` method is defined how to handle this event like this:
```python
self.framework.observe(self.on.config_changed, self._on_config_changed)
```
4. The method `_on_config_changed`, for its turn, will take the necessary actions such as waiting for all the relations to be ready and then configuring the containers.
