"""HTTP Protocol Adapter (cut #1) — thin, non-authorial boundary over the PGC transport.

Layer 2 (Transport Standard V0). Responsibilities are protocol-mechanical only:
  - serve configured static mounts (a demo shell + workload screens it is POINTED at)
  - translate `POST <route>` → Canonical Transport Request via the External Protocol
    Binding table (data)
  - hand it to the protocol-neutral resolver
  - project the Canonical Transport Response onto HTTP (status + JSON) — Response
    Projection, adapter-owned and protocol-specific (§7, RESPONSE_PROJECTION_EXTERNAL).
    The Result-Class → HTTP-status table lives HERE, never in a TE.

Stdlib only. Contains no workload knowledge: every route, operation, and filesystem root
comes from environment/config (ADAPTER_NON_AUTHORIAL). The acid test — grep this file for
any workload name and find nothing.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from adapters.http.binding import (
    AdmissionError,
    load_bindings,
    select_operation,
    to_canonical_request,
)
from resolver.registry import load_registry
from resolver.resolver import resolve

# Response Projection (adapter-owned; §7). Result Class -> HTTP status.
_HTTP_STATUS = {
    "SUCCESS": 200,
    "VIOLATION": 400,
    "UNAUTHORIZED": 401,
    # Both governed absence classes project to 404 in HTTP — the protocol cannot express the
    # distinction, but the Result Class in the response body preserves it. Projection collapses
    # meaning; the canonical response must not.
    "NOT_FOUND": 404,
    "OPERATION_NOT_FOUND": 404,
    "EXECUTION_FAILURE": 500,
}

# Serve JSONL traces as text so they open in-browser rather than downloading.
mimetypes.add_type("text/plain", ".jsonl")

# Friendly, fail-soft 404 for GET static requests. Live-mounted artifacts (per-run traces,
# compiled snapshot) are transient by design: a missing one yields this page, never a crash.
_NOT_FOUND_HTML = (
    "<!doctype html><meta charset=utf-8><title>Not found</title>"
    "<body style=\"font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:80px auto;color:#334155\">"
    "<h1 style=\"color:#0b1e3c\">404 &mdash; Not found</h1>"
    "<p>The requested resource is unavailable. If this was a <strong>trace</strong> or a "
    "<strong>compiled artifact</strong> (e.g. a workflow projection), it may have been removed or "
    "regenerated &mdash; the <code>data/</code> instance or the snapshot may have been cleaned or rebuilt.</p>"
    "<p>Re-run the workload to recreate a trace, or rebuild the snapshot to regenerate compiled "
    "artifacts, then try again.</p>"
    "<p><a href=\"/\" style=\"color:#0b1e3c\">&larr; Back to the platform surface</a></p></body>"
).encode("utf-8")


def _parse_mounts(spec: str) -> list[tuple[str, Path]]:
    """Parse PGC_STATIC_MOUNTS ("prefix=dir;prefix=dir") → sorted (prefix, dir), longest first."""
    mounts: list[tuple[str, Path]] = []
    for pair in spec.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        prefix, _, directory = pair.partition("=")
        mounts.append((prefix.rstrip("/") or "/", Path(directory).resolve()))
    mounts.sort(key=lambda m: len(m[0]), reverse=True)  # "/" (len 1) sorts last
    return mounts


def _snapshot_identity(root: str | None) -> str:
    """The snapshot_id this adapter booted against, for the startup banner.

    Printed so a STALE server is a one-line comparison rather than an inference: the boundary is
    read once at import (see below), so a snapshot rebuilt after startup is invisible to a running
    process. Reporting the id it actually booted with makes that visible without guesswork.
    """
    if not root:
        return "(runtime default)"
    manifest = Path(root) / "manifest.json"
    if not manifest.is_file():
        return "(no manifest)"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("snapshot_id", "(absent)")
    except (OSError, ValueError):
        return "(unreadable)"


# ── configuration (env-provisioned; the adapter is POINTED at everything) ──
_MOUNTS = _parse_mounts(os.environ["PGC_STATIC_MOUNTS"])
_BINDINGS = load_bindings(Path(os.environ["PGC_HTTP_BINDINGS"]))
_DATA_ROOT = os.environ["PGC_DATA_ROOT"]
_SNAPSHOT_ROOT = os.environ.get("PGC_SNAPSHOT_ROOT")  # None -> runtime default
# TI/TE boundary contracts are read from the sealed snapshot (compiled TI_/TE_ kinds), ONCE, at
# import. The snapshot is immutable by construction, so re-reading it mid-flight would be reading
# for a change that cannot happen — and a boundary that silently reloaded itself would no longer
# be the sealed boundary the composition attested. The operational consequence is real, though:
# a snapshot rebuilt after startup is invisible until the process restarts, which is why the
# banner reports the snapshot_id and the operations this process actually booted with.
_REGISTRY = load_registry(Path(os.environ["PGC_SNAPSHOT_ROOT"]))


class _Handler(BaseHTTPRequestHandler):
    server_version = "PGCTransportHTTP/0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[transport-http] " + (fmt % args) + "\n")

    # ── static serving ──
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        resolved = self._match_mount(path)
        if resolved is None:
            self._send(404, "text/html", _NOT_FOUND_HTML)
            return
        directory, rest = resolved
        target = (directory / rest).resolve()
        if not (target == directory or str(target).startswith(str(directory) + os.sep)):
            self._send(403, "text/plain", b"forbidden")
            return
        if target.is_dir():
            if not path.endswith("/"):
                # Redirect to add the trailing slash so the page's RELATIVE asset paths
                # resolve under its own mount (e.g. /foo -> /foo/), keeping domain
                # screens decoupled from their mount prefix. Standard web-server behavior.
                self.send_response(301)
                self.send_header("Location", path + "/")
                self.end_headers()
                return
            target = target / "index.html"
        if not target.is_file():
            self._send(404, "text/html", _NOT_FOUND_HTML)
            return
        mime, _ = mimetypes.guess_type(str(target))
        self._send(200, mime or "application/octet-stream", target.read_bytes())

    def _match_mount(self, path: str):
        for prefix, directory in _MOUNTS:
            if prefix == "/":
                return directory, path.lstrip("/")
            if path == prefix or path.startswith(prefix + "/"):
                return directory, path[len(prefix):].lstrip("/")
        return None

    # ── transport boundary ──
    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        binding = _BINDINGS.get(("POST", path))
        if binding is None:
            self._json(404, {"outcome": "FAILURE", "result_class": "OPERATION_NOT_FOUND",
                             "result": None, "evidence": [],
                             "errors": [{"code": "NO_BINDING", "message": f"no operation bound to POST {path}"}]})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"outcome": "FAILURE", "result_class": "VIOLATION",
                             "result": None, "evidence": [],
                             "errors": [{"code": "MALFORMED_BODY", "message": "invalid JSON"}]})
            return

        # Namespace admission for an operation-in-body route. Refusing an identity outside the
        # admitted namespace is protocol mechanics; the adapter still never interprets the
        # identity it admits (ADAPTER_NON_AUTHORIAL).
        try:
            operation, canonical_input = select_operation(
                binding, body if isinstance(body, dict) else {})
        except AdmissionError as exc:
            self._json(400, {"outcome": "FAILURE", "result_class": "VIOLATION",
                             "result": None, "evidence": [],
                             "errors": [{"code": "OPERATION_NOT_ADMITTED", "message": str(exc)}]})
            return

        canonical = to_canonical_request(operation, canonical_input)
        response = resolve(canonical, _REGISTRY, data_root=_DATA_ROOT, snapshot_root=_SNAPSHOT_ROOT)
        self._json(_HTTP_STATUS.get(response["result_class"], 500), response)

    # ── helpers ──
    def _json(self, status: int, obj: dict) -> None:
        self._send(status, "application/json", json.dumps(obj).encode("utf-8"))

    def _send(self, status: int, mime: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.environ.get("PGC_HTTP_PORT", "8000"))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    # Flushed explicitly: stdout is block-buffered when redirected to a file, and this banner is
    # the record of WHAT this process booted with. A diagnostic that only appears on a tty is not
    # available in the situation it exists for — a surface launched in the background.
    print(f"[transport-http] serving on http://127.0.0.1:{port}", flush=True)
    print(f"[transport-http] mounts:     {[(p, str(d)) for p, d in _MOUNTS]}")
    routes = ', '.join(
        f"{m} {p} -> {b.operation or b.namespace + '* (in body)'}"
        for (m, p), b in _BINDINGS.items()
    )
    print(f"[transport-http] bindings:   {{{routes}}}")
    print(f"[transport-http] snapshot:   {_SNAPSHOT_ROOT} "
          f"({_snapshot_identity(_SNAPSHOT_ROOT)})")
    print(f"[transport-http] operations: {sorted(_REGISTRY)}")
    print("[transport-http] the boundary is read once, at startup — restart after any rebuild",
          flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[transport-http] shutting down")
        httpd.shutdown()


if __name__ == "__main__":
    main()
