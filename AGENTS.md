# AGENTS.md - Context for AI coding assistants

## Project Overview

This repository has two components that work together:

1. **`httprequest_lego_provider/`** — A Django REST API implementing the [ACME HTTP request Lego provider protocol](https://go-acme.github.io/lego/dns/httpreq/). It allows ACME clients (e.g. cert-manager) to manage DNS TXT records stored in a git repository.
2. **`charm/`** — A Juju Kubernetes charm wrapping the Django app, built with [`paas_app_charmer.django`](https://github.com/canonical/paas-charm) (`django-framework` extension).

The OCI image is built with `rockcraft` and the charm with `charmcraft`.

## Build, Test, and Lint

All workflows are managed with `tox`:

```shell
tox run -e lint      # code style: black, isort, flake8, mypy, pylint, pydocstyle, codespell
tox run -e unit      # unit tests (Django/pytest with SQLite)
tox run -e static    # bandit security analysis
tox run -e fmt       # auto-format with black + isort
tox run -e integration  # Juju integration tests (requires a running Juju controller)
```

Run a single unit test file or test function:

```shell
tox run -e unit -- api/tests/test_views.py::test_post_present_when_not_logged_in
tox run -e unit -- api/tests/test_dns.py
```

Build artifacts:

```shell
charmcraft pack   # produces the charm .charm file
rockcraft pack    # produces the OCI rock image
```

## Architecture

### DNS Record Management Flow

ACME clients call `POST /present` (add TXT record) or `POST /cleanup` (remove TXT record). The API:

1. Authenticates the user with HTTP Basic Auth.
2. Checks if the user has a `DomainUserPermission` for the requested FQDN. Two access levels exist:
   - `DOMAIN`: exact match (e.g. `example.com`)
   - `SUBDOMAIN`: suffix match (e.g. any `*.example.com`)
3. Clones the git repo configured via `git-repo` charm config, modifies the bind9-format `{domain}.domain` file, commits, and pushes back.

The `_acme-challenge.` prefix (per ACME spec) is stripped before permission checks — the stripped FQDN is compared against stored domains.

### Django App Layout

- `api/models.py` — `Domain`, `DomainUserPermission` (with `AccessLevel.DOMAIN`/`SUBDOMAIN`), uses Django's built-in `User`
- `api/views.py` — `handle_present`, `handle_cleanup` (function-based); `DomainViewSet`, `UserViewSet`, `DomainUserPermissionViewSet` (admin-only ModelViewSets)
- `api/dns.py` — git clone → modify bind9 file → commit → push; raises `DnsSourceUpdateError` on any failure
- `api/urls.py` — ACME endpoints at `/present`, `/cleanup`; admin REST API at `/api/v1/`
- `api/management/commands/` — Django management commands: `create_user`, `allow_domains`, `revoke_domains`, `list_domains`
- `httprequest_lego_provider/settings.py` — production settings; `api/tests/settings.py` — test settings (SQLite)

### Charm Layout

- `charm/src/charm.py` — extends `paas_app_charmer.django.Charm`; pushes SSH key and `known_hosts` into the container on config change
- `charm/src/actions.py` — `Observer` class that maps Juju actions to Django management command calls via `python3 manage.py <command>`
- `charm/charmcraft.yaml` — uses `django-framework` extension; requires `postgresql` relation; defines `git-repo` and `git-ssh-key` configs

## Key Conventions

### Copyright Header

Every Python source file begins with:

```python
# Copyright <year> Canonical Ltd.
# See LICENSE file for licensing details.
```

### Docstrings

Google-style docstrings are enforced (`pydocstyle`, `flake8-docstrings`). All public functions/classes require docstrings with `Args:`, `Returns:`, and `Raises:` sections where applicable. Tests are exempt from docstring requirements.

### Test Structure (AAA Pattern)

Unit test docstrings follow arrange/act/assert format:

```python
def test_something():
    """
    arrange: set up preconditions.
    act: perform the operation.
    assert: verify the result.
    """
```

### OpenTelemetry Tracing

All non-trivial functions are decorated with `@tracer.start_as_current_span("span_name")`. Each module creates its own tracer:

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
```

### Django Test Settings

Unit tests use `DJANGO_SETTINGS_MODULE=api.tests.settings` (set automatically by tox). The test settings extend production settings but use SQLite and a random `SECRET_KEY`.

### DNS File Format

DNS records are stored in bind9 zone file format as `{domain}.domain` files in the git repo. Each TXT record line uses:

```text
{subdomain} 600 IN TXT "{value}"
```

The root of a domain uses `.` as the subdomain. Existing subdomain entries are always removed before writing a new one.

### Git Repository URL Format

The `git-repo` config follows `git+ssh://username@host/path@branch` where the branch is optional. Parsed by `dns.parse_repository_url()`.

### Line Length

99 characters (black + flake8 configured in `pyproject.toml`).
