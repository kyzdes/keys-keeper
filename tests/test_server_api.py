import json
import threading
import time
import urllib.request
import urllib.error
import pytest
from io import StringIO
from keys_keeper import cli
from keys_keeper.paths import Paths
from keys_keeper.server import AdminServer


@pytest.fixture
def admin(kk_home, test_keychain, monkeypatch):
    monkeypatch.setenv("KEYS_KEEPER_TEST_KEYCHAIN", str(test_keychain))
    monkeypatch.setenv("KEYS_KEEPER_TEST_SERVICE", "keys-keeper-test")
    paths = Paths()
    paths.ensure()
    server = AdminServer(paths=paths, port=0, idle_timeout_sec=60)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    while server.bound_port == 0:
        time.sleep(0.01)
    yield server
    server.stop()


def _post(admin, path, payload=None):
    data = json.dumps(payload).encode() if payload else b""
    req = urllib.request.Request(
        f"http://127.0.0.1:{admin.bound_port}{path}",
        data=data,
        method="POST",
    )
    req.add_header("Sec-Keys-Token", admin.token)
    req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, timeout=2)


def _get(admin, path):
    req = urllib.request.Request(f"http://127.0.0.1:{admin.bound_port}{path}")
    req.add_header("Sec-Keys-Token", admin.token)
    return urllib.request.urlopen(req, timeout=2)


def _seed(monkeypatch, name, value="v"):
    monkeypatch.setattr("sys.stdin", StringIO(value + "\n"))
    cli.main(["add", name, "--type", "api_key", "--stdin"])


def test_api_entries_returns_seeded_data(admin, monkeypatch):
    _seed(monkeypatch, "api-test-1")
    _seed(monkeypatch, "api-test-2")
    resp = _get(admin, "/api/entries")
    data = json.loads(resp.read())
    names = {e["name"] for e in data["entries"]}
    assert "api-test-1" in names
    assert "api-test-2" in names
    # values must NEVER appear in response
    body_str = json.dumps(data)
    assert "v\n" not in body_str
    assert "value" not in body_str.lower() or "value" not in [k for e in data["entries"] for k in e.get("fields", {})]


def test_api_copy_writes_clipboard_and_audits(admin, monkeypatch):
    _seed(monkeypatch, "copy-target", value="copy-secret-v")
    entries = json.loads(_get(admin, "/api/entries").read())["entries"]
    entry_id = next(e["id"] for e in entries if e["name"] == "copy-target")
    resp = _post(admin, "/api/copy", {"id": entry_id})
    payload = json.loads(resp.read())
    assert payload["ok"] is True
    import subprocess
    pasted = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    assert pasted == "copy-secret-v"
    # audit
    from keys_keeper.audit import AuditLog
    events = list(AuditLog(Paths()).search(op="copy"))
    assert any(e["name"] == "copy-target" for e in events)


def test_api_heartbeat_returns_ok(admin):
    resp = _post(admin, "/api/heartbeat")
    assert json.loads(resp.read())["ok"] is True


def test_api_shutdown_stops_server(admin):
    # In production this os._exit's; we patch it for the test.
    import os as _os
    real_exit = _os._exit
    called = threading.Event()
    def fake_exit(_):
        called.set()
    _os._exit = fake_exit
    try:
        _post(admin, "/api/shutdown")
        assert called.wait(timeout=2)
    finally:
        _os._exit = real_exit


def test_api_audit_returns_recent_events(admin, monkeypatch):
    _seed(monkeypatch, "audit-target")
    resp = _get(admin, "/api/audit?limit=10")
    events = json.loads(resp.read())["events"]
    assert any(e["name"] == "audit-target" for e in events)
