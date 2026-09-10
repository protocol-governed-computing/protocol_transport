# TRANSPORT_REQUEST_V0

**Kind:** transport canonical contract (request)
**Governs:** the single, protocol-neutral ingress interop object (Transport Standard V0 §5.1).
**Status:** cut-#1 hand-authored. Promoted to a compiled schema artifact in Phase 3.

The Canonical Transport Request is the *only* object Layer 3 sees. Every external
protocol (HTTP, RPC, CLI) is translated into this shape by its adapter; the governed
interaction never depends on the wire protocol (`TRANSPORT_PROTOCOL_INDEPENDENCE`).

## Machine

```yaml
contract_code: TRANSPORT_REQUEST_V0
version: v0

fields:
  request_id:      { type: string,  required: true,  note: "adapter-assigned id for this interaction" }
  operation:       { type: string,  required: true,  note: "Operation Identity — public, stable; NEVER a Workflow Identity" }
  actor:           { type: object,  required: false, note: "reserved for AC — not interpreted in V0" }
  context:         { type: object,  required: false, note: "reserved for AC — not interpreted in V0" }
  input:           { type: object,  required: true,  note: "operation input, conforming to the TI input contract" }
  correlation_id:  { type: string,  required: false, note: "reserved + propagated through evidence in V0" }
  idempotency_key: { type: string,  required: false, note: "reserved + declared, NOT enforced in V0 (Patch 6)" }
  metadata:        { type: object,  required: false, note: "open extension" }
```