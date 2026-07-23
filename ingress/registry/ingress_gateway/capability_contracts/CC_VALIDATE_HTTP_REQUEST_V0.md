# CC_VALIDATE_HTTP_REQUEST_V0

## Header

- **Artifact Code:** CC_VALIDATE_HTTP_REQUEST_V0
- **Artifact Kind:** capability_contract
- **Governed By:** CONSTITUTION_CAPABILITY_CONTRACTS_V0
- **Version:** v0
- **Status:** draft
- **Dependencies:** capability_transforms::CT_PURE_VALIDATE_RECORD_STRUCTURE_V0

---

## 1. Intent

Validate HTTP request body against TI admission schema.

## 2. Pipeline

1. capability_transforms::CT_PURE_VALIDATE_RECORD_STRUCTURE_V0

## 3. Inputs

| Field | Type | Required |
|-------|------|----------|
| request_body | object | yes |
| ti_code | string | yes |

## 4. Outputs

| Field | Type |
|-------|------|
| result_status | string |
| violations | array |

---

## Machine

```yaml
cc_code: CC_VALIDATE_HTTP_REQUEST_V0
version: v0
governed_by: fb.topology::CONSTITUTION_CAPABILITY_CONTRACT_V0

core:
  summary: Validate HTTP request body against TI admission schema

  inputs:
    request_body:
      type: object
      required: true
    ti_code:
      type: string
      required: true

  outputs:
    result_status:
      type: string
    violations:
      type: array

  result_status_contract:
    allowed: [SUCCESS, VIOLATION]
    on_input_failure: VIOLATION

  pipeline:
    - step: validate_request
      transform: capability_transforms::CT_PURE_VALIDATE_RECORD_STRUCTURE_V0
      op: VALIDATE_RECORD_STRUCTURE
      inputs:
        record: $.inputs.request_body
        schema:
          actor_record:
            type: object
            required: true
          wallet_id:
            type: string
            required: true
          to_address:
            type: hex_string
            required: true
            pattern: "^0x[0-9a-fA-F]{40}$"
          value:
            type: integer_string
            required: true
            min_value: 0
          mnemonic:
            type: string
            required: true
      outputs:
        result_status: $.capability_result.value.result_status
        violations: $.capability_result.value.violations
      on_ct_result:
        on_success: SUCCESS
        on_failure: VIOLATION
      on_result:
        SUCCESS: exit
        VIOLATION: exit

  error_codes:
    VIOLATION: HTTP_REQUEST_INVALID
```
