# Deploy the Httprequest Lego Provider charm for the first time

## What you’ll do

- Deploy the [Httprequest Lego Provider charm](https://charmhub.io/httprequest-lego-provider).
- Integrate with [the PostgreSQL K8s charm](https://charmhub.io/postgresql-k8s).
- Integrate with [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/#what-is-ingress) by using [NGINX Ingress Integrator](https://charmhub.io/nginx-ingress-integrator/).

## Prerequisites

- Juju 3 installed.
- Juju controller and model created.

For more information about how to install Juju, see [Get started with Juju](https://juju.is/docs/olm/get-started-with-juju).

## Deploy the Httprequest Lego Provider charm

The HTTPRequest Lego provider requires integration with [the PostgreSQL K8s charm](https://charmhub.io/postgresql-k8s) and [NGINX Ingress Integrator](https://charmhub.io/nginx-ingress-integrator/) for external access:

Deploy the charms:

```bash
juju deploy nginx-ingress-integrator --channel=v2/edge
juju trust nginx-ingress-integrator --scope=cluster
juju deploy postgresql-k8s --channel 14/stable
juju trust postgresql-k8s --scope=cluster
juju deploy httprequest-lego-provider --channel=latest/edge
```

To see the pod created by the charm, run `kubectl get pods` on the namespace for the Juju model you've deployed the charm to. The output is similar to the following:

```bash
NAME                             READY   STATUS    RESTARTS   AGE
httprequest-lego-provider-0      2/2     Running   0          9m36s
```

Run [`juju status`](https://juju.is/docs/olm/juju-status) to see the current status of the deployment. In the Unit list, you can see that the charm is waiting:

```bash
httprequest-lego-provider/0*  waiting   idle   10.1.180.77         Config git-repo is required
```

This means the required configurations have not been set yet.

## Configure the Httprequest Lego Provider charm
 Provide the configurations `git-repo` and `git-ssh-key` required by the charm:

 ```bash
juju config httprequest-lego-provider git-repo=git+ssh://username@host/repo@branch
juju config httprequest-lego-provider git-ssh-key=**REDACTED**
```
You can see the message has changed:

```bash
httprequest-lego-provider/0*  waiting   idle   10.1.180.77         Waiting for database integrations
```

## Integrate the Httprequest Lego Provider charm
For the charm to reach active status, integrate the charm with the PostgreSQL K8s charm and the NGINX Ingress Integrator charm:

```bash
juju integrate httprequest-lego-provider postgresql-k8s
juju integrate httprequest-lego-provider nginx-ingress-integrator
```

Run `juju status` and wait until the Application status is `Active`:

```bash
App                        Version  Status   Scale  Charm                      Channel      Rev  Address         Exposed  Message
httprequest-lego-provider           active       1  httprequest-lego-provider  latest/edge   17  10.152.183.194  no
```

In order to access the HTTP endpoints, you'll need configure a hostname and add it to Django's allow list and configure the path routes that will be accessible:
```bash
juju config nginx-ingress-integrator service-hostname=lego.local
juju config httprequest-lego-provider django-allowed-hosts=localhost,127.0.0.1,lego.local
juju config nginx-ingress-integrator path-routes="/admin,/present,/cleanup"
```

