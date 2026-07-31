"""Resolver — the governed transport boundary path (protocol-neutral, domain-neutral).

Given a Canonical Transport Request it resolves the Operation Identity through its TI to
a handler, invokes the handler, then classifies + projects the result through its TE into
a Canonical Transport Response.

This module contains ZERO operation-specific logic. Every operation-specific fact — the
bound WF, the input mapping, the result classification, the output projection — is
*declared* in the TI/TE artifacts and interpreted generically here. Adding an operation
(e.g. `si.query`) is additive: a new TI/TE pair, no change to this module. It also knows
no wire protocol: HTTP/RPC/CLI never appear here (`TRANSPORT_PROTOCOL_INDEPENDENCE`).
"""
from __future__ import annotations

import re
from typing import Any

from runtime.api import run_workflow

from resolver.registry import OperationContract

_SUCCESS = "SUCCESS"
_INPUT_TOKEN = re.compile(r"^\$\{input\.(\w+)\}$")

# Generic value-derivation operators referenced by a TE output_contract `op`.
_DERIVE = {
    "identity": lambda v: v,
    "length": len,
    "length_minus_one": lambda v: len(v) - 1,
    "max": max,
    "min": min,
}


def _substitute(template: Any, canonical_input: dict[str, Any]) -> Any:
    """Build a handler payload from a TI payload_template via ${input.KEY} substitution."""
    if isinstance(template, dict):
        return {k: _substitute(v, canonical_input) for k, v in template.items()}
    if isinstance(template, list):
        return [_substitute(v, canonical_input) for v in template]
    if isinstance(template, str):
        match = _INPUT_TOKEN.match(template)
        if match is not None:
            return canonical_input[match.group(1)]  # KeyError -> fail hard (declared field absent)
    return template


def _resolve_path(path: str, ctx: dict[str, Any]) -> Any:
    """Resolve a dotted path over {input, surface}. A `$key` segment substitutes
    str(input[key]) as the lookup key (e.g. `surface.items.$id` -> surface.items["<id-value>"])."""
    node: Any = ctx
    for seg in path.split("."):
        if seg.startswith("$"):
            seg = str(ctx["input"][seg[1:]])
        node = node[seg]
    return node


def _validate_input(canonical_input: dict[str, Any], input_contract: dict[str, Any]) -> list[dict]:
    """Return a list of error dicts (empty = valid). Generic over the declared contract."""
    errors: list[dict] = []
    for field, spec in input_contract.items():
        if field not in canonical_input:
            if spec.get("required", False):
                errors.append({"code": "INPUT_MISSING", "message": f"missing required input '{field}'"})
            continue
        value = canonical_input[field]
        if spec.get("type") == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append({"code": "INPUT_TYPE", "message": f"'{field}' must be an integer"})
            continue
        if "min" in spec and value < spec["min"]:
            errors.append({"code": "INPUT_OUT_OF_RANGE", "message": f"'{field}' below minimum {spec['min']}"})
        if "max" in spec and value > spec["max"]:
            errors.append({"code": "INPUT_OUT_OF_RANGE", "message": f"'{field}' above maximum {spec['max']}"})
    return errors


def _response(request_id: str, result_class: str, *, result: Any = None,
              evidence: list | None = None, errors: list | None = None) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "outcome": "SUCCESS" if result_class == _SUCCESS else "FAILURE",
        "result_class": result_class,
        "result": result,
        "evidence": evidence or [],
        "errors": errors or [],
    }


def resolve(request: dict[str, Any], registry: dict[str, OperationContract], *,
            data_root: str, snapshot_root: str | None) -> dict[str, Any]:
    """Resolve a Canonical Transport Request → Canonical Transport Response."""
    request_id = request.get("request_id") or ""
    operation = request.get("operation")
    canonical_input = request.get("input") or {}

    contract = registry.get(operation)
    if contract is None:
        return _response(request_id, "NOT_FOUND",
                         errors=[{"code": "OPERATION_NOT_FOUND", "message": f"unknown operation '{operation}'"}])

    ti = contract.ti
    input_errors = _validate_input(canonical_input, ti.get("input_contract", {}))
    if input_errors:
        return _response(request_id, "VIOLATION", errors=input_errors)

    handler = ti["handler"]
    kind = handler.get("kind")
    if kind != "WF_INVOCATION":
        # Only WF_INVOCATION is implemented in cut #1; SNAPSHOT_QUERY (si.query) is cut #2.
        return _response(request_id, "EXECUTION_FAILURE",
                         errors=[{"code": "HANDLER_KIND_UNSUPPORTED", "message": f"handler kind '{kind}' not implemented"}])

    payload = _substitute(handler.get("payload_template", {}), canonical_input)

    # Boundary error classification (Transport Standard V0 §7): a runtime raise is
    # projected as the EXECUTION_FAILURE Result Class, never leaked as a stack trace.
    # This is egress result classification, not control-flow fallback.
    try:
        run = run_workflow(wf_fqdn=handler["workflow"], payload=payload,
                           data_root=data_root, snapshot_root=snapshot_root)
    except Exception as exc:  # noqa: BLE001 — boundary classification, re-projected below
        return _response(request_id, "EXECUTION_FAILURE",
                         errors=[{"code": "EXECUTION_FAILURE", "message": str(exc)}])

    te = contract.te
    result_class = te.get("result_classification", {}).get(
        run.status, te.get("default_result_class", "EXECUTION_FAILURE"))

    if result_class != _SUCCESS:
        return _response(request_id, result_class,
                         errors=[{"code": result_class, "message": f"workflow status {run.status}"}])

    ctx = {"input": canonical_input, "surface": run.surface}
    result: dict[str, Any] = {}
    for spec in te.get("output_contract", []):
        value = _resolve_path(spec["from"], ctx)
        result[spec["field"]] = _DERIVE[spec.get("op", "identity")](value)

    evidence: list[str] = []
    if te.get("evidence_policy") == "reference_only":
        # Resolvable, protocol-neutral reference: the trace path relative to the instance data
        # root, derived from the runtime's OWN trace_dir (no trace layout hard-coded here). An
        # adapter that mounts the data root can turn this into a link; others treat it as an
        # opaque reference. Falls back to the bare trace id if the path can't be relativized.
        if run.trace_dir.is_relative_to(data_root):
            rel = run.trace_dir.relative_to(data_root)      # e.g. traces/<domain>/<wf>/<id>
            ref = f"{rel.as_posix()}/{run.trace_id}.jsonl"
        else:
            ref = run.trace_id
        evidence = [f"trace:{ref}"]

    return _response(request_id, _SUCCESS, result=result, evidence=evidence)
