# How to troubleshoot API timeouts

Some of the API calls will execute behind the scenes requests over the network.

In the event you have a slow network connection this might result in timeouts manifesting as HTTP 500 errors for the API caller. This is more likely the bigger your git repository is. If this is your case, adjusting the [webserver-timeout](https://charmhub.io/httprequest-lego-provider/configurations#webserver-timeout) configuration can help you solve this.

Note that if the HTTP Request LEGO provider is sitting behind a reverse proxy, the timeout might be occurring here. In the case of [Nginx ingress integrator](https://charmhub.io/nginx-ingress-integrator), you can change the [proxy-read-timeout](https://charmhub.io/nginx-ingress-integrator/configurations#proxy-read-timeout) configuration to adjust the timeout.
