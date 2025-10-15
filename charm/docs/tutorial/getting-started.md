<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Deploy the HTTP request Lego provider charm for the first time
<!-- vale Canonical.007-Headings-sentence-case = YES -->

## What you’ll do

- Deploy the [HTTP Request Lego Provider charm](https://charmhub.io/httprequest-lego-provider).
- Integrate with [the PostgreSQL K8s charm](https://charmhub.io/postgresql-k8s).
- Integrate with [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/#what-is-ingress) by using [NGINX Ingress Integrator](https://charmhub.io/nginx-ingress-integrator/).

## Requirements
- A working station, e.g., a laptop, with amd64 architecture.
- Juju 3 installed and bootstrapped to a MicroK8s controller. You can accomplish this process by following this guide: [How to manage your Juju deployment](https://documentation.ubuntu.com/juju/3.6/howto/manage-your-deployment/)
- NGINX Ingress Controller. If you're using [MicroK8s](https://microk8s.io/), this can be done by running the command `microk8s enable ingress`. For more details, see [Addon: Ingress](https://microk8s.io/docs/addon-ingress).

For more information about how to install Juju, see [Get started with Juju](https://documentation.ubuntu.com/juju/latest/tutorial/).

:warning: When using a Multipass VM, make sure to replace `127.0.0.1` IP addresses with the
VM IP in steps that assume you're running locally. To get the IP address of the
Multipass instance run ```multipass info my-juju-vm```.

## Steps
### Shell into the Multipass VM
> NOTE: If you're working locally, you don't need to do this step.

To be able to work inside the Multipass VM first you need to log in with the following command:
```
multipass shell my-juju-vm
```

### Set up the tutorial model
To easily clean up the resources and to separate your workload from the contents of this tutorial, set up a new model with the following command.

```
juju add-model httprequest-lego-provider-tutorial
```

### Deploy

The HTTP request Lego provider requires integration with [the PostgreSQL K8s charm](https://charmhub.io/postgresql-k8s) and [NGINX Ingress Integrator](https://charmhub.io/nginx-ingress-integrator/) for external access:

Deploy the charms:

```
juju deploy nginx-ingress-integrator --channel=v2/edge
juju trust nginx-ingress-integrator --scope=cluster
juju deploy postgresql-k8s --channel 14/stable
juju trust postgresql-k8s --scope=cluster
juju deploy httprequest-lego-provider --channel=latest/edge
```

To see the pod created by the charm, run `kubectl get pods -n httprequest-lego-provider-tutorial`. The output is similar to the following:

```
NAME                             READY   STATUS    RESTARTS   AGE
httprequest-lego-provider-0      2/2     Running   0          9m36s
```

Run [`juju status`](https://documentation.ubuntu.com/juju/3.6/reference/juju-cli/list-of-juju-cli-commands/status/#juju-status) to see the current status of the deployment. In the Unit list, you can see that the charm is waiting:

```
httprequest-lego-provider/0*  waiting   idle   10.1.180.77         Config git-repo is required
```

This means the required configurations have not been set yet.

### Configure the charm
> NOTE: For tutorial you can fork this [repo](https://github.com/canonical/httprequest-lego-provider/tree/main) and use you own fork and ssh key.
> If you fork the repo the `git-repo` will be in the form `git+ssh://git@github.com/<username>/httprequest-lego-provider.git@main`.
Provide the configurations `git-repo` and `git-ssh-key` required by the charm:

```
juju config httprequest-lego-provider git-repo=git+ssh://username@host/repo@branch
juju config httprequest-lego-provider git-ssh-key=**REDACTED**
```
You can see the message has changed:

```
httprequest-lego-provider/0*  waiting   idle   10.1.180.77         Waiting for database integrations
```

### Integrate the charm
For the charm to reach active status, integrate the charm with the PostgreSQL K8s charm and the NGINX Ingress Integrator charm:

```
juju integrate httprequest-lego-provider postgresql-k8s
juju integrate httprequest-lego-provider nginx-ingress-integrator
```

Run `juju status` and wait until the Application status is `Active`:

```
App                        Version  Status   Scale  Charm                      Channel      Rev  Address         Exposed  Message
httprequest-lego-provider           active       1  httprequest-lego-provider  latest/edge   17  10.152.183.194  no
```

In order to access the HTTP endpoints, you'll need configure a hostname and add it to Django's allow list and configure the path routes that will be accessible:
```
juju config nginx-ingress-integrator service-hostname=lego.local
juju config httprequest-lego-provider django-allowed-hosts=localhost,127.0.0.1,lego.local
juju config nginx-ingress-integrator path-routes="/admin,/present,/cleanup"
```

### Create a user and log in

To create a user, use the `create-user` action:
```
juju run httprequest-lego-provider/0 create-user username=my_user
```

The command will return the password of the created user.
If you are following the tutorial in your local machine, modify your `/etc/hosts` file so that it points to `127.0.0.1`:

```
echo 127.0.0.1 lego.local >> /etc/hosts
```

After that, visit `http://lego.local/present` to reach HTTP request Lego Provider, using the credentials returned from the `create-user` action to login.

### Clean up the environment
Congratulations! You have successfully finished the `httprequest-lego-provider` tutorial. You can now remove the model environment that you've created using the following command.

```
juju destroy-model --destroy-storage httprequest-lego-provider-tutorial
```

If you used Multipass, to remove the Multipass instance you created for this tutorial, use the following command.
```
multipass delete --purge my-juju-vm
```
Finally, remove the `127.0.0.1 lego.local` line from the `/etc/hosts` file.
