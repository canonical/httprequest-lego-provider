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

## Build the charm

Build the charm in this git repository using:

```shell
charmcraft pack
```

<!-- You may want to include any contribution/style guidelines in this document>
