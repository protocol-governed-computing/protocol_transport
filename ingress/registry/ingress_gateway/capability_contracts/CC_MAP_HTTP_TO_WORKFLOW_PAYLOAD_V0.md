# CC_MAP_HTTP_TO_WORKFLOW_PAYLOAD_V0

## Header

- **Artifact Code:** CC_MAP_HTTP_TO_WORKFLOW_PAYLOAD_V0
- **Artifact Kind:** capability_contract
- **Governed By:** CONSTITUTION_CAPABILITY_CONTRACTS_V0
- **Version:** v0
- **Status:** draft
- **Dependencies:** capability_transforms::CT_PURE_PASSTHROUGH_V0

---

## 1. Intent

Map validated HTTP request body to canonical workflow payload. For the transaction use case, HTTP body maps 1:1 to workflow payload. Future TI definitions may bind different CT atoms for field renaming or enrichment.

## 2. Pipeline

1. capability_transforms::CT_PURE_PASSTHROUGH_V0

---

## Machine

```yaml
cc_code: CC_MAP_HTTP_TO_WORKFLOW_PAYLOAD_V0
version: v0
governed_by: fb.topology::CONSTITUTION_CAPABILITY_CONTRACT_V0

core:
  summary: Map validated HTTP request body to canonical workflow payload

  inputs:
    request_body:
      type: object
      required: true

  outputs:
    canonical_payload:
      type: object

  result_status_contract:
    allowed: [SUCCESS, VIOLATION]
    on_input_failure: VIOLATION

  pipeline:
    - step: map_to_payload
      transform: capability_transforms::CT_PURE_PASSTHROUGH_V0
      op: PASSTHROUGH
      inputs:
        value: $.inputs.request_body
      outputs:
        canonical_payload: $.capability_result.value.value
      on_ct_result:
        on_success: SUCCESS
        on_failure: VIOLATION
      on_result:
        SUCCESS: exit
        VIOLATION: exit
```
