# Upgrade

Since the upgrade to the latest version involves running migration scripts in the database, it is essential to backup the postgresql database before upgrading to the latest version. 

## Back up

Follow the [PostgreSQL charm documentation](https://charmhub.io/postgresql/docs/h-configure-s3-aws) to back up the database.

## Upgrade to the latest version

Upgrade the charm to the latest version:
`juju refresh httprequest-lego-provider --revision=<revision number>`

You should see the `httprequest-lego-provider` charm go to `Active` and `Idle` state after upgrading.


