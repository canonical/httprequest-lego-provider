# How to manage domains

To manage the list of domains a user is allowed to request changes to, the following actions are available

## Allowing domains
To add domains to the list of allowed domains, run `juju run --wait=5s httprequest-lego-provider/0 allow-domains username=example domains="example.domain.com,example2.domain.com"`.

## Revoking domains
To remove domains from the list of allowed domains, run `juju run --wait=5s httprequest-lego-provider/0 revoke-domains username=example domains="example.domain.com,example2.domain.com"`.

## Listing domains
To query the list of allowed domains for a user, run `juju run --wait=5s httprequest-lego-provider/0 list-domains username=example` and the list of domains will be returned as in
```bash
result: |
  _acme-challenge.example.domain.com, _acme-challenge.example2.domain.com
```
