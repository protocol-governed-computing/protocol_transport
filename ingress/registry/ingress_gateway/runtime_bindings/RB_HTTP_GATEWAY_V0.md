# RB_HTTP_GATEWAY_V0

## Header

- **Artifact Code:** RB_HTTP_GATEWAY_V0
- **Artifact Kind:** runtime_binding
- **Governed By:** CONSTITUTION_RUNTIME_BINDINGS_V0
- **Version:** v0
- **Status:** draft
- **Dependencies:**
  - capability_side_effects::CS_WORKFLOW_GATEWAY_V0

---

## 1. Purpose

Bind transport-domain capability contracts to their runtime implementations. CS_WORKFLOW_GATEWAY_V0 is infrastructure-owned; this binding connects transport CCs to the infrastructure execution mechanism.

## 2. Bindings

| CS Code | Host | Module |
|---------|------|--------|
| capability_side_effects::CS_WORKFLOW_GATEWAY_V0 | WorkflowGatewayRuntime | infrastructure |

---

## Machine

```yaml
rb_code: RB_HTTP_GATEWAY_V0
fqdn: ingress_gateway::RB_HTTP_GATEWAY_V0
version: v0
governed_by: fb.topology::CONSTITUTION_RUNTIME_BINDING_V0

parameters:
  - module_data_root

core:
  summary: Bind transport CCs to HTTP gateway implementations

  bindings:
    capability_side_effects::CS_WORKFLOW_GATEWAY_V0:
      host: WorkflowGatewayRuntime
      policy:
        default_runtime_binding: RB_CAPABILITY_BINDINGS_V0
        strict: true

    capability_side_effects::CS_MUTABLE_JSON_V0:
      module: pgs_side_effects.side_effects.cs_mutable_json_v0
      callable: execute

    capability_side_effects::CS_SEND_EMAIL_V0:
      module: pgs_side_effects.side_effects.cs_send_email_v0
      callable: execute
```
