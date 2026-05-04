"""Shared pytest fixtures for keys-keeper."""
import os
import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def kk_home(tmp_path, monkeypatch):
    """Isolated KEYS_KEEPER_HOME for each test."""
    home = tmp_path / "kk-home"
    monkeypatch.setenv("KEYS_KEEPER_HOME", str(home))
    return home


@pytest.fixture
def test_keychain(tmp_path):
    """Create an isolated macOS keychain for testing.

    Returns the keychain path. Caller is responsible for setting
    `KEYS_KEEPER_TEST_KEYCHAIN` env var if the backend reads it,
    or for passing it explicitly to the backend constructor.
    """
    if os.uname().sysname != "Darwin":
        pytest.skip("macOS keychain tests require Darwin")
    kc_path = tmp_path / "test.keychain-db"
    pwd = "test-pwd"
    subprocess.run(
        ["security", "create-keychain", "-p", pwd, str(kc_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["security", "unlock-keychain", "-p", pwd, str(kc_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["security", "set-keychain-settings", "-u", str(kc_path)],
        check=True, capture_output=True,
    )
    yield kc_path
    subprocess.run(["security", "delete-keychain", str(kc_path)], capture_output=True)
