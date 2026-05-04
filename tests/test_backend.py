import os
import pytest
from keys_keeper.backend import (
    KeychainBackend,
    MacOSKeychainBackend,
    KeychainError,
)


@pytest.fixture
def backend(test_keychain):
    return MacOSKeychainBackend(
        service="keys-keeper-test",
        keychain_path=str(test_keychain),
    )


def test_set_and_get_round_trip(backend):
    backend.set("kk:abc", "sk-test-secret")
    assert backend.get("kk:abc") == "sk-test-secret"


def test_get_missing_raises(backend):
    with pytest.raises(KeychainError, match="not found"):
        backend.get("kk:does-not-exist")


def test_set_overwrites_existing(backend):
    backend.set("kk:abc", "first")
    backend.set("kk:abc", "second")
    assert backend.get("kk:abc") == "second"


def test_delete_removes_entry(backend):
    backend.set("kk:abc", "x")
    backend.delete("kk:abc")
    with pytest.raises(KeychainError):
        backend.get("kk:abc")


def test_delete_missing_is_noop(backend):
    # idempotent delete
    backend.delete("kk:never-set")  # must not raise


def test_list_ids_returns_only_our_service(backend):
    backend.set("kk:a", "1")
    backend.set("kk:b", "2")
    backend.set("kk:b:passphrase", "p")
    ids = set(backend.list_ids())
    assert ids == {"kk:a", "kk:b", "kk:b:passphrase"}


def test_set_multiline_value(backend):
    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nlinetwo\n-----END-----\n"
    backend.set("kk:multi", pem)
    assert backend.get("kk:multi") == pem
