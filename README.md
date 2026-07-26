# transport

**The PGC transport boundary engine** — a domain-neutral, protocol-neutral governed
boundary between external interaction protocols (HTTP, RPC, CLI) and a PGC execution
universe.

It knows *how* to transport. It declares nothing about *what* is transported: every route,
operation, and workflow binding arrives as configuration the engine is **pointed at**, never
hardcoded. The domain/platform declares what may be transported.

> **Semantic authority:** [`doc/TRANSPORT_STANDARD_V0.md`](doc/TRANSPORT_STANDARD_V0.md)
> (Phase-1 frozen). Read it first. For working in this repo, see
> [`CLAUDE.md`](CLAUDE.md).

---

## The invariant

> Many external protocols may bind to one **Operation Identity**; one Operation Identity
> resolves to one governed PGC invocation contract; the external protocol is replaceable,
> while the governed interaction remains stable.

```
HTTP / RPC / CLI
      │            (external protocol)
      ▼
  Protocol Adapter        ─ translates wire ↔ Canonical Transport Request/Response (owns no domain meaning)
      ▼
  Operation Identity      ─ stable public name (e.g. collatz.compute); NEVER a workflow id
      ▼
  TI  → handler → TE      ─ ingress contract → invocation → egress classification
      ▼
  Canonical Response      ─ protocol-neutral { outcome, result_class, result, evidence, errors }
      ▼
  Response Projection     ─ adapter maps Result Class → HTTP status / RPC error / CLI exit
```

`TI`/`TE` and the workflows they bind to are **domain-governed and live outside this repo**
(in the platform/domain surface). This repo is only the engine.

---

## Layout

| Path | Role |
|------|------|
| `contracts/` | Canonical, protocol-neutral interop objects — `TRANSPORT_REQUEST_V0`, `TRANSPORT_RESPONSE_V0` |
| `resolver/` | The generic resolution engine: `operation → TI → handler → TE → Canonical Response`. Zero domain knowledge. |
| `adapters/http/` | HTTP mechanics: static mounts, the External Protocol Binding table (data), Response Projection |
| `doc/` | `TRANSPORT_STANDARD_V0.md` — the frozen semantic model |
| `run_http.sh` | Domain-neutral launcher (env-provisioned; names no workload) |

---

## The acid test

The engine holds **no domain knowledge**. Grep `resolver/` and `adapters/` for any workload
or field name (`collatz`, `number`, `steps`, a route literal) and you find nothing. Everything
domain-specific is data the engine is pointed at:

- **operations** (`TI`/`TE` declarations) via `PGC_OPERATIONS_ROOTS`
- **routes → operations** via the External Protocol Binding JSON (`PGC_HTTP_BINDINGS`)
- **static content** via `PGC_STATIC_MOUNTS`

Adding an operation is additive — a new `TI`/`TE` pair plus a binding line — with **no engine
change**.

---

## Running

`run_http.sh` is generic and requires the environment to point it at roots. A concrete
composition (the platform reference surface) lives at
`platform/reference_surface/serve.sh`, which supplies every `PGC_*` variable and execs this
launcher:

```bash
./platform/reference_surface/serve.sh      # serves the reference surface on :8000
```

See [`CLAUDE.md`](CLAUDE.md) for the full configuration surface and architectural rules.

---

## Layer position

```
external world  →  transport (adapter → resolver)  →  runtime (executes)  →  transport (TE → adapter)  →  external world
```

The engine's only cross-repo dependency is the runtime **execution interface**
(`runtime.api.run_workflow`) — it never imports the compiler, protocol, or any domain.
