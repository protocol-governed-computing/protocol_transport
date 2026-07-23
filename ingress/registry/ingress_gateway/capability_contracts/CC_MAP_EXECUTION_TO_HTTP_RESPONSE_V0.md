# CC_MAP_EXECUTION_TO_HTTP_RESPONSE_V0

## Header

- **Artifact Code:** CC_MAP_EXECUTION_TO_HTTP_RESPONSE_V0
- **Artifact Kind:** capability_contract
- **Governed By:** CONSTITUTION_CAPABILITY_CONTRACTS_V0
- **Version:** v0
- **Status:** draft
- **Dependencies:** capability_transforms::CT_PURE_MAP_RESULT_TO_HTTP_V0

---

## 1. Intent

Map execution result to HTTP response envelope. Translates result_status to HTTP status codes using a governed mapping.

## 2. Pipeline

1. capability_transforms::CT_PURE_MAP_RESULT_TO_HTTP_V0

## 3. Status Mapping

| Result Status | HTTP Status |
|--------------|-------------|
| SUCCESS | 200 |
| VIOLATION | 422 |
| NOT_FOUND | 404 |
| BACKEND_ERROR | 500 |
| TIMEOUT | 504 |

---

## Machine

```yaml
cc_code: CC_MAP_EXECUTION_TO_HTTP_RESPONSE_V0
version: v0
governed_by: fb.topology::CONSTITUTION_CAPABILITY_CONTRACT_V0

core:
  summary: Map execution result to HTTP response envelope

  inputs:
    execution_result:
      type: object
      required: true

  outputs:
    http_status:
      type: integer
    response_body:
      type: object
    result_status:
      type: string

  result_status_contract:
    allowed: [SUCCESS, VIOLATION, NOT_FOUND, BACKEND_ERROR, TIMEOUT]
    on_input_failure: BACKEND_ERROR

  pipeline:
    - step: map_result_to_http
      transform: capability_transforms::CT_PURE_MAP_RESULT_TO_HTTP_V0
      op: MAP_RESULT_TO_HTTP
      inputs:
        execution_result: $.inputs.execution_result
        mapping:
          SUCCESS: 200
          VIOLATION: 422
          NOT_FOUND: 404
          BACKEND_ERROR: 500
          TIMEOUT: 504
      outputs:
        http_status: $.capability_result.value.http_status
        response_body: $.capability_result.value.response_body
        result_status: $.capability_result.value.result_status
      on_ct_result:
        on_success: SUCCESS
        on_failure: BACKEND_ERROR
      on_result:
        SUCCESS: exit
        VIOLATION: exit
        NOT_FOUND: exit
        BACKEND_ERROR: exit
        TIMEOUT: exit
```
