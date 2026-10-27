"""Fixed projection DML capture; never a canonical journal or mutable disk SQL."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any

# These templates are exactly the deterministic writes of TransitionVerifier.
# A format change must review this vocabulary; arbitrary signed SQL is not run.
INSERTS = {
    "files": 3,
    "resources": 4,
    "revisions": 5,
    "definitions": 4,
    "memberships": 2,
    "receipts": 5,
    "operation_keys": 5,
    "effects": 6,
    "replay_scopes": 5,
    "endpoints": 2,
    "legacy": 4,
    "immutable": 2,
    "commits": 3,
}
WRITES = {
    f"INSERT INTO {table} VALUES({','.join('?' for _ in range(arity))})": arity
    for table, arity in INSERTS.items()
}
WRITES["INSERT OR REPLACE INTO files VALUES(?,?,?)"] = 3
WRITES.update(
    (f"DELETE FROM {table} WHERE path=?", 1)
    for table in ("files", "resources", "memberships", "definitions", "revisions")
)
WRITES["DELETE FROM endpoints WHERE relation=?"] = 1
WRITES["INSERT OR REPLACE INTO commitment_leaves VALUES(?,?,?)"] = 3
WRITES["DELETE FROM commitment_leaves WHERE path=?"] = 1
WRITES["INSERT OR REPLACE INTO commitment_nodes VALUES(?,?,?)"] = 3
WRITES["DELETE FROM commitment_nodes WHERE height=? AND position=?"] = 2


def checked_write(sql: str, parameters: object) -> tuple[str, list]:
    """Validate the fixed derived vocabulary before capture or authenticated replay."""
    normalized = " ".join(sql.split())
    if (
        normalized not in WRITES
        or not isinstance(parameters, list | tuple)
        or len(parameters) != WRITES[normalized]
        or any(value is not None and type(value) not in (str, int) for value in parameters)
    ):
        raise ValueError("Invalid projection delta statement")
    return normalized, list(parameters)


class ProjectionConnection(sqlite3.Connection):
    """Private memory connection with bounded, fixed-statement transaction capture."""

    writes: list | None = None

    def execute(
        self, sql: str, parameters: Sequence[Any] | Mapping[str, Any] = (), /
    ) -> sqlite3.Cursor:
        mutation = sql.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "DELETE", "UPDATE"}
        item = checked_write(sql, parameters) if mutation and self.writes is not None else None
        result = super().execute(sql, parameters)
        writes = self.writes
        if item is not None and writes is not None:
            writes.append(item)
        return result


def memory_connection() -> ProjectionConnection:
    """No disk SQLite connection is part of the trusted read path."""
    return sqlite3.connect(":memory:", factory=ProjectionConnection)
