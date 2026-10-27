"""Versioned SHA256 content commitment; derived nodes are never canonical content."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping, Sequence
from uuid import UUID

SCHEME = "sha256-bucket16-v1"
PREFIX = b"second-brain.content\x00sha256-bucket16-v1\x00"
SCHEMA = """
CREATE TABLE commitment_leaves(bucket INTEGER, path TEXT PRIMARY KEY, sha TEXT NOT NULL);
CREATE INDEX commitment_bucket ON commitment_leaves(bucket);
CREATE TABLE commitment_nodes(height INTEGER, position INTEGER, hash TEXT NOT NULL,
 PRIMARY KEY(height,position));
"""


def frame(tag: bytes, parts: Sequence[bytes]) -> bytes:
    """Unambiguous domain/version framing; lengths are unsigned big-endian."""
    return (
        PREFIX
        + len(tag).to_bytes(2)
        + tag
        + len(parts).to_bytes(4)
        + b"".join(len(part).to_bytes(8) + part for part in parts)
    )


class ContentCommitment:
    """Fixed-depth directory of complete buckets; worst-case bucket cost is linear."""

    def __init__(self, connection: sqlite3.Connection, instance: str) -> None:
        self.connection = connection
        self.instance = UUID(instance).bytes
        self.defaults = [self._hash(b"empty", [self.instance])]
        for height in range(1, 17):
            self.defaults.append(self._parent(height, self.defaults[-1], self.defaults[-1]))

    @staticmethod
    def _hash(tag: bytes, parts: Sequence[bytes]) -> str:
        return hashlib.sha256(frame(tag, parts)).hexdigest()

    def bucket(self, path: str) -> int:
        return int(self._hash(b"key", [self.instance, path.encode("utf-8")])[:4], 16)

    def _parent(self, height: int, left: str, right: str) -> str:
        return self._hash(
            b"branch",
            [self.instance, height.to_bytes(2), bytes.fromhex(left), bytes.fromhex(right)],
        )

    def _node(self, height: int, position: int) -> str:
        row = self.connection.execute(
            "SELECT hash FROM commitment_nodes WHERE height=? AND position=?", (height, position)
        ).fetchone()
        return row[0] if row else self.defaults[height]

    def update(self, changes: Mapping[str, str | None], *, apply: bool = False) -> dict[str, str]:
        """Overlay changed SHA256 leaves, recomputing complete touched buckets/branches.

        Preview never writes. Apply is owned by the verifier's SQLite transaction.
        Callers must validate canonical paths and bind content hashes to Git bytes.
        """
        buckets: dict[int, dict[str, str | None]] = {}
        seen = set()
        for path, value in changes.items():
            if path in seen:
                raise ValueError("Duplicate canonical path")
            seen.add(path)
            buckets.setdefault(self.bucket(path), {})[path] = value
        pending: dict[tuple[int, int], str] = {}
        for bucket, updates in buckets.items():
            values = dict(
                self.connection.execute(
                    "SELECT path,sha FROM commitment_leaves WHERE bucket=?", (bucket,)
                )
            )
            for path, value in updates.items():
                if value is None:
                    values.pop(path, None)
                else:
                    if len(value) != 64 or bytes.fromhex(value).hex() != value:
                        raise ValueError("Invalid content SHA256")
                    values[path] = value
                if apply:
                    if value is None:
                        self.connection.execute(
                            "DELETE FROM commitment_leaves WHERE path=?", (path,)
                        )
                    else:
                        self.connection.execute(
                            "INSERT OR REPLACE INTO commitment_leaves VALUES(?,?,?)",
                            (bucket, path, value),
                        )
            leaf = self.defaults[0]
            if values:
                entries = b"".join(
                    frame(b"entry", [path.encode("utf-8"), bytes.fromhex(value)])
                    for path, value in sorted(values.items())
                )
                leaf = self._hash(
                    b"bucket", [self.instance, bucket.to_bytes(2), len(values).to_bytes(4), entries]
                )
            pending[0, bucket] = leaf
        positions = set(buckets)
        for height in range(1, 17):
            positions = {position // 2 for position in positions}
            for position in positions:
                children = [
                    pending.get((height - 1, child)) or self._node(height - 1, child)
                    for child in (position * 2, position * 2 + 1)
                ]
                pending[height, position] = self._parent(height, *children)
        if apply:
            for (height, position), value in sorted(pending.items()):
                if value == self.defaults[height]:
                    self.connection.execute(
                        "DELETE FROM commitment_nodes WHERE height=? AND position=?",
                        (height, position),
                    )
                else:
                    self.connection.execute(
                        "INSERT OR REPLACE INTO commitment_nodes VALUES(?,?,?)",
                        (height, position, value),
                    )
        root = pending.get((16, 0)) or self._node(16, 0)
        return {
            "algorithm": "sha256",
            "value": self._hash(b"root", [self.instance, bytes.fromhex(root)]),
        }


def content_digest(instance: str, files: Mapping[str, bytes]) -> dict[str, str]:
    """Explicit full build for bootstrap/forensic verification, never warm mutation."""
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(SCHEMA)
        return ContentCommitment(connection, instance).update(
            {path: hashlib.sha256(raw).hexdigest() for path, raw in files.items() if covered(path)}
        )


def covered(path: str) -> bool:
    return path.startswith("knowledge/") or path == "control/metadata.json"
