"""keys ssh — resolve server + ssh_key, write tempfile, exec ssh."""
from __future__ import annotations
import os
import subprocess
import tempfile
from keys_keeper.backend import KeychainBackend
from keys_keeper.models import Entry, EntryType
from keys_keeper.refs import resolve_chain, RefMissingError
from keys_keeper.store import MetadataStore


def run_ssh(
    *,
    store: MetadataStore,
    backend: KeychainBackend,
    server_name: str,
    extra_cmd: str | None = None,
) -> int:
    server = store.get_by_name(server_name)
    if server is None or server.type != EntryType.SERVER:
        raise ValueError(f"{server_name!r} is not a server entry")
    host = server.fields["host"]
    user = server.fields.get("user", "root")
    port = int(server.fields.get("port", 22))
    auth = server.fields.get("auth", "ssh_key")

    if auth == "ssh_key":
        try:
            ssh_entry = resolve_chain(store.list(), server_name, "ssh_key")
        except RefMissingError as e:
            raise ValueError(f"server {server_name} requires ssh_key ref: {e}")
        private_key = backend.get(ssh_entry.id)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".key", delete=False, dir=os.path.expanduser("~/.ssh") if os.path.exists(os.path.expanduser("~/.ssh")) else None,
        ) as tmp:
            os.chmod(tmp.name, 0o600)
            tmp.write(private_key)
            if not private_key.endswith("\n"):
                tmp.write("\n")
            tmp_path = tmp.name
        try:
            cmd = ["ssh", "-i", tmp_path, "-p", str(port), f"{user}@{host}"]
            if extra_cmd:
                cmd.append(extra_cmd)
            result = subprocess.run(cmd)
            return result.returncode
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
    elif auth == "password":
        cmd = ["ssh", "-p", str(port), f"{user}@{host}"]
        if extra_cmd:
            cmd.append(extra_cmd)
        return subprocess.run(cmd).returncode
    else:
        cmd = ["ssh", "-p", str(port), f"{user}@{host}"]
        if extra_cmd:
            cmd.append(extra_cmd)
        return subprocess.run(cmd).returncode
