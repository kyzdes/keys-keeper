import os
import subprocess
import time
import pytest
from io import StringIO
from keys_keeper import cli


@pytest.fixture
def cli_env(kk_home, test_keychain, monkeypatch):
    monkeypatch.setenv("KEYS_KEEPER_TEST_KEYCHAIN", str(test_keychain))
    monkeypatch.setenv("KEYS_KEEPER_TEST_SERVICE", "keys-keeper-test")
    return kk_home


def _add(name, value, monkeypatch):
    monkeypatch.setattr("sys.stdin", StringIO(value + "\n"))
    cli.main(["add", name, "--type", "api_key", "--stdin"])


def test_reveal_blocked_without_env_var(cli_env, capsys, monkeypatch):
    monkeypatch.delenv("KEYS_KEEPER_ALLOW_REVEAL", raising=False)
    _add("rev1", "secret-val", monkeypatch)
    capsys.readouterr()
    rc = cli.main(["reveal", "rev1"])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "keys_keeper_allow_reveal" in err
    assert "secret-val" not in err


def test_reveal_with_env_prints_value(cli_env, capsys, monkeypatch):
    _add("rev2", "secret-val-2", monkeypatch)
    monkeypatch.setenv("KEYS_KEEPER_ALLOW_REVEAL", "1")
    capsys.readouterr()
    rc = cli.main(["reveal", "rev2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "secret-val-2" in out


def test_reveal_unknown_name(cli_env, capsys, monkeypatch):
    monkeypatch.setenv("KEYS_KEEPER_ALLOW_REVEAL", "1")
    rc = cli.main(["reveal", "ghost"])
    assert rc != 0


def test_copy_writes_to_pbcopy(cli_env, capsys, monkeypatch):
    _add("cp1", "clip-secret", monkeypatch)
    capsys.readouterr()
    rc = cli.main(["copy", "cp1"])
    assert rc == 0
    pasted = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    assert pasted == "clip-secret"
    out = capsys.readouterr().out
    assert "clip-secret" not in out  # never echoed
    assert "copied" in out.lower()


def test_copy_records_audit(cli_env, monkeypatch):
    from keys_keeper.audit import AuditLog
    from keys_keeper.paths import Paths
    _add("cp2", "v2", monkeypatch)
    cli.main(["copy", "cp2"])
    events = list(AuditLog(Paths()).search(op="copy"))
    assert any(e["name"] == "cp2" for e in events)
