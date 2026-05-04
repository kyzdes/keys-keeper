"""JSON API handlers."""
from __future__ import annotations
import json
from keys_keeper.paths import Paths
from keys_keeper.store import MetadataStore


def handle_api(handler, *, paths: Paths, method: str, path: str, body: bytes | None) -> None:
    if path == "/api/entries" and method == "GET":
        store = MetadataStore(paths)
        items = [e.to_dict() for e in store.list()]
        handler._send_json(200, {"entries": items})
        return
    if path == "/api/heartbeat" and method == "POST":
        # The server already heartbeats on every request; this endpoint is just a
        # cheap ping the page calls every 60s.
        handler._send_json(200, {"ok": True})
        return
    handler._send_json(404, {"error": "not found"})
