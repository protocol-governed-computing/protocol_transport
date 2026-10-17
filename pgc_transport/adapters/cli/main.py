"""Command-line Protocol Adapter — the `pgc_transport` command.

Layer 2 (Transport Standard V0), the command-line counterpart of the HTTP adapter:

    pgc_transport call <operation> '<input as JSON>'
        Translate one invocation into a Canonical Transport Request, hand it to the
        protocol-neutral resolver, and print the Canonical Transport Response as JSON. The
        exit status is this adapter's Response Projection (§7, RESPONSE_PROJECTION_EXTERNAL):
        the Result-Class → exit-status table lives HERE, never in a TE.

    pgc_transport http
        Serve the HTTP adapter (`pgc_transport.adapters.http.server`), configured exactly as `run_http.sh`
        configures it.

Both are POINTED at everything through the environment (ADAPTER_NON_AUTHORIAL):
    PGC_SNAPSHOT_ROOT   the assembled snapshot the boundary is read from
    PGC_DATA_ROOT       the instance root execution writes traces and stored state under
plus, for `http`, the variables `run_http.sh` documents. Nothing here names a workload,
an operation or a field: the operation is whatever the caller names, and the snapshot's TI
alone decides whether to admit its input.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pgc_transport.adapters.http.binding import to_canonical_request
from pgc_transport.resolver.registry import load_registry
from pgc_transport.resolver.resolver import resolve

# Response Projection (adapter-owned; §7). Result Class -> exit status. Distinct statuses keep
# the classes apart for a caller that cannot read the body; the body carries the class itself.
_EXIT_STATUS = {
    "SUCCESS": 0,
    "VIOLATION": 1,
    "UNAUTHORIZED": 3,
    "NOT_FOUND": 4,
    "OPERATION_NOT_FOUND": 5,
    "EXECUTION_FAILURE": 6,
}
_USAGE = 2   # as argparse uses it: the invocation never reached the boundary


def _refuse(message: str) -> None:
    print(f"pgc_transport: {message}", file=sys.stderr)
    raise SystemExit(_USAGE)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        _refuse(f"{name} is not set. The adapter reads nothing it is not pointed at.")
    return value


def _call(operation: str, raw_input: str) -> int:
    try:
        canonical_input = json.loads(raw_input)
    except json.JSONDecodeError as exc:
        _refuse(f"the input is not JSON: {exc}")
    if not isinstance(canonical_input, dict):
        _refuse("the input must be a JSON object")

    snapshot_root = _required_env("PGC_SNAPSHOT_ROOT")
    data_root = _required_env("PGC_DATA_ROOT")
    registry = load_registry(Path(snapshot_root))
    response = resolve(to_canonical_request(operation, canonical_input), registry,
                       data_root=data_root, snapshot_root=snapshot_root)
    json.dump(response, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return _EXIT_STATUS.get(response["result_class"], _EXIT_STATUS["EXECUTION_FAILURE"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pgc_transport",
        description="The PGC transport boundary, from the command line.")
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    call = commands.add_parser("call", help="send one request through the boundary")
    call.add_argument("operation", help="the Operation Identity, e.g. one a TI in the snapshot declares")
    call.add_argument("input", nargs="?", default="{}", help="the operation's input, a JSON object")
    commands.add_parser("http", help="serve the HTTP adapter")
    args = parser.parse_args(argv)

    if args.command == "call":
        return _call(args.operation, args.input)
    # Imported only when asked for: the HTTP adapter reads its configuration at import.
    from pgc_transport.adapters.http import server
    server.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
