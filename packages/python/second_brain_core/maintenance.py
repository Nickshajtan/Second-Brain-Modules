"""Trusted-host history maintenance; never a public operation discriminator."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from jsonschema.exceptions import SchemaError, ValidationError

from .boundary import CoreError
from .git_store import StorageError
from .history_index import HistoryIndexError

if TYPE_CHECKING:
    from .application import Core


def _host(core: Core) -> None:
    if not core.context.principal.bootstrap:
        core.boundary.fail("FORBIDDEN")


def _diagnostic(exc: Exception) -> dict[str, object]:
    category = exc.category if isinstance(exc, HistoryIndexError) else "CANONICAL_STATE_CORRUPT"
    if isinstance(exc, StorageError):
        if str(exc) in {"MISSING_ANCESTOR", "NONLINEAR_HISTORY"}:
            category = str(exc)
        elif "Missing canonical blob" in str(exc):
            category = "MISSING_ANCESTOR"
    rebuild = category in {"INDEX_MISSING", "INDEX_STALE", "INDEX_CORRUPT"}
    return dict(
        status="repair_required",
        code=category,
        rebuild_sufficient=rebuild,
        recommendation="explicit_rebuild" if rebuild else "operator_review_canonical_history",
    )


def audit_history(core: Core, *, recommend_rebuild: bool = True) -> dict[str, object]:
    """Verify only; optional recommendation never mutates Git or the disk index."""
    _host(core)
    try:
        with core.store.writer():
            result = core.history_index.audit()
        if not recommend_rebuild:
            result.pop("rebuild_recommended", None)
        return result
    except (
        CoreError,
        StorageError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        ValidationError,
        SchemaError,
    ) as exc:
        return _diagnostic(exc)


def rebuild_history_index(core: Core) -> dict[str, object]:
    """Explicit full canonical verification and fenced atomic derived replacement."""
    _host(core)
    try:
        with core.store.writer():
            return core.history_index.rebuild()
    except (
        CoreError,
        StorageError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        ValidationError,
        SchemaError,
    ) as exc:
        return _diagnostic(exc)
