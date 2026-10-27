"""Trusted-host history maintenance; never a public operation discriminator."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import TYPE_CHECKING

from jsonschema.exceptions import SchemaError, ValidationError

from .boundary import GENERATION, CoreError, uid
from .codec import encode
from .commitment import SCHEME, ContentCommitment
from .git_store import StorageError
from .history_index import (
    MAX_DELTA_BYTES,
    MAX_DELTAS,
    PREDECESSOR_CONTRACTS,
    HistoryIndex,
    HistoryIndexError,
)

MAINTENANCE_DELTAS = MAX_DELTAS // 2
MAINTENANCE_BYTES = MAX_DELTA_BYTES // 2
ERRORS = (
    CoreError,
    StorageError,
    OSError,
    ValueError,
    KeyError,
    TypeError,
    sqlite3.Error,
    ValidationError,
    SchemaError,
)

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
        recommendation=(
            "explicit_compaction_or_rebuild"
            if category == "INDEX_COMPACTION_REQUIRED"
            else "explicit_rebuild"
            if rebuild
            else "operator_review_canonical_history"
        ),
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


def compact_history_index(core: Core) -> dict[str, object]:
    """Explicitly compact accepted authenticated derived state; Git is untouched."""
    _host(core)
    try:
        with core.store.writer():
            return core.history_index.compact()
    except (
        CoreError,
        StorageError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
    ) as exc:
        return _diagnostic(exc)


def upgrade_history_index(core: Core) -> dict[str, object]:
    """Explicitly authenticate the known predecessor before a source-fenced rebuild.

    The prior checkpoint/key/ancestry remain authoritative after interruption.
    Unknown schema bindings cannot authorize reenrollment.
    """
    _host(core)
    index = core.history_index
    try:
        with core.store.writer():
            index.upgrading = True
            payload = index.anchor(rebuilding=True)
            if payload is None:
                index.fail("INDEX_MISSING")
            if payload["binding"] != index.binding:
                predecessor = HistoryIndex(core.repository)
                predecessor.binding = dict(index.binding, format=3, contracts=PREDECESSOR_CONTRACTS)
                predecessor.load(locked=True)
                if predecessor.connection is not None:
                    predecessor.connection.close()
            result = index.rebuild()
            result["status"] = "upgraded"
            return result
    except ERRORS as exc:
        return _diagnostic(exc)
    finally:
        index.upgrading = False


def adopt_generation_commitment(core: Core) -> dict[str, object]:
    """Publish only a one-way versioned generation descriptor; no knowledge rewrite."""
    _host(core)
    index = core.history_index
    try:
        with core.store.writer():
            index.ensure(locked=True)
            index.coherent()
            if index.generation is None or index.connection is None or index.frontier is None:
                index.fail("INDEX_MISSING")
            if index.generation.get("commitment_scheme") == SCHEME:
                return dict(status="already_adopted", generation=index.generation)
            generation = dict(
                instance_id=core.context.instance_id,
                generation_id=uid(),
                commitment_scheme=SCHEME,
                digest=ContentCommitment(index.connection, core.context.instance_id).update({}),
            )
            parent = index.frontier
            candidate = core.store.prepare_delta({GENERATION: encode(generation)}, parent)
            with index.candidate(candidate) as (connection, verified):
                core.store.publish(candidate, parent)
                index.publish(connection, candidate, verified)
            return dict(status="adopted", source_commit=candidate, generation=generation)
    except ERRORS as exc:
        return _diagnostic(exc)


def maintain_history_index(core: Core, *, force: bool = False) -> dict[str, object]:
    """Host-orchestrated preemptive maintenance; never a background Core scheduler."""
    _host(core)
    index = core.history_index
    try:
        with core.store.writer():
            index.ensure(locked=True)
            index.coherent()
            accepted = index.accepted
            if accepted is None:
                index.fail("INDEX_MISSING")
            count = accepted["sequence"] - accepted["base_sequence"]
            size = accepted["tail_bytes"]
            needed = count >= MAINTENANCE_DELTAS or size >= MAINTENANCE_BYTES
            result: dict[str, object] = (
                index.compact() if force or needed else dict(status="healthy")
            )
            result.update(
                maintenance_required=needed,
                deltas_before=count,
                tail_bytes_before=size,
                delta_reserve=MAX_DELTAS if force or needed else MAX_DELTAS - count,
                byte_reserve=MAX_DELTA_BYTES if force or needed else MAX_DELTA_BYTES - size,
                rejection_rule="exact_encoded_delta_must_fit_before_git_publication",
            )
            return result
    except ERRORS as exc:
        return _diagnostic(exc)


def _retained(index: HistoryIndex, payload: dict) -> set[str]:
    """Authenticate a complete retained base/tail before using its reachability."""
    name = payload["base_filename"]
    if not re.fullmatch(r"history-[0-9a-f]{32}\.sqlite3", name):
        index.fail("INDEX_CORRUPT")
    path = index.directory / name
    if path.is_symlink() or path.is_junction():
        index.fail("INDEX_CORRUPT")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != payload["database_sha256"]:
        index.fail("INDEX_CORRUPT")
    connection = index.empty()
    binding = index.binding
    try:
        connection.deserialize(raw)
        index.binding = payload["binding"]
        index._replay_deltas(connection, payload)
    finally:
        index.binding = binding
        connection.close()
    return {name} | {
        index._delta_path(sequence).name
        for sequence in range(payload["base_sequence"] + 1, payload["sequence"] + 1)
    }


def collect_history_index(core: Core, *, apply: bool = False) -> dict[str, object]:
    """Explicit reader-safe derived GC; preserve current and one exact prior anchor."""
    _host(core)
    index = core.history_index
    try:
        with core.store.writer():
            index.ensure(locked=True)
            index.coherent()
            current = index.anchor()
            if current is None:
                index.fail("INDEX_MISSING")
            retained = {name: "current_checkpoint" for name in _retained(index, current)}
            previous = current["base_previous_state"]
            if previous is not None:
                if not re.fullmatch(r"[0-9a-f]{64}", previous):
                    index.fail("INDEX_CORRUPT")
                archive = index.directory / f"checkpoint-{previous}.json"
                raw = archive.read_bytes()
                if hashlib.sha256(raw).hexdigest() != previous:
                    index.fail("INDEX_CORRUPT")
                index.upgrading = True
                try:
                    prior = index.anchor(rebuilding=True, path=archive)
                finally:
                    index.upgrading = False
                if prior is None:
                    index.fail("INDEX_CORRUPT")
                retained.update({name: "prior_checkpoint" for name in _retained(index, prior)})
                retained[archive.name] = "prior_checkpoint"
            candidates = []
            protected = {"checkpoint.json", "checkpoint.key", "enrollment.json"}
            directory = index.directory.resolve()
            if index.directory.is_symlink() or index.directory.is_junction():
                index.fail("INDEX_CORRUPT")
            for path in sorted(index.directory.iterdir()):
                if path.name in retained or path.name in protected:
                    continue
                if path.is_symlink() or path.is_junction() or not path.is_file():
                    retained[path.name] = "unknown_or_link_preserved"
                    continue
                if path.resolve().parent != directory:
                    index.fail("INDEX_CORRUPT")
                recognized = re.fullmatch(
                    r"(?:history-[0-9a-f]{32}\.sqlite3|delta-[0-9]+\.json|checkpoint-[0-9a-f]{64}\.json)(?:\.prepared)?",
                    path.name,
                )
                if recognized:
                    candidates.append((path, path.stat().st_size))
                else:
                    retained[path.name] = "unknown_preserved"
            if (
                core.store.resolve() != index.frontier
                or index.checkpoint.read_bytes() != current["_raw"]
            ):
                index.fail("INDEX_STALE")
            reclaimed = 0
            for path, size in candidates:
                if apply:
                    path.unlink()
                    reclaimed += size
            return dict(
                status="collected" if apply else "planned",
                source_commit=index.frontier,
                candidates=[dict(file=path.name, bytes=size) for path, size in candidates],
                reclaimable_bytes=sum(size for _, size in candidates),
                reclaimed_bytes=reclaimed,
                retained=[
                    dict(file=name, reason=reason) for name, reason in sorted(retained.items())
                ],
            )
    except ERRORS as exc:
        return _diagnostic(exc)
