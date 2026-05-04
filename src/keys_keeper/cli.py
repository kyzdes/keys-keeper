"""keys CLI — argparse routing + subcommand dispatch."""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
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

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
