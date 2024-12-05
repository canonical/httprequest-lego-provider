# HTTPRequest Lego provider

  A [Juju](https://juju.is/) [charm](https://juju.is/docs/olm/charmed-operators)
  deploying and managing [HTTP request Lego provider](https://go-acme.github.io/lego/dns/httpreq/)
  on Kubernetes. HTTP request Lego provider is a web application implementing the [DNS HTTP request
  provider as defined by ACME](https://go-acme.github.io/lego/dns/httpreq/) to manage DNS records.

  This charm simplifies initial deployment and operations of the HTTP request Lego
  provider on Kubernetes, enabling the automation of DNS management. It allows for deployment
  on many different Kubernetes platforms, from [MicroK8s](https://microk8s.io) to
  [Charmed Kubernetes](https://ubuntu.com/kubernetes) and public cloud Kubernetes offerings.

  As such, the charm makes it easy for those looking to host their own ACME provider, and gives
  them the freedom to deploy on the Kubernetes platform of their choice.

  For DevOps or SRE teams this charm will make operating HTTP request Lego provider simple and
  straightforward through Juju's clean interface. It will allow easy deployment
  into multiple environments for testing of changes, and supports scaling out for
  enterprise deployments.

## In this documentation

| | |
|--|--|
|  [Tutorials](https://discourse.charmhub.io/t/httprequest-lego-provider-docs-getting-started/15784)</br>  Get started - a hands-on introduction to using the HTTPRequest Lego provider for new users </br> |  [How-to guides](https://charmhub.io/httprequest-lego-provider/docs/authentication) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](https://charmhub.io/httprequest-lego-provider/actions) </br> Technical information - specifications, APIs, architecture | [Explanation](https://charmhub.io/httprequest-lego-provider/docs/architecture) </br> Concepts - discussion and clarification of key topics  |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to the documentation as the code. As such, we welcome community contributions, suggestions and constructive feedback on our documentation. Our documentation is hosted on the [Charmhub forum](https://discourse.charmhub.io/) to enable easy collaboration. Please use the "Help us improve this documentation" links on each documentation page to either directly change something you see that's wrong, or ask a question, or make a suggestion about a potential change via the comments section.

If there's a particular area of documentation that you'd like to see that's missing, please [file a bug](https://github.com/canonical/httprequest-lego-provider/issues).

## Project and community

HTTPRequest Lego Provider is an open-source project that welcomes community contributions, suggestions, fixes and constructive feedback.
- [Read our Code of Conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/tag/lego)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- Contribute and report bugs to [the HTTPRequest Lego Provider](https://github.com/canonical/httprequest-lego-provider/issues)

# Navigation

[details=Mapping table]

| Level | Path | Navlink |
| -- | -- | -- |
| 1 | tutorial | [Tutorial]() |
| 2 | tutorial-deploy-the-deploy-the-httprequest-lego-provider-charm-for-the-first-time | [ Deploy the Httprequest Lego Provider charm for the first time](/t/httprequest-lego-provider-docs-getting-started/15784) |
| 1 | how-to| [How to]() |
| 2 | manage-domains | [Manage Domains](/t/httprequest-lego-provider-docs-how-to-manage-domains/15786) |
| 2 | manage-users | [Manage Users](/t/httprequest-lego-provider-docs-how-to-manage-users/15787) |
| 1 | reference| [Reference]() |
| 2 | reference-actions | [Actions](/t/httprequest-lego-provider-docs-actions/15788) |
| 2 | reference-configurations | [Configurations](/t/httprequest-lego-provider-docs-configurations/15789) |
| 2 | reference-integrations | [Integrations](/t/httprequest-lego-provider-docs-integrations/15790) |

[/details]
