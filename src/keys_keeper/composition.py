"""Composition root — builds adapters from environment.

Single dispatch point for swappable adapters (today macOS-only;
v0.2 will add Linux/Windows backends here without touching cli/api).
"""
from __future__ import annotations
import os

from keys_keeper.backend import KeychainBackend, MacOSKeychainBackend


def build_backend() -> KeychainBackend:
    return MacOSKeychainBackend(
        service=os.environ.get("KEYS_KEEPER_TEST_SERVICE", "keys-keeper"),
        keychain_path=os.environ.get("KEYS_KEEPER_TEST_KEYCHAIN"),
    )
