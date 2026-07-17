.. Copyright 2026 Canonical Ltd.
.. See LICENSE file for licensing details.

.. meta::
   :description: Discover the HTTP request Lego provider charm, a Juju operator that deploys and manages HTTP request Lego provider.

.. vale Canonical.007-Headings-sentence-case = NO

.. _index:

HTTP request Lego provider operator
===================================

.. vale Canonical.007-Headings-sentence-case = YES

A `Juju <https://juju.is/>`_ `charm <https://canonical.com/juju/docs/juju-cli/3.6/reference/charm/>`_
deploying and managing HTTP request Lego provider on Kubernetes. 
The HTTP request Lego provider is a web application implementing the DNS HTTP request provider as defined by ACME to manage DNS records.

Like any Juju charm, this charm supports one-line deployment, configuration, integration,
scaling, and more. 
For HTTP request Lego provider, this includes:

* `ACME DNS-01 challenge <https://letsencrypt.org/docs/challenge-types/#dns-01-challenge>`_ support for TLS certificate issuance and renewal.
* A simple web interface for managing DNS records.
* Admin and user roles for managing access to DNS records.

The HTTP request Lego provider charm allows for deployment on many different Kubernetes platforms,
from `MicroK8s <https://canonical.com/microk8s>`_ to 
`Charmed Kubernetes <https://ubuntu.com/kubernetes>`_ to public cloud Kubernetes offerings.

This charm will make managing and renewing TLS certificates for your applications straightforward.

In this documentation
---------------------

.. list-table::
    :header-rows: 0

    * - Get started
      - :ref:`Deploy and access HTTP request Lego provider <getting_started>`
    * - Deployment
      - :ref:`Manage domains <manage_domains>` | :ref:`Manage users <manage_users>`
    * - Operations
      - :ref:`Back up and restore <backup_and_restore>` | :ref:`Troubleshoot API timeouts <troubleshoot_api_timeouts>` | :ref:`Upgrade <upgrade>`
    * - Design
      - :ref:`Charm architecture <charm_architecture>` | :ref:`Integrations <integrations>`
    * - Security
      - :ref:`Overview <security>`

How this documentation is organized
------------------------------------

This documentation uses the `Diátaxis documentation structure <https://diataxis.fr/>`_.

- The :ref:`Tutorial <tutorial_index>` takes you step-by-step through a basic deployment of the HTTP request Lego provider charm.
- The :ref:`How-to guides <how_to_index>` assume you have basic familiarity with the charm. Learn more about setting up, using, maintaining, and contributing to this charm.
- The :ref:`Reference <reference_index>` provides a guide to actions, configurations, relations, and other technical details.
- The :ref:`Explanation <explanation_index>` includes topic overviews, background and context and detailed discussion.

Contributing to this documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Documentation is an important part of this project, and we take the same open-source approach
to the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation.
See our `contributing guide
<https://github.com/canonical/httprequest-lego-provider/blob/main/CONTRIBUTING.md>`_
for more information.

If there's a particular area of documentation that you'd like to see that's missing, please 
`file a bug <https://github.com/canonical/httprequest-lego-provider/issues/>`_.

Project and community
---------------------

The HTTP request Lego provider Operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

Governance and policies
^^^^^^^^^^^^^^^^^^^^^^^

- `Code of conduct <https://ubuntu.com/community/code-of-conduct>`_

Get involved
^^^^^^^^^^^^

- `Get support <https://discourse.charmhub.io/>`_
- `Join our online chat <https://matrix.to/#/#charmhub-charmdev:ubuntu.com>`_
- `Contribute <https://github.com/canonical/httprequest-lego-provider/blob/main/CONTRIBUTING.md>`_

Thinking about using the HTTP request Lego provider Operator for your next project? 
`Get in touch <https://matrix.to/#/#charmhub-charmdev:ubuntu.com>`_!

.. vale Canonical.013-Spell-out-numbers-below-10 = NO
.. vale Canonical.500-Repeated-words = NO

.. toctree::
    :hidden:
    :maxdepth: 1

    Tutorial <tutorial/index>
    How-to guides <how-to/index>
    Reference <reference/index>
    Explanation <explanation/index>
