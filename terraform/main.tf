# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "lego" {
  name  = var.app_name
  model = var.model

  charm {
    name     = "httprequest-lego-provider"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config      = var.config
  constraints = var.constraints
  units       = var.units
}
