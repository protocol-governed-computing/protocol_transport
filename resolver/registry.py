"""Registry — loads hand-authored TI/TE boundary declarations, keyed by Operation Identity.

CUT-#1 DEVIATION (deliberate, scoped): the boundary declarations are read from
hand-authored `.md` artifacts at process start, not from a compiled snapshot. Phase 3
promotes these to compiler-recognized `TI_`/`TE_` kinds in the sealed snapshot. Until
then this is the single, declared place that materializes them.

DOMAIN NEUTRALITY: this module knows nothing about any workload. It is *pointed at*
roots (it does not discover domains by convention) and loads whatever TI/TE declarations
live there. No operation name, workload path, or field name is hard-coded here.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_YAML_BLOCK = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


class OperationContract:
    """The TI + TE declaration pair for one Operation Identity."""

    __slots__ = ("operation", "ti", "te")

    def __init__(self, operation: str, ti: dict[str, Any], te: dict[str, Any]) -> None:
        self.operation = operation
        self.ti = ti
        self.te = te


def _machine_block(md_path: Path) -> dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    match = _YAML_BLOCK.search(text)
    if match is None:
        raise ValueError(f"no ```yaml machine block in {md_path}")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"machine block in {md_path} is not a mapping")
    return data


def load_registry(roots: list[Path]) -> dict[str, OperationContract]:
    """Load every TI/TE pair found under the given roots, keyed by Operation Identity.

    Structure convention (declarations, not semantics): each `TI_*.md` has a sibling
    `TE_*.md` in the same directory declaring the same `operation`.

    Fails hard on: missing sibling TE, TI/TE operation mismatch, duplicate operation.
    """
    registry: dict[str, OperationContract] = {}
    for root in roots:
        for ti_path in sorted(root.rglob("TI_*.md")):
            te_candidates = sorted(ti_path.parent.glob("TE_*.md"))
            if len(te_candidates) != 1:
                raise ValueError(
                    f"{ti_path.parent} must contain exactly one TE_*.md beside {ti_path.name}"
                )
            ti = _machine_block(ti_path)
            te = _machine_block(te_candidates[0])
            operation = ti.get("operation")
            if not operation:
                raise ValueError(f"TI has no operation identity: {ti_path}")
            if te.get("operation") != operation:
                raise ValueError(
                    f"TE operation {te.get('operation')!r} != TI operation {operation!r} "
                    f"in {ti_path.parent}"
                )
            if operation in registry:
                raise ValueError(f"duplicate operation identity: {operation!r}")
            registry[operation] = OperationContract(operation, ti, te)
    return registry