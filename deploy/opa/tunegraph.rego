package tunegraph

import rego.v1

default allow := {"allow": false, "reason": "Default deny"}

allow := {"allow": true, "decision_id": "default-development", "reason": "Approved patch plan"} if {
  input.environment != "production"
  every patch in input.patches {
    patch.state != "revoked"
  }
}

allow := {"allow": true, "decision_id": "default-production", "reason": "Production-approved patches"} if {
  input.environment == "production"
  every patch in input.patches {
    patch.state in {"production", "canary"}
  }
}
