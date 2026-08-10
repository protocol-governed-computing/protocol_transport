# Architecture — `protocol_transport`

**Release 5.** This document is frozen for this release. It describes what this repository is, what
it owns, and what it must never do. It is written to be read before any code, and assumes no prior
familiarity with Protocol-Governed Computing.

For the big picture — what PGC is and how the repositories compose — see
**https://github.com/protocol-governed-computing**.

---

## 1. What this repo is

This is the **boundary** between the outside world and a governed execution universe. It turns an
arriving HTTP request into a governed invocation, and turns the result back into a reply.

The unusual thing about it is what it does *not* contain:

> This repository knows **how** to transport. It declares nothing about **what** may be transported.

Every fact that is specific to a business — which routes exist, what an operation is called, which
workflow it runs, what fields the caller may send, what a failure means — arrives as **data the
engine is pointed at**. None of it is written here.

**What this repo is not.** It is not a web framework, an API gateway with rules in it, or a place
where an endpoint's behaviour is implemented. Adding a new operation to a running system requires
**no change to any file in this repository**.

## 2. Where it sits

```
   external world     browser · script · CLI · another service
          │
          │  HTTP (or, later, another wire protocol)
          ▼
   ┌──────────────────────────────────────────────────┐
   │  protocol_transport        ← YOU ARE HERE        │
   │                                                  │
   │   adapters/   wire mechanics only                │
   │   resolver/   operation → contract → handler     │
   │   contracts/  protocol-neutral request/response  │
   └───────┬──────────────────────────────┬───────────┘
           │                              │
           ▼                              ▼
   protocol_runtime               snapshot_inspector
   (executes a workflow)          (answers about a snapshot)
```

The boundary declarations themselves — which operations exist and what each admits — live **outside
this repo**, with the domain that owns them, and are compiled and sealed into the snapshot. The
engine reads them from there.

## 3. The central idea: an operation is not a workflow

The distinction that explains every design choice in this repository:

```
   THE USUAL ARRANGEMENT                 THIS BOUNDARY

   a route names a handler               a route names an OPERATION IDENTITY
   POST /compute → computeHandler()          POST /api/run → collatz.compute
        │                                         │
        │  renaming the internals                 │  the public name is stable;
        │  breaks every caller                    │  the bound workflow is not
        ▼                                         ▼
   the outside world depends on          the outside world depends on a
   how the inside is built               governed name, and nothing else
```

`collatz.compute` is a promise made to callers. Which workflow serves it is an internal decision
that may be re-pointed at any time — a different workflow, a different version, a different domain
layout — **with no adapter change and no caller change**. The two identities are deliberately
independent, and keeping them independent is the whole reason this layer exists.

Between the two sits a matched pair of governed contracts:

| | contract | what it decides |
|---|---|---|
| **TI** | Transport **Ingress** | may this call in at all, and what does it carry? |
| **TE** | Transport **Egress** | what happened, and what class of result is that? |

Both are declared by the domain, compiled, and sealed. Neither lives in this repository.

## 4. What it owns, and what it must never do

**It owns:**

- **canonical objects** — one protocol-neutral request shape and one response shape, so that what
  crosses the boundary is the same regardless of the wire it arrived on;
- **resolution** — turning an operation identity into its declared TI, a handler, and its TE;
- **wire mechanics** — parsing an HTTP request, serving static files, writing a status code back;
- **response projection** — mapping a governed result class onto whatever the wire uses to say it.

**It must never:**

- **know a domain.** No workload name, no operation name, no field name, no route literal appears in
  `resolver/` or `adapters/`.
- **author meaning.** An adapter translates mechanics. It never decides whether a call is allowed,
  what it means, or whether it succeeded.
- **carry a wire assumption inward.** `contracts/` and `resolver/` contain nothing about HTTP. A
  result class has no status code in it.
- **fall back.** Missing configuration, an unknown operation, an unsupported handler kind — each is
  a refusal, never a default.

### The acid test

This is a claim the reader can execute, and it is the point of the repository:

```bash
grep -rniE 'collatz|number|steps|/api/' resolver/ adapters/
```

**It returns nothing.** If it ever returns something, this layer has stopped being a boundary and
has started being an application.

## 5. How one call proceeds

```
   HTTP request
        │
        ▼
   ┌─ adapter ─────────────────────────────────────────────────┐
   │  binding table (DATA):  method + path  →  operation        │
   │  or: route carries a NAMESPACE, operation named in body    │
   └────────────────────────┬──────────────────────────────────-┘
                            ▼
                   Canonical Transport Request
                            │
   ┌─ resolver ─────────────▼──────────────────────────────────┐
   │  TI   admit or refuse; extract the declared payload        │
   │   │                                                        │
   │   ▼                                                        │
   │  handler   one of exactly three kinds (closed table)        │
   │      WF_INVOCATION  → runtime executes a workflow           │
   │      SNAPSHOT_READ  → inspector projects sealed material    │
   │      SNAPSHOT_QUERY → inspector derives an answer           │
   │   │                                                        │
   │   ▼                                                        │
   │  TE   classify the outcome into a governed Result Class     │
   └────────────────────────┬──────────────────────────────────-┘
                            ▼
                  Canonical Transport Response
              { outcome · result_class · result · evidence · errors }
                            │
   ┌─ adapter ──────────────▼──────────────────────────────────┐
   │  projection:  Result Class → HTTP status                   │
   └───────────────────────────────────────────────────────────┘
```

Two details carry most of the weight.

**The binding table is data.** Routes are a JSON file the adapter is pointed at, not code. A route
may also carry a *namespace* rather than a single operation, so a whole family of operations shares
one route — the namespace is then an admission constraint the adapter checks **textually**, and each
identity still resolves against its own governed TI/TE pair. The adapter never branches on what an
operation means.

**The handler table is closed.** Three kinds, statically listed. Each turns a declared payload into a
status and a surface; the TE then classifies and projects it, so all three share one path. A fourth
kind is not a code change — it is a change to the standard this repository implements.

## 6. Result classes

The response carries one of five governed classes. They are protocol-neutral by construction:

| class | meaning |
|---|---|
| `SUCCESS` | the operation ran and conformed |
| `VIOLATION` | a rule refused it |
| `UNAUTHORIZED` | the caller was not entitled to it |
| `EXECUTION_FAILURE` | it was admitted and could not complete |
| `NOT_FOUND` | no such operation identity |

A result class contains no HTTP status, no exit code, and no wire vocabulary. Mapping it onto one is
the adapter's job and happens at the very last moment — which is what makes a second wire protocol
an additive change rather than a rewrite.

## 7. Layout

```
contracts/            the canonical request and response objects — no protocol in them
resolver/
    registry.py       operation identity → its compiled TI/TE pair
    resolver.py       the generic path: TI → handler → TE
adapters/
    http/
        binding.py    the External Protocol Binding: routes as data
        server.py     HTTP mechanics, static mounts, response projection
doc/                  the transport standard this engine implements
run_http.sh           a launcher that names no workload
```

The whole engine is under 700 lines. That is not an accident of scale — a boundary that grows is a
boundary that has begun to hold opinions.

## 8. Rules this repo enforces

1. **An operation identity is not a workflow identity.** The public name is stable; the binding
   behind it is re-pointable with no adapter change.
2. **An adapter is non-authorial.** It translates mechanics and determines no domain meaning.
3. **A result class carries no protocol semantics**, and the mapping to a status code lives only in
   the adapter.
4. **TI and TE are boundary contracts, not execution stages.** They are not steps inside a workflow.
5. **`contracts/` and `resolver/` never depend on a wire protocol.**
6. **The engine holds zero domain knowledge** — the grep in section 4 is the test.
7. **Exactly two cross-repo imports are permitted**, one per handler-kind interface: the runtime's
   execution entry point and the inspector's query entry point. Both are interfaces, not domains.
8. **No fallback.** One documented exception exists: a runtime exception is caught in order to
   *classify* it as `EXECUTION_FAILURE`. That is egress projection, not control flow.

## 9. How to know it works

Run the acid test in section 4 — it is the fastest and most meaningful check in the repository.

Then serve a composition and call it:

```bash
./run_http.sh          # requires the environment to point it at roots; it names no workload
```

A good result looks like this: the same engine, unchanged, serves a business workload and an
inspection surface at once; adding an operation touches a contract pair and a line of binding data;
and a bad request comes back refused with a governed result class rather than a stack trace.

## 10. Where the architecture is explained

This document describes *this repository*. The architecture it realizes is developed in the papers
indexed at **https://github.com/protocol-governed-computing**:

- **An Architecture for Deterministic Declarative Execution** — the execution partition this
  boundary opens onto, and why the thing on the other side decides nothing.
- **Realizing the Normative Platform and Its Governed Transformation** — what it takes for a governed
  platform to *answer* to the outside world, and the conditions a boundary must meet to do so.
- **A Conceptual Model** — the snapshot as the immutable admissibility boundary, and the evidence
  model the canonical response carries forward.
