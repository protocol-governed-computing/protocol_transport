"""External Protocol Binding (HTTP) — adapter-owned config, NOT a PGC artifact (Patch 2).

The binding is **data**: a table of entries loaded from a JSON file the adapter is pointed at.
It maps an HTTP protocol selector (method + route) to an Operation Identity. It is deliberately
*not* imperative routing logic, so it can later be promoted to a governed `XB_` artifact with no
change to the transport engine.

Two entry forms coexist, both governed — an operation resolves only if a matching TI/TE pair is
registered in the snapshot:

    fixed operation      {"method", "path", "operation"}
    operation in body    {"method", "path", "operation_in_body": true, "namespace": "…"}

The second form exists because a catalog of many sibling identities would otherwise need one
route each. **The namespace is an ADMISSION CONSTRAINT, not a dispatcher.** The adapter checks
that the submitted identity falls inside the declared namespace and does nothing else with it:
the value is passed through as an Operation Identity and resolved through the same governed
registry as a fixed operation, against its own TI/TE pair. Branching on operation semantics here
is forbidden (`ADAPTER_NON_AUTHORIAL`) — that would make the adapter an RPC router.

This module contains no workload knowledge — the concrete routes, operations and namespaces live
entirely in the JSON data file.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, NamedTuple


class Binding(NamedTuple):
    """One bound route. Exactly one of `operation` / `namespace` is meaningful."""

    operation: str | None       # fixed form: the identity this route always carries
    namespace: str | None       # in-body form: the namespace an identity must fall inside


class AdmissionError(ValueError):
    """The submitted identity is absent or outside the namespace this route admits."""


def load_bindings(path: Path) -> dict[tuple[str, str], Binding]:
    """Load the HTTP binding table → {(METHOD, path): Binding}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    table: dict[tuple[str, str], Binding] = {}
    for entry in data.get("bindings", []):
        key = (entry["method"].upper(), entry["path"])
        if key in table:
            raise ValueError(f"duplicate HTTP binding for {key}")
        if entry.get("operation_in_body"):
            namespace = entry.get("namespace")
            if not namespace:
                raise ValueError(f"binding {key} declares operation_in_body without a namespace")
            table[key] = Binding(operation=None, namespace=namespace)
        else:
            table[key] = Binding(operation=entry["operation"], namespace=None)
    return table


def select_operation(binding: Binding, body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Determine (Operation Identity, canonical input) for a bound route.

    Fixed form: the route carries the identity and the whole body IS the input.
    In-body form: the body carries `operation` plus its `params`, and the identity is admitted
    iff it falls inside the route's declared namespace. The check is textual containment — the
    adapter neither knows nor asks what the identity means.
    """
    if binding.operation is not None:
        return binding.operation, body

    operation = body.get("operation")
    if not isinstance(operation, str) or not operation:
        raise AdmissionError("request body declares no operation identity")
    if not operation.startswith(binding.namespace or ""):
        raise AdmissionError(
            f"operation '{operation}' is outside the namespace "
            f"'{binding.namespace}' admitted by this route"
        )
    params = body.get("params")
    return operation, params if isinstance(params, dict) else {}


def to_canonical_request(operation: str, canonical_input: dict[str, Any]) -> dict[str, Any]:
    """Translate (bound operation, canonical input) → Canonical Transport Request.

    Reserved AC/idempotency slots are structural only (no V0 semantics)."""
    request_id = str(uuid.uuid4())
    return {
        "request_id": request_id,
        "operation": operation,
        "actor": {},                      # reserved (AC) — not interpreted in V0
        "context": {},                    # reserved (AC) — not interpreted in V0
        "input": canonical_input,
        "correlation_id": request_id,     # reserved + propagated in V0
        "idempotency_key": None,          # reserved, not enforced in V0
        "metadata": {},
    }
