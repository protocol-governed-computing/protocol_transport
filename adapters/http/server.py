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

from adapters.http.binding import load_bindings, to_canonical_request
from resolver.registry import load_registry
from resolver.resolver import resolve

# Response Projection (adapter-owned; §7). Result Class -> HTTP status.
_HTTP_STATUS = {
    "SUCCESS": 200,
    "VIOLATION": 400,
    "UNAUTHORIZED": 401,
    "NOT_FOUND": 404,
    "EXECUTION_FAILURE": 500,
}


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


# ── configuration (env-provisioned; the adapter is POINTED at everything) ──
_MOUNTS = _parse_mounts(os.environ["PGC_STATIC_MOUNTS"])
_BINDINGS = load_bindings(Path(os.environ["PGC_HTTP_BINDINGS"]))
_REGISTRY = load_registry([Path(r) for r in os.environ["PGC_OPERATIONS_ROOTS"].split(":") if r])
_DATA_ROOT = os.environ["PGC_DATA_ROOT"]
_SNAPSHOT_ROOT = os.environ.get("PGC_SNAPSHOT_ROOT")  # None -> runtime default


class _Handler(BaseHTTPRequestHandler):
    server_version = "PGCTransportHTTP/0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[transport-http] " + (fmt % args) + "\n")

    # ── static serving ──
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        resolved = self._match_mount(path)
        if resolved is None:
            self._send(404, "text/plain", b"not found")
            return
        directory, rest = resolved
        target = (directory / rest).resolve()
        if not (target == directory or str(target).startswith(str(directory) + os.sep)):
            self._send(403, "text/plain", b"forbidden")
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self._send(404, "text/plain", b"not found")
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
        operation = _BINDINGS.get(("POST", path))
        if operation is None:
            self._json(404, {"outcome": "FAILURE", "result_class": "NOT_FOUND",
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

        canonical = to_canonical_request(operation, body if isinstance(body, dict) else {})
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
    print(f"[transport-http] serving on http://127.0.0.1:{port}")
    print(f"[transport-http] mounts:     {[(p, str(d)) for p, d in _MOUNTS]}")
    print(f"[transport-http] bindings:   {{{', '.join(f'{m} {p} -> {op}' for (m, p), op in _BINDINGS.items())}}}")
    print(f"[transport-http] operations: {sorted(_REGISTRY)}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[transport-http] shutting down")
        httpd.shutdown()


if __name__ == "__main__":
    main()
