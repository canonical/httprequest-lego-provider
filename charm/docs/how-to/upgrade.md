(upgrade)=

# How to upgrade

Since the upgrade to the latest version involves running migration scripts in the database, it is essential to backup the PostgreSQL database before upgrading to the latest version. 

## Back up

Follow the [PostgreSQL charm documentation](https://charmhub.io/postgresql/docs/h-configure-s3-aws) to back up the database.

## Upgrade from a revision that uses paas-charm 1.x

The charm now uses `paas-charm` 2.0 on Ubuntu 26.04. The workload container is renamed from
`django-app` to `app` and the OCI resource from `django-app-image` to `app-image`. On Juju
earlier than 4.1, [Juju bug LP#1991955](https://bugs.launchpad.net/juju/+bug/1991955) keeps the
old container alive and makes `juju refresh` fail. On those versions you must remove the
application and deploy it again. Back up the database first, as described above.

1. Save the configuration and note the integrations, because removing the application deletes
   them:

   ```
   juju config httprequest-lego-provider git-repo > git-repo.txt
   juju config httprequest-lego-provider git-ssh-key > git-ssh-key.txt
   juju status httprequest-lego-provider --relations
   ```

2. Remove the application:
   `juju remove-application httprequest-lego-provider --destroy-storage`
3. Deploy the new revision, restore the configuration and recreate the integrations:

   ```
   juju deploy httprequest-lego-provider --base ubuntu@26.04 --revision=<revision number>
   juju config httprequest-lego-provider git-repo=@git-repo.txt git-ssh-key=@git-ssh-key.txt
   juju integrate httprequest-lego-provider postgresql-k8s
   ```

The charm generates a new application secret key, which signs out existing sessions. To keep a
key, store it in a Juju secret and set the `app-secret-key` option to the secret ID:

```
juju add-secret my-app-secret-key value=<secret-string>
juju grant-secret my-app-secret-key httprequest-lego-provider
juju config httprequest-lego-provider app-secret-key=secret:<secret id>
```

The `django-secret-key` option is replaced by `app-secret-key`. Update any automation that sets
the old option, the old resource name `django-app-image`, or the `secret-storage` relation.

## Upgrade to the latest version

Upgrade the charm to the latest version:
`juju refresh httprequest-lego-provider --revision=<revision number>`

You should see the `httprequest-lego-provider` charm go to `Active` and `Idle` state after upgrading.

The upgrade automatically repairs the domain and domain-permission ID sequences left behind by
the database table rename. This also repairs deployments that already completed the table rename
and then encountered duplicate primary-key errors when adding domains or granting permissions.
Existing domains and permissions retain their IDs and data.
