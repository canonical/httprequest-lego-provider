# How to manage users

Users will be leveraged to dertermine if a request is authorized to manage a specific domain. To add a new user simply run 
`juju run --wait=5s httprequest-lego-provider/0 create-user username=example-user`. The action will generate and output a password.

If the action is rerun, a new password will be generated.
