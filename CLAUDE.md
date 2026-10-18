## Response Style

Keep responses under ~400 output tokens. Prefer terse bullet summaries over prose narration. When a full document is needed, Write it to a file instead of printing it in chat.

## Document Authoring Rules

- Never include internal review notes, meta-scaffolding, work-order framing, cross-reference stubs, or 'Status:' metadata in deliverable docs or figures.
- Do not add dates to papers or appendices.
- An 'outline' means a clean reader-facing outline of the paper, not an execution plan.

# Transport (PGC) — Architectural Rules

## What this repo is

The **domain-neutral transport boundary engine**. It implements the PGC Transport
Standard and knows *how to transport* — it declares nothing about *what* is transported.

**Governed by `TRANSPORT_STANDARD_V0.md` (Phase-1 frozen). Read it before touching
anything here.** That document is the semantic authority; this file is how to work in the code.

> `protocol_transport/` knows how to transport. The **domain/platform** declares what may be
> transported (TI/TE boundary contracts live there, not here).

## Layout

```
contracts/      canonical, protocol-neutral interop objects (TRANSPORT_REQUEST/RESPONSE_V0)
pgc_transport/  the one import package
  request.py    the Canonical Transport Request, protocol-neutral; every adapter builds it here
  resolver/     generic engine: operation → TI → handler → TE → Canonical Response
  adapters/     protocol adapters (Layer 2)
    http/       HTTP mechanics + External Protocol Binding (data) + static mounts
    cli/        the `pgc_transport` command: `call` (one request) and `http` (serve the HTTP adapter)
TRANSPORT_STANDARD_V0.md  the frozen semantic model
run_http.sh     domain-neutral launcher (env-provisioned; names no workload)
```

Import package (transport repo root on PYTHONPATH): `pgc_transport`, holding
`pgc_transport.request`, `pgc_transport.adapters` and `pgc_transport.resolver`. One distinctive
top-level name, so an install puts nothing generic into site-packages.

## The acid test (MANDATORY, non-negotiable)

**The engine contains ZERO domain knowledge.** `grep -r pgc_transport/` for any workload,
operation, or field name (`collatz`, `number`, `steps`, a route literal, …) → **find nothing**.
Every domain fact — routes, operations, WF bindings, input/output mapping, result
classification — arrives as **data/config the adapter is POINTED at**. Never hardcoded,
never discovered by convention.

If you're about to write `if operation == "..."`, a workload path, or a domain field name in
`pgc_transport/`, stop — it belongs in a TI/TE artifact or a config file instead.

## Where boundary declarations live (NOT here)

`TI`/`TE` (Transport Ingress/Egress Contracts) are **domain-governed** and live with the
domain surface — a business/workload domain (`conformance_workloads/workloads/<wf>/transport/`)
or a **tool domain** (`snapshot_inspector/transport/`, namespace `inspection::`). A tool domain
declares capabilities *about* a snapshot rather than within one, and composes exactly like any
other. The engine reads the compiled contracts from the sealed snapshot. Adding an operation =
a new TI/TE pair + a binding line; **no engine change**.

## Normative invariants (from the Standard; enforced in this code)

- **OPERATION_IDENTITY_INDEPENDENCE** — an Operation Identity ≠ a Workflow Identity. The
  public name (`collatz.compute`) is stable; the bound WF is not, and may be re-pointed with
  no adapter change.
- **ADAPTER_NON_AUTHORIAL** — adapters translate protocol mechanics only; they determine no
  domain/business semantics.
- **RESULT_CLASS_PROTOCOL_INDEPENDENCE** — a Result Class carries no HTTP/RPC/CLI semantics.
- **RESPONSE_PROJECTION_EXTERNAL** — Result Class → HTTP status / exit code lives in the
  **adapter**, never in a TE.
- **TI_BOUNDARY_NOT_STAGE** — TI/TE are boundary contracts, not inline execution stages.
- **RB_NOT_TRANSPORT_ABSTRACTION** — the boundary is never expressed as a business `RB`.
- **TRANSPORT_PROTOCOL_INDEPENDENCE** — `contracts/` and `resolver/` never depend on a wire
  protocol.

## Configuration surface (env-provisioned; the adapter is POINTED at everything)

| Env | Meaning |
|---|---|
| `PGC_OPERATIONS_ROOTS` | colon-separated dirs holding `TI_`/`TE_` declarations |
| `PGC_STATIC_MOUNTS` | `prefix=dir;…` read-only static mounts (client, traces, snapshot) |
| `PGC_HTTP_BINDINGS` | path to the HTTP External Protocol Binding JSON (`{method,path}→operation`, or `operation_in_body` + `namespace`) |
| `PGC_RUNTIME_ROOT` | `protocol_runtime` repo root (provides the `runtime` package) |
| `PGC_INSPECTOR_ROOT` | `snapshot_inspector` repo root (provides the `inspector` package) |
| `PGC_IMPL_ROOTS` | domain CT/CS impl roots (loaded by `handler_ref` at execution) |
| `PGC_SNAPSHOT_ROOT` / `PGC_DATA_ROOT` | assembled snapshot (read-only) / instance root (traces, CS state) |
| `PGC_HTTP_PORT` | default 8000 |
| `PGC_HTTP_BIND` | listen address, default `127.0.0.1`; a node-group boundary sets its external address |
| `PGC_COORDINATOR_URL` | required only when the snapshot places execution on `FEDERATED_NODE` (read by the runtime) |

A concrete launcher supplies all of the above: each client's `client/serve.sh` (Collatz, the
inspector, blockchain). `run_http.sh` here is generic and validates the env.

## Import rules (MANDATORY)

- Absolute, fully-qualified from `pgc_transport.*`, `runtime.*`, or `inspector.*`.
- **Exactly two cross-repo imports are permitted, one per handler-kind interface:**
  `runtime.api.invoke_workflow` (execution) and `inspector.api.query` (inspection). Both are
  *interfaces*, not domains — each is a static entry point behind which that component
  dispatches its own identities. No `compiler.*`, no `structure.*`, no `pgs_*`, no domain
  imports. Adding a third interface means adding a handler kind, which is a Standard change.
- No relative imports (`.`/`..`). No `sys.path` manipulation (roots are env-provisioned).
- No dynamic imports / reflection / filesystem-based discovery.

## Fail-hard

No fallback, no silent success, no guessing missing config. **One documented carve-out:** the
resolver catches a runtime exception to classify it as the `EXECUTION_FAILURE` Result Class
(Standard §7 boundary error classification) — this is egress *projection*, not control-flow
fallback, and is the only permitted `try/except` in the engine.

## What the engine implements

- TI/TE are compiler-recognized `TRANSPORT_INGRESS`/`TRANSPORT_EGRESS` kinds, governed by
  `CONSTITUTION_TRANSPORT_{ENVELOPE,INGRESS,EGRESS}` and sealed into the snapshot. The engine reads
  the compiled boundary contracts from the snapshot. The transport invariants enforce boundary
  conformance at compile time.
- External Protocol Binding is **adapter-owned JSON** (Standard Patch 2). `XB_` artifactization
  deferred.
- **All three handler kinds are implemented.** `WF_INVOCATION` → `runtime.api.invoke_workflow`;
  `SNAPSHOT_READ` / `SNAPSHOT_QUERY` → `inspector.api.query`. The kind table is static and
  closed; a handler turns a declared payload into `(status, surface)` and the TE classifies and
  projects it, so all three share one path.
- **`operation_in_body` bindings are supported.** A route may carry a namespace rather than a
  fixed operation, so an operation FAMILY shares one route. The namespace is an ADMISSION
  CONSTRAINT the adapter checks textually; each identity still resolves against its own governed
  TI/TE pair. The adapter never branches on operation semantics.

## Workflow rules (MANDATORY)

Diagnose → plan → **get approval before multi-file changes**. Present the complete file list
first; one coherent change set, not scattered edits. Don't read/write code before fully
understanding the request.

## Environment

Do NOT `pip install` — dependencies are managed externally. The adapters are **stdlib-only**.

In the workspace this repo stays uninstalled: its roots are env-provisioned. It is published as
the `pgc-transport` distribution, whose console command is `pgc_transport` (`pgc_transport.adapters.cli.main`);
an install is how a user without the workspace reaches the boundary.

## One-line summary

Absolute `pgc_transport.*`/`runtime.*` imports, protocol-neutral canonical contracts, a
generic resolver, thin non-authorial adapters — **zero domain knowledge in the engine.**
transport knows *how* to transport; the domain declares *what* may be transported.
