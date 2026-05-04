"""JSON API handlers for the admin server."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlparse
from keys_keeper.audit import AuditLog
from keys_keeper.backend import MacOSKeychainBackend
from keys_keeper.paths import Paths
from keys_keeper.refs import reverse_refs
from keys_keeper.store import MetadataStore


def _backend():
    return MacOSKeychainBackend(
        service=os.environ.get("KEYS_KEEPER_TEST_SERVICE", "keys-keeper"),
        keychain_path=os.environ.get("KEYS_KEEPER_TEST_KEYCHAIN"),
    )


def handle_api(handler, *, paths: Paths, method: str, path: str, body: bytes | None) -> None:
    parsed = urlparse(path)
    route = parsed.path

    if route == "/api/entries" and method == "GET":
        return _entries(handler, paths, parsed.query)
    if route.startswith("/api/entries/") and method == "GET":
        entry_id = route.rsplit("/", 1)[-1]
        return _entry_detail(handler, paths, entry_id)
    if route == "/api/copy" and method == "POST":
        return _copy(handler, paths, body)
    if route == "/api/heartbeat" and method == "POST":
        handler._send_json(200, {"ok": True})
        return
    if route == "/api/shutdown" and method == "POST":
        # schedule a shutdown after responding
        handler._send_json(200, {"ok": True})
        threading.Thread(target=_shutdown_self, daemon=True).start()
        return
    if route == "/api/audit" and method == "GET":
        return _audit(handler, paths, parsed.query)

    handler._send_json(404, {"error": "not found"})


def _entries(handler, paths: Paths, query: str) -> None:
    store = MetadataStore(paths)
    entries = store.list()
    rev = reverse_refs(entries)
    out = []
    for e in entries:
        d = e.to_dict()
        d["used_by"] = rev.get(e.name, [])
        out.append(d)
    handler._send_json(200, {"entries": out})


def _entry_detail(handler, paths: Paths, entry_id: str) -> None:
    store = MetadataStore(paths)
    e = store.get_by_id(entry_id)
    if e is None:
        handler._send_json(404, {"error": "not found"})
        return
    rev = reverse_refs(store.list())
    d = e.to_dict()
    d["used_by"] = rev.get(e.name, [])
    # also inline last 5 audit events for this entry
    audit = AuditLog(paths)
    d["recent_events"] = list(audit.search(name=e.name, limit=5))
    handler._send_json(200, d)


def _copy(handler, paths: Paths, body: bytes) -> None:
    payload = json.loads(body or b"{}")
    entry_id = payload.get("id")
    store = MetadataStore(paths)
    audit = AuditLog(paths)
    e = store.get_by_id(entry_id) if entry_id else None
    if e is None:
        handler._send_json(404, {"error": "entry not found"})
        return
    backend = _backend()
    try:
        value = backend.get(e.id)
    except Exception as ex:
        audit.record(op="copy", name=e.name, id_=e.id, success=False, error=str(ex))
        handler._send_json(500, {"error": str(ex)})
        return
    proc = subprocess.run(["pbcopy"], input=value, text=True)
    if proc.returncode != 0:
        audit.record(op="copy", name=e.name, id_=e.id, success=False, error="pbcopy failed")
        handler._send_json(500, {"error": "pbcopy failed"})
        return
    audit.record(op="copy", name=e.name, id_=e.id, success=True)
    written_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    threading.Thread(
        target=_clipboard_clear_after,
        args=(written_hash, 30),
        daemon=True,
    ).start()
    handler._send_json(200, {"ok": True})


def _clipboard_clear_after(written_hash: str, delay: int) -> None:
    time.sleep(delay)
    current = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    current_hash = hashlib.sha256(current.encode("utf-8")).hexdigest()
    if current_hash == written_hash:
        subprocess.run(["pbcopy"], input="", text=True)


def _audit(handler, paths: Paths, query: str) -> None:
    qs = parse_qs(query)
    op = qs.get("op", [None])[0]
    name = qs.get("name", [None])[0]
    limit = int(qs.get("limit", ["100"])[0])
    audit = AuditLog(paths)
    events = list(audit.search(op=op, name=name, limit=limit))
    handler._send_json(200, {"events": events})


def _shutdown_self() -> None:
    # graceful exit — the test server handles the actual stop via close
    time.sleep(0.05)
    os._exit(0)
