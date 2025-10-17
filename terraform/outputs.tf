# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.httprequest_lego.name
}

output "requires" {
  value = {
    logging = "logging"
  }
}

output "provides" {
  value = {
    certificates = "certificates"
    send-ca-cert = "send-ca-cert"
  }
}

output "endpoints" {
  value = {
    certificates = "certificates"
    logging      = "logging"
    send-ca-cert = "send-ca-cert"
  }
}
