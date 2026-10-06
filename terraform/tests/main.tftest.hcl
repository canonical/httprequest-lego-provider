# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    channel    = "latest/edge"
    # renovate: depName="httprequest-lego-provider"
    revision = 79
  }

  assert {
    condition     = output.application.name == "httprequest-lego-provider"
    error_message = "httprequest-lego-provider application name did not match expected"
  }
}
