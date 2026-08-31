"""Resolver — the governed transport boundary path (protocol-neutral, domain-neutral).

Given a Canonical Transport Request it resolves the Operation Identity through its TI to
a handler, invokes the handler, then classifies + projects the result through its TE into
a Canonical Transport Response.

This module contains ZERO operation-specific logic. Every operation-specific fact — the
bound WF or inspection operation, the input mapping, the result classification, the output
projection — is *declared* in the TI/TE artifacts and interpreted generically here. Adding
an operation is additive: a new TI/TE pair, no change to this module. It also knows no wire
protocol: HTTP/RPC/CLI never appear here (`TRANSPORT_PROTOCOL_INDEPENDENCE`).

**Three handler kinds, one shape.** A handler is anything that turns a declared payload into
`(status, surface)`; the TE then classifies that status and projects that surface. Execution
and inspection differ only in which static entry point the KIND selects:

    WF_INVOCATION    runtime.api.run_workflow    execute a governed workflow
    SNAPSHOT_READ    inspector.api.query         project PUBLISHED snapshot material
    SNAPSHOT_QUERY   inspector.api.query         DERIVE a result over snapshot state

The engine routes by kind to a static entry point and stops there — the inspector dispatches
its own Operation Identity internally. The resolver never interprets an operation string;
`if operation == …` in this module would make it an RPC router (Plan §3 rules 2 and 4).

The READ/QUERY distinction is preserved at the boundary even though both reach the same entry
point: they are different governed identities with different TI/TE, and a boundary that
collapsed them would lose the ability to admit published reads while refusing derived queries.
"""
from __future__ import annotations

import re
from typing import Any, Callable, NamedTuple

from inspector.api import query as inspect_query
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


class _Omit:
    """An optional declared input the caller did not supply: the slot is dropped, not defaulted."""

    def __repr__(self) -> str:  # pragma: no cover — diagnostics only
        return "<omit>"


_OMIT = _Omit()


def _substitute(template: Any, canonical_input: dict[str, Any],
                input_contract: dict[str, Any]) -> Any:
    """Build a handler payload from a TI payload_template via ${input.KEY} substitution.

    Three cases, and the distinction between them is load-bearing:

      * supplied         → the value substitutes, type-preserving.
      * declared but not supplied → the slot is OMITTED from the payload. It can only be an
        optional field, because a missing required one already failed `_validate_input` before
        this point. The resolver invents no default: what an absent optional means belongs to
        the handler that declared it, not to the boundary that forwards it.
      * not declared at all → fail hard. A template naming a field its own input_contract does
        not declare is an authoring error, and silently forwarding nothing would hide it.
    """
    if isinstance(template, dict):
        rendered = {k: _substitute(v, canonical_input, input_contract) for k, v in template.items()}
        return {k: v for k, v in rendered.items() if v is not _OMIT}
    if isinstance(template, list):
        rendered_list = [_substitute(v, canonical_input, input_contract) for v in template]
        return [v for v in rendered_list if v is not _OMIT]
    if isinstance(template, str):
        match = _INPUT_TOKEN.match(template)
        if match is not None:
            key = match.group(1)
            if key in canonical_input:
                return canonical_input[key]
            if key in input_contract:
                return _OMIT
            raise KeyError(
                f"payload_template references '{key}', which this TI's input_contract "
                "does not declare"
            )
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
        declared_type = spec.get("type")
        if declared_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append({"code": "INPUT_TYPE", "message": f"'{field}' must be an integer"})
            continue
        # A declared type that goes unchecked is a contract the boundary does not actually
        # enforce, so every type the contract may declare is checked here.
        if declared_type == "string" and not isinstance(value, str):
            errors.append({"code": "INPUT_TYPE", "message": f"'{field}' must be a string"})
            continue
        if declared_type == "boolean" and not isinstance(value, bool):
            errors.append({"code": "INPUT_TYPE", "message": f"'{field}' must be a boolean"})
            continue
        if "min" in spec and value < spec["min"]:
            errors.append({"code": "INPUT_OUT_OF_RANGE", "message": f"'{field}' below minimum {spec['min']}"})
        if "max" in spec and value > spec["max"]:
            errors.append({"code": "INPUT_OUT_OF_RANGE", "message": f"'{field}' above maximum {spec['max']}"})
    return errors


class Outcome(NamedTuple):
    """What every handler kind returns: a terminal status and the surface it exposes.

    `evidence_ref` is the handler's own resolvable reference to its evidence, or None when the
    kind produces none. An inspection read has no trace: it executed nothing.
    """

    status: str
    surface: Any
    evidence_ref: str | None


def _invoke_workflow(handler: dict[str, Any], payload: dict[str, Any], *,
                     data_root: str, snapshot_root: str | None) -> Outcome:
    run = run_workflow(wf_fqdn=handler["workflow"], payload=payload,
                       data_root=data_root, snapshot_root=snapshot_root)
    ref: str | None = None
    # Resolvable, protocol-neutral reference: the trace path relative to the instance data
    # root, derived from the runtime's OWN trace_dir (no trace layout hard-coded here). An
    # adapter that mounts the data root can turn this into a link; others treat it as an
    # opaque reference. Falls back to the bare trace id if the path can't be relativized.
    if run.trace_dir.is_relative_to(data_root):
        rel = run.trace_dir.relative_to(data_root)      # e.g. traces/<domain>/<wf>/<id>
        ref = f"{rel.as_posix()}/{run.trace_id}.jsonl"
    else:
        ref = run.trace_id
    return Outcome(run.status, run.surface, ref)


def _inspect(handler: dict[str, Any], payload: dict[str, Any], *,
             data_root: str, snapshot_root: str | None) -> Outcome:
    """Route to the inspector's static entry point; it resolves its own Operation Identity.

    The handler declares WHICH inspection identity to ask (`handler.operation`), the TI declares
    how canonical input becomes its params, and the inspector alone decides how to answer it.
    Inspection never executes, so it yields no evidence reference.
    """
    if snapshot_root is None:
        raise ValueError("snapshot inspection requires a snapshot root")
    status, surface = inspect_query(handler["operation"], payload, snapshot_root)
    return Outcome(status, surface, None)


# Static kind → entry point table. Declared, closed, and resolved by lookup: an unknown kind
# fails rather than falling back (`fail-hard`), and no kind is discovered at runtime.
_HANDLER_KINDS: dict[str, Callable[..., Outcome]] = {
    "WF_INVOCATION": _invoke_workflow,
    "SNAPSHOT_READ": _inspect,
    "SNAPSHOT_QUERY": _inspect,
}


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
        # OPERATION_NOT_FOUND, not NOT_FOUND: the identity resolves to no registered TI/TE, so
        # the boundary could not admit the request at all. NOT_FOUND means an ADMITTED request
        # whose subject is absent (CONSTITUTION_TRANSPORT_EGRESS_V0) — conflating them tells a
        # caller their query found nothing when in fact it was never asked.
        return _response(request_id, "OPERATION_NOT_FOUND",
                         errors=[{"code": "OPERATION_NOT_FOUND", "message": f"unknown operation '{operation}'"}])

    ti = contract.ti
    input_contract = ti.get("input_contract") or {}
    input_errors = _validate_input(canonical_input, input_contract)
    if input_errors:
        return _response(request_id, "VIOLATION", errors=input_errors)

    handler = ti["handler"]
    kind = handler.get("kind")
    invoke = _HANDLER_KINDS.get(kind)
    if invoke is None:
        return _response(request_id, "EXECUTION_FAILURE",
                         errors=[{"code": "HANDLER_KIND_UNSUPPORTED",
                                  "message": f"handler kind '{kind}' is not a declared kind"}])

    payload = _substitute(handler.get("payload_template", {}), canonical_input, input_contract)

    # Boundary error classification (Transport Standard V0 §7): a raise from behind the
    # boundary is projected as the EXECUTION_FAILURE Result Class, never leaked as a stack
    # trace. This is egress result classification, not control-flow fallback.
    try:
        outcome = invoke(handler, payload, data_root=data_root, snapshot_root=snapshot_root)
    except Exception as exc:  # noqa: BLE001 — boundary classification, re-projected below
        return _response(request_id, "EXECUTION_FAILURE",
                         errors=[{"code": "EXECUTION_FAILURE", "message": str(exc)}])

    te = contract.te
    result_class = te.get("result_classification", {}).get(
        outcome.status, te.get("default_result_class", "EXECUTION_FAILURE"))

    if result_class != _SUCCESS:
        return _response(request_id, result_class,
                         errors=[{"code": result_class, "message": f"handler status {outcome.status}"}])

    ctx = {"input": canonical_input, "surface": outcome.surface}
    result: dict[str, Any] = {}
    for spec in te.get("output_contract", []):
        value = _resolve_path(spec["from"], ctx)
        result[spec["field"]] = _DERIVE[spec.get("op", "identity")](value)

    evidence: list[str] = []
    if te.get("evidence_policy") == "reference_only" and outcome.evidence_ref is not None:
        evidence = [f"trace:{outcome.evidence_ref}"]

    return _response(request_id, _SUCCESS, result=result, evidence=evidence)
