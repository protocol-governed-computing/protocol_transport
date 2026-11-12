"""The Canonical Transport Request — protocol-neutral, so every adapter builds it the same way.

An adapter translates its protocol's mechanics into a bound operation and a canonical input. This
module turns that pair into the request the resolver reads. It knows no protocol.
"""
from __future__ import annotations

import uuid
from typing import Any


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
