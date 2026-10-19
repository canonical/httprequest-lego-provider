# Contributing

To make contributions to this charm, you'll need a working [development setup](https://documentation.ubuntu.com/juju/latest/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/).

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

## Testing

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

```shell
tox run -e format
tox run -e lint
tox run -e unit
tox run -e integration
tox
```

### PostgreSQL migration tests

The sequence-repair regression requires PostgreSQL: SQLite automatically accounts for explicit
IDs and cannot reproduce the failure. CI runs these tests against PostgreSQL 14.

To run them locally, start a disposable PostgreSQL 14 server:

```shell
docker run --detach --rm --name lego-sequence-test \
  --publish 127.0.0.1:55471:5432 \
  --env POSTGRES_USER=lego --env POSTGRES_PASSWORD=local-test-only \
  --env POSTGRES_DB=lego postgres:14

until docker exec lego-sequence-test pg_isready -U lego -d lego; do sleep 1; done

POSTGRESQL_DB_CONNECT_STRING='postgresql://lego:local-test-only@127.0.0.1:55471/lego' \
  tox run -e postgres

docker stop lego-sequence-test
```

Use only a disposable server. Pytest creates and drops a test database, and the database user
must have permission to create databases. The default `unit` environment continues to use SQLite
and skips the PostgreSQL-specific regression.

## Build the charm

Build the charm in this git repository using:

```shell
charmcraft pack
```

<!-- You may want to include any contribution/style guidelines in this document>
