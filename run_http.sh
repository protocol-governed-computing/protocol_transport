#!/usr/bin/env bash
#
# Generic HTTP transport-adapter launcher. DOMAIN-NEUTRAL: it names no workload, no
# route, no operation, no domain path. The caller MUST point it at roots via the
# environment. See platform/demo_site/serve.sh for a concrete platform composition.
#
# Required env:
#   PGC_RUNTIME_ROOT     protocol_runtime repo root (provides the `runtime` package)
#   PGC_INSPECTOR_ROOT   snapshot_inspector repo root (provides the `inspector` package)
#   PGC_ASSEMBLER_ROOT   snapshot_assembler repo root (provides the `assembler` package)
#   PGC_STATIC_MOUNTS    "prefix=dir;prefix=dir" static mount table
#   PGC_HTTP_BINDINGS    path to the HTTP external-protocol-binding JSON
#   PGC_SNAPSHOT_ROOT    assembled snapshot dir (read-only input)
#   PGC_DATA_ROOT        instance root for CS state + traces (mutable output)
# Optional env:
#   PGC_IMPL_ROOTS       colon-separated roots for domain CT/CS impl imports (handler_ref)
#   PGC_HTTP_PORT        default 8000
#   PGC_HTTP_BIND        listen address, default 127.0.0.1
#   PGC_COORDINATOR_URL  required when the snapshot places execution on FEDERATED_NODE
#   PYTHON               default python3
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # protocol_transport/ = source root for `adapters`,`resolver`
PYTHON="${PYTHON:-python3}"

# The three interface roots default to wherever the interpreter already keeps its
# packages. That is not a guess and not a fallback: a root names the directory a
# package is read from, and the interpreter is the authority on where its own
# packages live. Setting any of them still overrides, which is what a development
# checkout does — it points at repo roots instead.
#
# The check below is what makes this fail-hard rather than permissive. Previously
# an unset or wrong root produced no error here at all: the launcher accepted it,
# and the failure surfaced inside the server as `ModuleNotFoundError: No module
# named 'runtime'`, three frames deep in the resolver, naming a package rather
# than the misconfigured root that caused it. Silent until far too late is the
# failure mode this repo's fail-hard rule exists to prevent.
_SITE="$("$PYTHON" -c 'import site,sys; p=site.getsitepackages() if hasattr(site,"getsitepackages") else []; sys.stdout.write(p[0] if p else "")' 2>/dev/null || true)"
: "${PGC_RUNTIME_ROOT:=$_SITE}"
: "${PGC_INSPECTOR_ROOT:=$_SITE}"
: "${PGC_ASSEMBLER_ROOT:=$_SITE}"

for _pair in "runtime:$PGC_RUNTIME_ROOT" "inspector:$PGC_INSPECTOR_ROOT" "assembler:$PGC_ASSEMBLER_ROOT"; do
  _pkg="${_pair%%:*}"; _root="${_pair#*:}"
  if [ -z "$_root" ]; then
    echo "run_http.sh: no root for '$_pkg' and $PYTHON reports no site-packages." >&2
    echo "  Set PGC_$(echo "$_pkg" | tr '[:lower:]' '[:upper:]')_ROOT to the directory providing it." >&2
    exit 2
  fi
  if ! PYTHONPATH="$_root" "$PYTHON" -c "import $_pkg" >/dev/null 2>&1; then
    echo "run_http.sh: '$_pkg' is not importable from $_root" >&2
    echo "  In a development checkout this is the component's repository root." >&2
    echo "  Under an install it is the interpreter's site-packages, which is the default." >&2
    echo "  Interpreter: $PYTHON" >&2
    exit 2
  fi
done
: "${PGC_STATIC_MOUNTS:?set PGC_STATIC_MOUNTS (prefix=dir;prefix=dir)}"
: "${PGC_HTTP_BINDINGS:?set PGC_HTTP_BINDINGS (path to binding JSON)}"
: "${PGC_SNAPSHOT_ROOT:?set PGC_SNAPSHOT_ROOT (assembled snapshot dir)}"
: "${PGC_DATA_ROOT:?set PGC_DATA_ROOT (instance root for CS state + traces)}"

# Source roots on PYTHONPATH (env-provisioned; no sys.path manipulation):
#   this repo  -> `adapters`, `resolver`
#   runtime    -> `runtime`   (the EXECUTION interface, handler kind WF_INVOCATION)
#   inspector  -> `inspector` (the INSPECTION interface, kinds SNAPSHOT_READ/SNAPSHOT_QUERY)
#   assembler  -> `assembler` (acceptance: `runtime.boot` reaches the SAME determination the
#                 assembler makes rather than carrying a second, weaker copy of it — so booting a
#                 snapshot needs it on the path, adapter or CLI alike)
#   impl roots -> domain CT/CS impls loaded by handler_ref at execution time
# Both interfaces are required, not optional: the engine knows three handler kinds from day one,
# and a domain declares which of them it uses. An engine that imported an interface only when some
# snapshot happened to need it would resolve its own capabilities by discovery.
export PYTHONPATH="$SCRIPT_DIR:$PGC_RUNTIME_ROOT:$PGC_INSPECTOR_ROOT:$PGC_ASSEMBLER_ROOT${PGC_IMPL_ROOTS:+:$PGC_IMPL_ROOTS}${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$PGC_DATA_ROOT"

exec "$PYTHON" -m adapters.http.server
