"""External Protocol Binding (HTTP) — adapter-owned config, NOT a PGC artifact (Patch 2).

The binding is **data**: a table of `{method, path, operation}` entries loaded from a JSON
file the adapter is pointed at. It maps an HTTP protocol selector (method + route) to an
Operation Identity. It is deliberately *not* imperative routing logic, so it can later be
promoted to a governed `XB_` artifact with no change to the transport engine.

This module contains no workload knowledge — the concrete routes/operations live entirely
in the JSON data file (`ADAPTER_NON_AUTHORIAL`).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


def load_bindings(path: Path) -> dict[tuple[str, str], str]:
    """Load the HTTP binding table → {(METHOD, path): operation}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    table: dict[tuple[str, str], str] = {}
    for entry in data.get("bindings", []):
        key = (entry["method"].upper(), entry["path"])
        if key in table:
            raise ValueError(f"duplicate HTTP binding for {key}")
        table[key] = entry["operation"]
    return table


def to_canonical_request(operation: str, body: dict[str, Any]) -> dict[str, Any]:
    """Translate (bound operation, HTTP JSON body) → Canonical Transport Request.

    For a route-bound endpoint the JSON body IS the operation input. Reserved AC/idempotency
    slots are structural only (no V0 semantics)."""
    request_id = str(uuid.uuid4())
    return {
        "request_id": request_id,
        "operation": operation,
        "actor": {},                      # reserved (AC) — not interpreted in V0
        "context": {},                    # reserved (AC) — not interpreted in V0
        "input": body,
        "correlation_id": request_id,     # reserved + propagated in V0
        "idempotency_key": None,          # reserved, not enforced in V0
        "metadata": {},
    }
