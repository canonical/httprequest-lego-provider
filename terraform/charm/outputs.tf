# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "The deployed Juju application object."
  value       = juju_application.httprequest_lego
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    certificates = {
      kind     = "endpoint"
      name     = juju_application.httprequest_lego.name
      endpoint = "certificates"
    }
    send-ca-cert = {
      kind     = "endpoint"
      name     = juju_application.httprequest_lego.name
      endpoint = "send-ca-cert"
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    logging = {
      kind     = "endpoint"
      name     = juju_application.httprequest_lego.name
      endpoint = "logging"
    }
    postgresql = {
      kind     = "endpoint"
      name     = juju_application.httprequest_lego.name
      endpoint = "postgresql"
    }
  }
}
