#!/usr/bin/env bash
#
# Generic HTTP transport-adapter launcher. DOMAIN-NEUTRAL: it names no workload, no
# route, no operation, no domain path. The caller MUST point it at roots via the
# environment. See platform/demo_site/serve.sh for a concrete platform composition.
#
# Required env:
#   PGC_RUNTIME_ROOT     protocol_runtime repo root (provides the `runtime` package)
#   PGC_STATIC_MOUNTS    "prefix=dir;prefix=dir" static mount table
#   PGC_HTTP_BINDINGS    path to the HTTP external-protocol-binding JSON
#   PGC_SNAPSHOT_ROOT    assembled snapshot dir (read-only input)
#   PGC_DATA_ROOT        instance root for CS state + traces (mutable output)
# Optional env:
#   PGC_IMPL_ROOTS       colon-separated roots for domain CT/CS impl imports (handler_ref)
#   PGC_HTTP_PORT        default 8000
#   PYTHON               default python3
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # protocol_transport/ = source root for `adapters`,`resolver`
PYTHON="${PYTHON:-python3}"

: "${PGC_RUNTIME_ROOT:?set PGC_RUNTIME_ROOT (protocol_runtime repo root)}"
: "${PGC_STATIC_MOUNTS:?set PGC_STATIC_MOUNTS (prefix=dir;prefix=dir)}"
: "${PGC_HTTP_BINDINGS:?set PGC_HTTP_BINDINGS (path to binding JSON)}"
: "${PGC_SNAPSHOT_ROOT:?set PGC_SNAPSHOT_ROOT (assembled snapshot dir)}"
: "${PGC_DATA_ROOT:?set PGC_DATA_ROOT (instance root for CS state + traces)}"

# Source roots on PYTHONPATH (env-provisioned; no sys.path manipulation):
#   this repo  -> `adapters`, `resolver`
#   runtime    -> `runtime` (execution interface)
#   impl roots -> domain CT/CS impls loaded by handler_ref at execution time
export PYTHONPATH="$SCRIPT_DIR:$PGC_RUNTIME_ROOT${PGC_IMPL_ROOTS:+:$PGC_IMPL_ROOTS}${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$PGC_DATA_ROOT"

exec "$PYTHON" -m adapters.http.server
