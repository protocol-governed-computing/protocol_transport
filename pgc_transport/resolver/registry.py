"""Registry — loads compiled TI/TE boundary declarations from the sealed snapshot,
keyed by Operation Identity.

Phase 3: the boundary declarations are read from the **compiled snapshot** (canonical
`artifact_type: TI`/`TE` artifacts), not from hand-authored `.md`. The compiler recognizes
the `TI_`/`TE_` kinds and seals them; this module materializes them from that snapshot.

DOMAIN NEUTRALITY: this module knows nothing about any workload. It is *pointed at* a
snapshot root; it loads whatever TI/TE artifacts the snapshot contains and pairs them by
the `operation` each declares. No operation name, workload path, or field name is
hard-coded here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OperationContract:
    """The TI + TE declaration pair for one Operation Identity."""

    __slots__ = ("operation", "ti", "te")

    def __init__(self, operation: str, ti: dict[str, Any], te: dict[str, Any]) -> None:
        self.operation = operation
        self.ti = ti
        self.te = te


def load_registry(snapshot_root: Path) -> dict[str, OperationContract]:
    """Load every compiled TI/TE pair from the sealed snapshot, keyed by Operation Identity.

    Reads the compiled canonical artifacts (`artifact_type` TI/TE), takes each artifact's
    `frontmatter` (the declared boundary contract), and pairs TI with TE by the `operation`
    each declares.

    Fails hard on: a transport artifact with no `operation`, a duplicate operation for the
    same side, or a TI/TE without a matching counterpart in the snapshot.
    """
    canonical = snapshot_root / "canonical"
    if not canonical.is_dir():
        raise ValueError(f"snapshot canonical dir not found: {canonical}")

    ti_by_op: dict[str, dict[str, Any]] = {}
    te_by_op: dict[str, dict[str, Any]] = {}
    for jf in sorted(canonical.rglob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        side = data.get("artifact_type")
        if side not in ("TI", "TE"):
            continue
        fm = data.get("frontmatter", {}) or {}
        operation = fm.get("operation")
        if not operation:
            raise ValueError(f"transport artifact has no operation identity: {jf}")
        target = ti_by_op if side == "TI" else te_by_op
        if operation in target:
            raise ValueError(f"duplicate {side} operation identity: {operation!r}")
        target[operation] = fm

    registry: dict[str, OperationContract] = {}
    for operation, ti in ti_by_op.items():
        te = te_by_op.get(operation)
        if te is None:
            raise ValueError(f"TI operation {operation!r} has no matching TE in the snapshot")
        registry[operation] = OperationContract(operation, ti, te)
    for operation in te_by_op:
        if operation not in ti_by_op:
            raise ValueError(f"TE operation {operation!r} has no matching TI in the snapshot")
    return registry
