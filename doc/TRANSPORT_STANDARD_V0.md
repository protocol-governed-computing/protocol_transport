# PGC Transport Standard — V0

**Status:** Phase-1 frozen (semantic model). No constitutions, schemas-as-artifacts, or code are authorized by this document.
**Governs:** the meaning of the PGC transport boundary, protocol-neutrally.
**Supersedes:** the RI-0 / PGS realization of transport as `CC + RB + EV`.

> One line: **PGC Transport is not a protocol. It is a governed, protocol-neutral interaction boundary.**

---

## 1. Scope

### 1.1 What PGC Transport is

PGC Transport is the **governed boundary** between an external interaction protocol and a PGC execution universe. It defines, protocol-neutrally:

- how an external interaction is admitted into governed execution (**ingress**), and
- how a governed execution result is projected back out (**egress**).

Its purpose is a single invariant:

> **Many external protocols may bind to one Operation Identity; one Operation Identity resolves to one governed PGC invocation contract; the external protocol is replaceable, while the governed interaction remains stable.**

### 1.2 What PGC Transport is not

- It is **not** HTTP, JSON-RPC, CLI, WebSocket, or a message queue. Those are external protocols.
- It is **not** a second business-logic engine. It owns no domain truth, no state-transition validity, no capability selection.
- It is **not** an execution pipeline stage. `TI` and `TE` are **boundary contracts**, not steps in `IN → OP → CC → CT/CS`.
- It is **not** realized as a business `RB`. The RI-0 pattern of expressing the boundary through `CC + RB + EV` is retired (see §4, `RB_NOT_TRANSPORT_ABSTRACTION`).

---

## 2. Architectural topology

The transport model is a **boundary ring** around execution — not a line. The retired linear string

```
AC → TI → WF → IN → OP → CC → CT/CS → EV → TE
```

is preserved only as a historical **concern inventory**. It MUST NOT be read as a topology or an execution order, because a linear reading is precisely what caused RI-0 to implement the boundary as an inline `CC` stage.

Three independent dimensions:

- **Boundary ring** (spatial, at the edge): `TI` inbound, `TE` outbound.
- **Interior execution** (sequential): `IN → OP → CC → CT/CS`.
- **Cross-cutting** (span the whole interaction): `AC` (authority/context), `EV` (evidence).

```
                         EXTERNAL WORLD

     HTTP              JSON-RPC              CLI
       │                   │                  │
       ▼                   ▼                  ▼
 ┌───────────┐       ┌───────────┐      ┌───────────┐
 │ HTTP      │       │ RPC       │      │ CLI       │
 │ Adapter   │       │ Adapter   │      │ Adapter   │
 └─────┬─────┘       └─────┬─────┘      └─────┬─────┘
       │                   │                  │
       └───────────────────┼──────────────────┘
                           │
                           ▼
                External Protocol Binding        (adapter-owned; §3, Patch 2)
                           │
                           ▼
                  Operation Identity             (first-class; §3, Patch 1)
                           │
                           ▼
              Canonical Transport Request        (TRANSPORT_REQUEST_V0; §5)
                           │
        ┌──────────────────┼───────────────────────────────┐
        │  PGC DOMAIN       ▼                               │
        │           Operation Identity Resolution           │
        │                   ▼                               │
        │          ┌─────────────────┐                      │
        │          │ TI              │  Admission Contract   │
        │          └────────┬────────┘                      │
        │                   ▼                               │
        │          Compiled Invocation Contract             │
        │                   ▼                               │
        │             PGC Invocation                        │
        │                   ▼                               │
        │        governed target (WF in the RI)             │
        │                   ▼                               │
        │          IN → OP → CC → CT/CS                      │
        │                   ▼                               │
        │                  EV ───────────┐                  │
        │                                ▼                  │
        │                       ┌─────────────────┐         │
        │                       │ TE              │ Egress   │
        │                       └────────┬────────┘ Contract │
        │        AC = cross-cutting authority/context        │
        └───────────────────┼───────────────────────────────┘
                            ▼
              Canonical Transport Response       (TRANSPORT_RESPONSE_V0; §5)
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
           HTTP           RPC            CLI      (Response Projection; §7)
```

`TI` and `TE` bound the interaction. `AC` and `EV` are cross-cutting, not stages.

---

## 3. Semantic vocabulary

| Term | Layer | Governed? | Definition |
|---|---|---|---|
| **External Protocol** | 1 | No | Wire mechanics: HTTP, JSON-RPC, CLI, WebSocket, MQ. How bytes/messages are exchanged. |
| **Protocol Adapter** | 2 | No (thin, non-authorial) | Translates External Protocol ↔ Canonical Transport Request/Response. Owns no domain meaning. |
| **External Protocol Binding** | 2 | Formal concept; **adapter-owned config in V0** | Declared map from a protocol selector (HTTP route+method / RPC method spelling / CLI verb) to an **Operation Identity**. Protocol-specific. `XB_` artifactization deferred (Patch 2). |
| **Operation Identity** | 3 | **Yes** | The stable, protocol-neutral **identity** of a governed interaction (e.g. `collatz.compute`) — an addressable identity within the PGC governance universe, independent of any workflow, implementation, external protocol, or transport representation. MUST be uniquely resolvable within the applicable governance universe; MUST NOT equal a Workflow Identity. |
| **Canonical Transport Request** | 3 | **Yes** (`TRANSPORT_REQUEST_V0`) | Protocol-neutral request contract. The single ingress interop object. |
| **TI — Transport Ingress Contract** | 3 | **Yes** | Declares admission semantics for an Operation Identity: input contract reference, context requirements, and an **invocation binding** (operation identity → governed executable target). Declared here, **resolved by the compiler**. |
| **PGC Invocation** | 3→4 | runtime construct (not an artifact) | The governed act of executing the TI-bound target under TI's compiled constraints, yielding a PGC Result. |
| **PGC Result** | 4 | Runtime construct; **not inherently a transport artifact** | Outcome of a PGC Invocation (`outcome`, `class`, `payload`, `evidence`, `errors`). It exists whether or not a transport boundary exists; the boundary **projects** it into a Canonical Transport Response via `TE`. |
| **TE — Transport Egress Contract** | 3 | **Yes** | **Declares** the governed classification of PGC outcomes into a protocol-neutral **Result Class**, and the output/evidence exposure contract. A declaration compiled and applied at runtime — not a runtime decision engine. |
| **Canonical Transport Response** | 3 | **Yes** (`TRANSPORT_RESPONSE_V0`) | Protocol-neutral response contract. The single egress interop object. |
| **Result Class** | 3 | **Yes** (via TE) | `SUCCESS \| VIOLATION \| UNAUTHORIZED \| EXECUTION_FAILURE \| OPERATION_NOT_FOUND`. Carries **no** protocol semantics. `OPERATION_NOT_FOUND` means the requested Operation Identity is absent from the governance universe — a domain resource-not-found is a *domain* result, not a transport one. |
| **Response Projection** | 2 | No | Adapter map from `Result Class` + Canonical Response → protocol representation (HTTP status, RPC error, CLI exit). |

**Patch 1 — Operation Identity is first-class, and the boundary is three distinct relationships, not one flat resolution:**

```
Identification:  External Protocol Binding → Operation Identity          (what governed operation is referred to?)
Admission:       Operation Identity        → TI                          (under what governed contract may it enter?)
Execution:       TI → PGC Invocation Contract → governed executable target (what governed execution is invoked?)
```

not `route → WF` and not `route → TI → WF`. `TI → WF` is an **implementation realization** of the invocation binding, not the transport ontology: the boundary is indifferent to whether the target is a `WF`, a capability, or a future execution construct. The public identity `collatz.compute` is stable; the implementation `WF_COLLATZ_CONJECTURE_V0` is not. Re-pointing `collatz.compute` from `TI_COLLATZ_COMPUTE_V0` to `TI_COLLATZ_COMPUTE_V1` MUST NOT require any adapter change.

**Patch 2 — External Protocol Binding is a formal concept, not yet an artifact.** In V0 it is adapter-owned configuration. The distinction is governance domain:
- *PGC governance* — what an operation means, whether it is permitted, which WF serves it, what inputs are valid, what result classes exist.
- *Adapter configuration* — which route, which CLI syntax, which RPC method spelling, which wire encoding.

The second may be auditable without being a PGC artifact. `XB_` is defined semantically here and deferred; if every public endpoint must eventually be compiler-verifiable, `XB_` becomes necessary at that point.

---

## 4. Normative invariants

All keywords per RFC 2119.

- **`TRANSPORT_PROTOCOL_INDEPENDENCE`** — A PGC transport contract (`TI`, `TE`, canonical request/response) MUST NOT depend on HTTP, RPC, CLI, or any other external protocol.
- **`OPERATION_IDENTITY_INDEPENDENCE`** — An Operation Identity MUST NOT be identical to a Workflow Identity. (Patch 1)
- **`ADAPTER_NON_AUTHORIAL`** — A Protocol Adapter MUST NOT determine business/domain semantics. It translates protocol mechanics only.
- **`COMPILED_INVOCATION_RESOLUTION`** — Operation-to-target resolution (the governed executable target), input-contract existence/compatibility, and closure validity MUST be determined before runtime execution. The runtime MUST NOT interpret arbitrary schema semantics at request time.
- **`RESULT_CLASS_PROTOCOL_INDEPENDENCE`** — A PGC Result Class MUST NOT encode protocol-specific response semantics (no HTTP status, no RPC error code). (Patch 4)
- **`RESPONSE_PROJECTION_EXTERNAL`** — Mapping a canonical result to HTTP status, RPC error, CLI exit code, or equivalent MUST occur outside the PGC transport contract, in the adapter. (Patch 4)
- **`TI_BOUNDARY_NOT_STAGE`** — `TI` and `TE` are boundary contracts. They MUST NOT be modeled or implemented as inline execution stages within `IN → OP → CC → CT/CS`. (§2)
- **`RB_NOT_TRANSPORT_ABSTRACTION`** — The transport boundary MUST NOT require a business `RB` as its semantic abstraction. Adapters MAY use implementation mechanisms internally, but transport *semantics* are never expressed as an `RB`.
- **`TRANSPORT_DOMAIN_SEPARATION`** — A PGC transport contract MUST NOT define domain state-transition semantics, domain resource semantics, or domain-specific result interpretation. Domain semantics MUST enter governed execution through declared PGC artifacts and MUST NOT be introduced by an adapter, `TI`, or `TE`.
- **`OPERATION_IDENTITY_RESOLVABLE`** — An Operation Identity MUST be uniquely resolvable within the applicable governance universe.
- **`INVOCATION_TARGET_ABSTRACT`** — A `TI` binds an Operation Identity to a *governed executable target*; the transport contract MUST NOT assume that target is a Workflow.
- **`TI_INPUT_CONTRACT_BY_REFERENCE`** — A `TI` MUST reference an existing governed input contract and MUST NOT define operation input semantics inline.

---

## 5. Canonical request and response schemas

Represented here as the **Canonical Transport Contract**. The "envelope" is merely its serialization; the contract is the governed object. The canonical transport contract is **representation-independent**: JSON is one serialization and is not normative unless separately specified. In Phase 3 these become schema artifacts `TRANSPORT_REQUEST_V0` and `TRANSPORT_RESPONSE_V0`.

### 5.1 `TRANSPORT_REQUEST_V0`

```json
{
  "request_id":      "string",
  "operation":       "OperationIdentity",
  "actor":           {},          // transport-carried governance input; delegated to AC, not evaluated in V0
  "context":         {},          // transport-carried governance input; delegated to AC, not evaluated in V0
  "input":           {},          // operation input, conforming to TI's input contract
  "correlation_id":  "string",    // reserved + PROPAGATED in V0 (tracing/evidence)
  "idempotency_key": "string",    // reserved + DECLARED, NOT ENFORCED in V0
  "metadata":        {}           // open extension
}
```

**Patch 6 — correlation vs idempotency are distinct.** `correlation_id` is an identity/tracing concern and is propagated through evidence in V0. `idempotency_key` is a *behavioral guarantee* (dedup against persistent state); carrying the key MUST NOT be taken to imply idempotent behavior. It is reserved and declared only.

### 5.2 `TRANSPORT_RESPONSE_V0`

```json
{
  "request_id":   "string",
  "outcome":      "SUCCESS | FAILURE",   // binary
  "result_class": "ResultClass",         // SUCCESS | VIOLATION | UNAUTHORIZED | EXECUTION_FAILURE | OPERATION_NOT_FOUND
  "result":       {},                    // payload on success; null on failure
  "evidence":     [],                    // references (e.g. trace ids)
  "errors":       []                     // populated on failure
}
```

`actor`/`context` are **transport-carried governance inputs** whose interpretation is delegated to the authority/context subsystem — V0 carries them structurally but does not evaluate them. With the reservation of `correlation_id`/`idempotency_key`, they are **forward-compatibility slots**: no V0 semantics, no version bump when `AC`/idempotency arrive.

---

## 6. TI semantics

A `TI` **declares** an ingress contract. It does not validate at runtime in the schema-interpretation sense (Patch 3).

A `TI` declares:

```
TI
 ├── operation identity          (the public name it admits)
 ├── input contract reference    (a declared, named contract — never inline schema logic)
 ├── context requirements        (what actor/context the operation requires; inert in V0)
 └── invocation binding          (operation identity → governed executable target)
```

A `TI` MUST reference an existing governed input contract; it MUST NOT define operation input semantics inline. This preserves *operation admission ≠ data contract*, and prevents `TI` from becoming a disguised schema artifact.

Division of labor:

```
TI declares  ──►  Compiler resolves & validates  ──►  Runtime enforces the compiled boundary
```

- **Compiler MUST verify:** the operation exists, the input contract exists and is type-compatible, the **invocation target** exists (a governed executable target — a `WF` in the current RI), and the closure is valid.
- **Runtime MUST:** resolve an incoming Canonical Request against the *already-compiled* TI and perform a deterministic invocation. It MUST NOT decide arbitrary semantics at request time.

Consistent with the central PGC principle: **the compiler decides; the runtime executes.**

---

## 7. TE semantics

A `TE` **declares** classification policy; the compiler validates it; the runtime applies it; the adapter **projects**. A PGC Result exists independent of transport — `TE` projects it, it does not own it.

```
PGC Result  ──►  TE (declared classification, compiled)  ──►  Canonical Response  ──►  Adapter Response Projection
```

A `TE` declares:

```
TE
 ├── result classification policy  (PGC outcome → Result Class)
 ├── output contract               (which result payload is exposed)
 └── evidence exposure policy       (which evidence references leave the boundary)
```

Result Class is governed and protocol-neutral:

```
SUCCESS | VIOLATION | UNAUTHORIZED | EXECUTION_FAILURE | OPERATION_NOT_FOUND
```

Projection is adapter-owned and protocol-specific — the mapping table lives in the adapter, never in `TE`:

```
VIOLATION
    ├── HTTP → 400
    ├── RPC  → InvalidParams
    └── CLI  → exit 2
```

`RESULT_CLASS_PROTOCOL_INDEPENDENCE` forbids any HTTP/RPC/CLI semantics from leaking backward into `TE`.

---

## 8. Collatz conformance example

The same operation, `collatz.compute(15)`, through three protocols, converging on one governed interaction.

**Three wires → three External Protocol Bindings → one Canonical Request:**

```
HTTP   POST /collatz  {"number":15}              POST /collatz      → collatz.compute
RPC    {"method":"collatz.compute",              method             → collatz.compute
        "params":{"number":15}}
CLI    collatz compute 15                        verb + positional  → collatz.compute
```

**Canonical Transport Request (Layer 3 sees only this):**

```json
{
  "request_id": "abc-123",
  "operation": "collatz.compute",
  "actor": {},
  "context": {},
  "input": { "number": 15 },
  "correlation_id": "abc-123",
  "idempotency_key": null,
  "metadata": {}
}
```

**Ingress —** `TI_COLLATZ_COMPUTE_V0`: declares input contract (`number:int`, required); context requirements none (V0); binds `collatz.compute → WF_COLLATZ_CONJECTURE_V0`. Resolved and validated at compile time.

**Execution —** `WF_COLLATZ_CONJECTURE_V0` → PGC Result `{ steps: 17 }` + evidence.

**Egress —** `TE_COLLATZ_COMPUTE_V0`: classifies `SUCCESS`; exposes `{number, steps}`; evidence policy = reference-only.

**Canonical Transport Response:**

```json
{
  "request_id": "abc-123",
  "outcome": "SUCCESS",
  "result_class": "SUCCESS",
  "result": { "number": 15, "steps": 17 },
  "evidence": ["trace:..."],
  "errors": []
}
```

**Three Response Projections (Layer 2 again):**

```
HTTP  200  + JSON body
RPC   { "id":"abc-123", "result": { "number":15, "steps":17 } }
CLI   stdout JSON, exit 0
```

Failure path illustration (`number` out of range):

```json
{ "request_id":"abc-123", "outcome":"FAILURE", "result_class":"VIOLATION",
  "result": null, "evidence": [], "errors": [ { "code":"INPUT_OUT_OF_RANGE" } ] }
```
→ HTTP 400 · RPC InvalidParams · CLI exit 2.

The invariant holds: **every external protocol is replaceable; the governed interaction is not.**

---

## 9. Explicit V0 exclusions

Out of scope for Transport Standard V0 — reserved structurally, not implemented:

- **`AC` enforcement** — `actor`/`context` are carried as governance inputs but not evaluated; no authority evaluation in V0.
- **Idempotency enforcement** — `idempotency_key` declared, not enforced.
- **`XB_` artifact kind** — External Protocol Binding stays adapter-owned config.
- **WebSocket and Message Queue adapters** — only HTTP, RPC, CLI are modeled.
- **RB rework beyond de-abstraction** — transport no longer *requires* RB semantically; wholesale RB deletion is a migration task, not a V0 deliverable.
- **Constitutions** — `CONSTITUTION_TRANSPORT_{ENVELOPE,INGRESS,EGRESS}` are Phase 2 and MUST NOT be created until this document is frozen and accepted.

---

## Phase roadmap

| Phase | Deliverable | Repo(s) |
|---|---|---|
| **1 (this doc)** | Semantic model — vocabulary, topology, invariants, canonical schemas, TI/TE semantics, Collatz conformance | `transport/doc/` |
| 2 | Governing constitutions (envelope, TI, TE) | `pgc_charter` / governance |
| 3 | Compiler recognition of `TI_`/`TE_` kinds + `TRANSPORT_REQUEST/RESPONSE_V0` schemas; snapshot assembly | `protocol_compiler`, `snapshot_assembler` |
| 4 | First `TI_`/`TE_COLLATZ_COMPUTE_V0` + thin HTTP adapter reusing the existing Collatz UI | `transport/`, `platform/reference_workloads`, `protocol_runtime` |
| 5 | RPC + CLI adapters against the *same* TI/TE — proves protocol-neutrality | `transport/` |

---

## Final invariant

> **Many external protocols may bind to one Operation Identity; one Operation Identity resolves to one governed PGC invocation contract; the external protocol is replaceable, while the governed interaction remains stable.**