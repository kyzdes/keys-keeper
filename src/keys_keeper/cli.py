"""keys CLI — argparse routing + subcommand dispatch."""
from __future__ import annotations
import argparse
import hashlib
import os
import subprocess
import sys
import threading
from pathlib import Path

from keys_keeper import __version__
from keys_keeper.audit import AuditLog
from keys_keeper.backend import KeychainBackend, MacOSKeychainBackend
from keys_keeper.models import Entry, EntryType, ValidationError
from keys_keeper.paths import Paths
from keys_keeper.store import MetadataStore, NameConflict, NotFound, StoreError


# ----- backend factory (test override hook) -----

def _backend() -> KeychainBackend:
    return MacOSKeychainBackend(
        service=os.environ.get("KEYS_KEEPER_TEST_SERVICE", "keys-keeper"),
        keychain_path=os.environ.get("KEYS_KEEPER_TEST_KEYCHAIN"),
    )


# ----- input source resolution -----

def _read_input(args: argparse.Namespace) -> str:
    sources = [
        bool(args.from_clipboard),
        bool(args.from_file),
        bool(args.stdin),
        bool(args.web),
    ]
    if sum(sources) != 1:
        sys.stderr.write(
            "error: must specify exactly one input source: "
            "--from-clipboard | --from-file PATH | --stdin | --web\n"
        )
        return ""
    if args.from_clipboard:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return result.stdout
    if args.from_file:
        return Path(args.from_file).read_text()
    if args.stdin:
        return sys.stdin.read().rstrip("\n")
    if args.web:
        sys.stderr.write("--web flag is implemented in admin UI; not supported here yet\n")
        return ""
    return ""


# ----- subcommand handlers -----

def cmd_add(args: argparse.Namespace) -> int:
    paths = Paths()
    paths.ensure()
    store = MetadataStore(paths)
    audit = AuditLog(paths)
    backend = _backend()

    value = _read_input(args)
    if not value and not args.from_file:
        return 2

    fields: dict = {}
    if args.service:
        fields["service"] = args.service
    type_ = EntryType(args.type)
    try:
        entry = Entry.new(
            name=args.name,
            type=type_,
            fields=fields,
            tags=args.tag or [],
            note=args.note or "",
        )
    except ValidationError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2

    try:
        if args.replace:
            existing = store.get_by_name(args.name)
            if existing:
                entry.id = existing.id  # reuse keychain account
                store.replace_by_name(entry)
            else:
                store.add(entry)
        else:
            store.add(entry)
    except NameConflict as e:
        sys.stderr.write(f"error: {e}\n")
        return 1

    backend.set(entry.id, value)
    audit.record(op="add", name=entry.name, id_=entry.id, success=True)
    print(f"added {entry.type.value} '{entry.name}' (id={entry.id})")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = MetadataStore(Paths())
    entries = store.list()
    if args.type:
        entries = [e for e in entries if e.type.value == args.type]
    if args.tag:
        entries = [e for e in entries if args.tag in e.tags]
    if args.search:
        q = args.search.lower()
        entries = [e for e in entries if q in e.name.lower() or q in (e.note or "").lower()]
    if not entries:
        print("no entries")
        return 0
    for e in entries:
        tag_str = "[" + ",".join(e.tags) + "]" if e.tags else ""
        print(f"{e.type.value:10s}  {e.name:30s}  {tag_str}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    store = MetadataStore(Paths())
    e = store.get_by_name(args.name)
    if e is None:
        sys.stderr.write(f"no entry named {args.name!r}\n")
        return 1
    print(f"name:       {e.name}")
    print(f"type:       {e.type.value}")
    print(f"id:         {e.id}")
    print(f"created:    {e.created_at}")
    print(f"updated:    {e.updated_at}")
    print(f"tags:       {', '.join(e.tags) or '-'}")
    print(f"note:       {e.note or '-'}")
    if e.fields:
        print("fields:")
        for k, v in e.fields.items():
            print(f"  {k}: {v}")
    if e.refs:
        print("refs:")
        for r in e.refs:
            print(f"  {r['role']} -> {r['name']}")
    return 0


def cmd_reveal(args: argparse.Namespace) -> int:
    if os.environ.get("KEYS_KEEPER_ALLOW_REVEAL") != "1":
        sys.stderr.write(
            "error: `keys reveal` requires KEYS_KEEPER_ALLOW_REVEAL=1 in env. "
            "Add to ~/.zshrc to enable. (This guard exists so AI agents can't accidentally "
            "extract plaintext.)\n"
        )
        return 2
    paths = Paths()
    store = MetadataStore(paths)
    audit = AuditLog(paths)
    e = store.get_by_name(args.name)
    if e is None:
        sys.stderr.write(f"no entry named {args.name!r}\n")
        return 1
    backend = _backend()
    try:
        value = backend.get(e.id)
    except Exception as ex:
        audit.record(op="reveal", name=e.name, id_=e.id, success=False, error=str(ex))
        sys.stderr.write(f"failed to read keychain: {ex}\n")
        return 1
    if args.as_env:
        # NAME=value format for `eval $(keys reveal X --as-env)`
        env_name = e.name.upper().replace("-", "_").replace(".", "_")
        print(f"{env_name}={_shell_quote(value)}")
    else:
        sys.stdout.write(value)
        if not value.endswith("\n"):
            sys.stdout.write("\n")
    audit.record(op="reveal", name=e.name, id_=e.id, success=True)
    return 0


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def cmd_copy(args: argparse.Namespace) -> int:
    paths = Paths()
    store = MetadataStore(paths)
    audit = AuditLog(paths)
    e = store.get_by_name(args.name)
    if e is None:
        sys.stderr.write(f"no entry named {args.name!r}\n")
        return 1
    backend = _backend()
    try:
        value = backend.get(e.id)
    except Exception as ex:
        audit.record(op="copy", name=e.name, id_=e.id, success=False, error=str(ex))
        sys.stderr.write(f"failed to read keychain: {ex}\n")
        return 1

    proc = subprocess.run(["pbcopy"], input=value, text=True)
    if proc.returncode != 0:
        audit.record(op="copy", name=e.name, id_=e.id, success=False, error="pbcopy failed")
        sys.stderr.write("pbcopy failed\n")
        return 1

    written_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    print(f"copied {e.name} to clipboard · auto-clear in {args.clear_after}s")
    audit.record(op="copy", name=e.name, id_=e.id, success=True)

    if args.clear_after > 0:
        # Spawn a detached process to handle the clear, so this CLI exits immediately.
        clear_script = (
            f"sleep {args.clear_after}; "
            f"current=$(pbpaste 2>/dev/null); "
            f"current_hash=$(echo -n \"$current\" | shasum -a 256 | cut -d' ' -f1); "
            f"if [ \"$current_hash\" = \"{written_hash}\" ]; then printf '' | pbcopy; fi"
        )
        subprocess.Popen(
            ["sh", "-c", clear_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return 0


# ----- top-level parser -----

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="keys", description="personal secrets manager")
    p.add_argument("--version", action="version", version=f"keys-keeper {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # add
    a = sub.add_parser("add", help="add a new entry")
    a.add_argument("name")
    a.add_argument("--type", choices=[t.value for t in EntryType], default="api_key")
    a.add_argument("--from-clipboard", action="store_true")
    a.add_argument("--from-file")
    a.add_argument("--stdin", action="store_true")
    a.add_argument("--web", action="store_true")
    a.add_argument("--service")
    a.add_argument("--tag", action="append", default=[])
    a.add_argument("--note", default="")
    a.add_argument("--replace", action="store_true")
    a.set_defaults(func=cmd_add)

    # list
    l = sub.add_parser("list", help="list entries")
    l.add_argument("--type")
    l.add_argument("--tag")
    l.add_argument("--search")
    l.set_defaults(func=cmd_list)

    # info
    i = sub.add_parser("info", help="show entry metadata (no value)")
    i.add_argument("name")
    i.set_defaults(func=cmd_info)

    # reveal
    rv = sub.add_parser("reveal", help="print value to stdout (gated by env-var)")
    rv.add_argument("name")
    rv.add_argument("--as-env", action="store_true", help="print as NAME=value for eval")
    rv.set_defaults(func=cmd_reveal)

    # copy
    cp = sub.add_parser("copy", help="copy value to clipboard with auto-clear")
    cp.add_argument("name")
    cp.add_argument("--clear-after", type=int, default=30, help="seconds before auto-clear (0 = never)")
    cp.set_defaults(func=cmd_copy)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
