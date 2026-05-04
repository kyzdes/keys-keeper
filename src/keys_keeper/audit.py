"""Append-only audit log (JSONL) with monthly rotation."""
from __future__ import annotations
import gzip
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from keys_keeper.paths import Paths


@dataclass
class AuditEvent:
    ts: str
    op: str
    name: str
    id: str
    caller_pid: int
    caller_path: str
    file_target: str | None
    success: bool
    error: str | None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, separators=(",", ":"))


def _resolve_caller_path(pid: int) -> str:
    try:
        out = os.popen(f"ps -p {pid} -o command=").read().strip()
        return out or "?"
    except Exception:
        return "?"


class AuditLog:
    def __init__(self, paths: Paths):
        self.paths = paths

    def record(
        self,
        *,
        op: str,
        name: str,
        id_: str,
        file_target: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # parent pid is the caller (CLI was invoked by zsh / claude / etc)
        ppid = os.getppid()
        event = AuditEvent(
            ts=now,
            op=op,
            name=name,
            id=id_,
            caller_pid=ppid,
            caller_path=_resolve_caller_path(ppid),
            file_target=file_target,
            success=success,
            error=error,
        )
        with open(self.paths.audit_jsonl, "a") as f:
            f.write(event.to_json() + "\n")

    def tail(self, n: int = 50) -> Iterator[dict]:
        if not self.paths.audit_jsonl.exists():
            return
        lines = self.paths.audit_jsonl.read_text().splitlines()
        for line in lines[-n:]:
            if line.strip():
                yield json.loads(line)

    def search(
        self,
        *,
        op: str | None = None,
        name: str | None = None,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> Iterator[dict]:
        if not self.paths.audit_jsonl.exists():
            return
        for line in self.paths.audit_jsonl.read_text().splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            if op and ev["op"] != op:
                continue
            if name and ev["name"] != name:
                continue
            if since and ev["ts"] < since.strftime("%Y-%m-%dT%H:%M:%SZ"):
                continue
            yield ev
            limit -= 1
            if limit <= 0:
                break

    def rotate_if_needed(self, now: datetime | None = None) -> None:
        """If audit.jsonl contains events from a previous month, archive them."""
        if not self.paths.audit_jsonl.exists():
            return
        now = now or datetime.now(timezone.utc)
        cur_ym = now.strftime("%Y-%m")
        # peek at the first event's month
        with open(self.paths.audit_jsonl) as f:
            first = f.readline().strip()
        if not first:
            return
        first_ev = json.loads(first)
        first_ym = first_ev["ts"][:7]
        if first_ym == cur_ym:
            return
        # archive the entire current file
        archive = self.paths.audit_archive(first_ym)
        with open(self.paths.audit_jsonl, "rb") as src, gzip.open(archive, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.unlink(self.paths.audit_jsonl)
