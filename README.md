# pgs_transport

**Transport realization boundary for Protocol-Governed Systems.**

This repository defines how the outside world reaches the runtime — and how execution results leave it. All ingress and egress surfaces are declared here; none originate in application code.

> **New to PGS?** This is one of the repositories in the Protocol-Governed Systems ecosystem.
> For orientation, architecture overview, and end-to-end execution, start at [pgs_workspace](https://github.com/bachipeachy/pgs_workspace).

---

## What this repository contains

### `ingress/`

Ingress adapters — the surfaces through which external requests enter the governed execution environment.

| Path | Role |
|------|------|
| `registry/ingress_gateway/capability_contracts/` | CC declarations for HTTP request mapping and validation |
| `registry/ingress_gateway/runtime_bindings/` | RB declarations binding ingress CCs to concrete implementations |

### `egress/`

Egress adapters — the surfaces through which execution results leave the governed environment.

| Path | Role |
|------|------|
| `registry/egress_gateway/events/` | Event declarations emitted at egress boundary |

---

## Execution model

Every request through transport follows this path:

```
IN_ → WF_ → CC_ → (CT_ / CS_) → Trace
```

Transport concerns sit at the boundary of that path:

| Concern | What it does | Where declared |
|---------|-------------|----------------|
| `CC_` Capability Contract | Maps/validates HTTP requests; maps execution results to HTTP responses | `ingress/` |
| `EV_` Event | Emitted at egress boundary | `egress/` |
| `RB_` Runtime Binding | Connects transport CCs to their HTTP gateway implementation | `ingress/` |
| `CT_` / `CS_` | Pure transforms and side effects invoked by CCs | `pgs_capabilities` (external) |

Transport declares the boundary surfaces. All domain behavior runs through `pgs_runtime`.

---

## Build lifecycle

```
compile → build → run
```

| Phase | What happens | Where |
|-------|-------------|-------|
| **compile** | Source artifacts validated against invariants | `pgs_governance` / `pgs_compiler` |
| **build** | Validated artifacts materialized into a closed snapshot | `pgs_compiler` → `pgs_workspace/protocol_snapshot/` |
| **run** | Runtime reads snapshot and executes | `pgs_workspace` (pgs_runtime CLI) |

The snapshot is sealed at build time. No behavior enters at execution time that was not in the snapshot.

---

## Layer position

```
external world
    ↓
pgs_transport       ←  THIS REPO: ingress/egress boundary declarations
    ↓
pgs_runtime         →  executes governed workflows
    ↓
pgs_transport       ←  egress: results returned to caller
```

---

## Part of the PGS ecosystem

| Repo | Role |
|------|------|
| `pgs_workspace` | Entry point — snapshot + scripts |
| `pgs_runtime` | Execution engine (pgs_runtime CLI) |
| `pgs_governance` | Constitutional rules + structure definitions |
| `pgs_compiler` | Compiler pipeline + tooling |
| `pgs_transport` | **This repo** — ingress/egress adapters |
| `pgs_capabilities` | CT/CS implementations |
| `pgs_blockchain` | Blockchain domain |
| `pgs_ai_governance` | AI governance domain |
| `pgs_change_mgmt` | Governed SDLC — Change Request to Authoring Mandate (new in v0.5.0) |
