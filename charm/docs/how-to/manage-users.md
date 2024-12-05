# How to manage users

Users will be leveraged to determine if a request is authorised to manage a specific domain. To add a new user simply run 
`juju run --wait=5s httprequest-lego-provider/0 create-user username=example-user`. The action will generate and output a password:
```bash
result: |
  Created or updated "example" with password "**REDACTED**"
```

If the action is rerun, a new password will be generated.
