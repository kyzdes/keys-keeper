import pytest
from keys_keeper import cli


@pytest.fixture
def cli_env(kk_home, test_keychain, monkeypatch):
    monkeypatch.setenv("KEYS_KEEPER_TEST_KEYCHAIN", str(test_keychain))
    monkeypatch.setenv("KEYS_KEEPER_TEST_SERVICE", "keys-keeper-test")
    return kk_home


def test_doctor_creates_paths_and_returns_0(cli_env, capsys):
    rc = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "data.json" in out
    assert "audit.jsonl" in out


def test_doctor_warns_when_reveal_env_missing(cli_env, capsys, monkeypatch):
    monkeypatch.delenv("KEYS_KEEPER_ALLOW_REVEAL", raising=False)
    cli.main(["doctor"])
    out = capsys.readouterr().out
    assert "KEYS_KEEPER_ALLOW_REVEAL" in out
