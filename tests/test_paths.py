import os
from pathlib import Path
from keys_keeper.paths import Paths


def test_paths_default_uses_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.delenv("KEYS_KEEPER_HOME", raising=False)
    p = Paths()
    assert p.root == tmp_path / ".config" / "keys-keeper"
    assert p.data_json == p.root / "data.json"
    assert p.audit_jsonl == p.root / "audit.jsonl"
    assert p.config_toml == p.root / "config.toml"


def test_paths_respects_keys_keeper_home_override(tmp_path, monkeypatch):
    custom = tmp_path / "custom-kk"
    monkeypatch.setenv("KEYS_KEEPER_HOME", str(custom))
    p = Paths()
    assert p.root == custom


def test_paths_ensure_creates_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("KEYS_KEEPER_HOME", str(tmp_path / "kk"))
    p = Paths()
    assert not p.root.exists()
    p.ensure()
    assert p.root.exists()
    assert p.root.is_dir()
