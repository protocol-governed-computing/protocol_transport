# TRANSPORT_RESPONSE_V0

**Kind:** transport canonical contract (response)
**Governs:** the single, protocol-neutral egress interop object (Transport Standard V0 §5.2).
**Status:** cut-#1 hand-authored. Promoted to a compiled schema artifact in Phase 3.

The Canonical Transport Response carries a governed, protocol-neutral `result_class`
(`RESULT_CLASS_PROTOCOL_INDEPENDENCE`). Mapping it to an HTTP status / RPC error / CLI
exit code is Response Projection, which happens in the adapter, never here
(`RESPONSE_PROJECTION_EXTERNAL`).

## Machine

```yaml
contract_code: TRANSPORT_RESPONSE_V0
version: v0

fields:
  request_id:   { type: string, required: true }
  outcome:      { type: enum,   required: true, values: [SUCCESS, FAILURE] }
  result_class: { type: enum,   required: true, values: [SUCCESS, VIOLATION, UNAUTHORIZED, EXECUTION_FAILURE, NOT_FOUND] }
  result:       { type: object, required: false, note: "payload on success; null on failure" }
  evidence:     { type: array,  required: true,  note: "references only (e.g. trace ids)" }
  errors:       { type: array,  required: true,  note: "populated on failure; empty on success" }
```