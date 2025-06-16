# How to troubleshoot API timeouts

Some of the API calls will execute requests over the network from behind the scenes.

In the event you have a slow network connection this might result in timeouts manifesting as HTTP 500 errors for the API caller. This is more likely for larger Git repositories. If this is your case, adjusting the [`webserver-timeout`](https://charmhub.io/httprequest-lego-provider/configurations#webserver-timeout) configuration can help you solve this.

For the scenario described above, you should be able to find a log entry containing the following:
```
  File "/usr/lib/python3.10/subprocess.py", line 1154, in communicate
    stdout, stderr = self._communicate(input, endtime, timeout)
  File "/usr/lib/python3.10/subprocess.py", line 2021, in _communicate
    ready = selector.select(timeout)
  File "/usr/lib/python3.10/selectors.py", line 416, in select
    fd_event_list = self._selector.poll(timeout)
  File "/lib/python3.10/site-packages/gunicorn/workers/base.py", line 204, in handle_abort
    sys.exit(1)
SystemExit: 1
```

Note that if the HTTP Request LEGO provider is sitting behind a reverse proxy, the timeout might be occurring here. In the case of [Nginx ingress integrator](https://charmhub.io/nginx-ingress-integrator), you can change the [`proxy-read-timeout`](https://charmhub.io/nginx-ingress-integrator/configurations#proxy-read-timeout) configuration to adjust the timeout.
