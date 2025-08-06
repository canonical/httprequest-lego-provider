# How to manage domains

To manage the list of domains a user is allowed to view or request changes to, the following actions are available:
- `allow-domains`
- `revoke-domains`
- `list-domains`

The `allow-domains` and `revoke-domains` support the following inputs:
- `domains`: This input is used to allow a user access to a particular domain only. For example, if we run `allow-domains` with `domains="example.domain.com"`, the user will be able to request a certificate for `example.domain.com` only.
- `subdomains`: This input is used to allow a user access to all the subdomains under a domain. For example, if we run `allow-domains` with `subdomains="example.domain.com"`, the user will be able to request a certificate for any subdomain under `example.domain.com`, but not a certificate for `example.domain.com` itself or a wildcard certificate for `example.domain.com`.

The above-mentioned commands can be run with one or more of the above inputs at the same time.

## Allowing domains
To add domains to the list of allowed domains, run `juju run --wait=5s httprequest-lego-provider/0 allow-domains username=example domains="example.domain.com,example2.domain.com" subdomains="example.domain.com,example3.domain.com"`.

## Revoking domains
To remove domains from the list of allowed domains, run `juju run --wait=5s httprequest-lego-provider/0 revoke-domains username=example domains="example.domain.com,example2.domain.com" subdomains="example.domain.com,example3.domain.com"`.

## Listing domains
To query the list of allowed domains for a user, run `juju run --wait=5s httprequest-lego-provider/0 list-domains username=example` and the list of domains will be returned as in
```bash
result: |
example:
    domains:
        example.domain.com, example2.domain.com
    subdomains:
        example.domain.com, example3.domain.com
```

You can also query the list of allowed domains for all users by running `juju run --wait=5s httprequest-lego-provider/0 list-domains --string-args username='*'`
