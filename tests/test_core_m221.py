"""Authenticated bounded projection advancement with disposable real Git."""

import hashlib
import hmac
import json
import sqlite3
from dataclasses import replace

import pytest
from second_brain_core import Core, audit_history, compact_history_index, rebuild_history_index
from second_brain_core.git_store import PublicationConflict
from second_brain_core.history_index import _json
from second_brain_core.projection import ProjectionConnection
from test_core_m1 import batch, error, read_node
from test_core_m22 import empowered, update


def restart(app):
    return Core(app.context, app.store, app.contracts)


def prepared(core):
    app, cluster = core
    app = empowered(app, cluster)
    request = batch(app, cluster)
    receipt = app.submit(request)
    node = read_node(app, request["operations"][0]["request_id"]).records[0].root
    return app, cluster, request, receipt, node


def advance(app, node, body="new revision"):
    request = update(app, node, body=body)
    generation = app.generation()
    receipt = app.execute(request, generation)
    return request, generation, receipt


def sign(path, envelope, key):
    envelope["mac"] = hmac.digest(key, _json(envelope["payload"]), "sha256").hex()
    path.write_bytes(_json(envelope))


def test_warm_update_persists_only_bounded_delta(core, monkeypatch):
    import second_brain_core.history_index as module

    app, _, _, _, node = prepared(core)
    base = app.history_index.database.read_bytes()
    changed_before = app.history_index.connection.total_changes
    writes = []
    original, sha = module._atomic, hashlib.sha256

    def atomic(path, raw):
        writes.append((path.name, len(raw)))
        assert not raw.startswith(b"SQLite format 3")
        original(path, raw)

    def hashed(raw=b"", **kwargs):
        assert not raw.startswith(b"SQLite format 3"), "full projection hash"
        return sha(raw, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail("whole projection/history operation on bounded update")

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", atomic)
        patch.setattr(hashlib, "sha256", hashed)
        patch.setattr(ProjectionConnection, "serialize", forbidden)
        for owner, names in (
            (app.store, ("read", "entries", "ancestry")),
            (app.history_index, ("fork", "rebuild", "load")),
        ):
            for name in names:
                patch.setattr(owner, name, forbidden)
        advance(app, node)
    assert len(writes) == 2
    assert writes[0][0].startswith("delta-") and writes[1][0] == "checkpoint.json"
    assert sum(size for _, size in writes) < 20000
    assert app.history_index.database.read_bytes() == base
    delta = json.loads(
        app.history_index._delta_path(app.history_index.accepted["sequence"]).read_bytes()
    )
    # M2.2.2 adds bounded commitment rows. Preserve the original domain-work
    # budget independently rather than treating the extra tree rows as free work.
    commitment_writes = [item for item in delta["payload"]["writes"] if "commitment_" in item[0]]
    assert len(delta["payload"]["writes"]) - len(commitment_writes) <= 26
    assert (
        len(commitment_writes) <= 3 * 18
    )  # Three changed content paths, <=17 nodes plus leaf each.
    assert app.history_index.connection.total_changes - changed_before == 19 + len(
        commitment_writes
    )
    assert read_node(restart(app), node.id.root).records[0].root.revision.root == 2


@pytest.mark.parametrize(
    "case", ["missing_first", "missing_last", "truncate", "reorder", "duplicate"]
)
def test_complete_anchored_tail_required(core, case):
    app, _, request, _, node = prepared(core)
    advance(app, node)
    index = app.history_index
    first, last = index._delta_path(1), index._delta_path(2)
    if case.startswith("missing"):
        (first if case == "missing_first" else last).unlink()
    elif case == "truncate":
        last.write_bytes(last.read_bytes()[:70])
    elif case == "reorder":
        raw = first.read_bytes()
        first.write_bytes(last.read_bytes())
        last.write_bytes(raw)
    else:
        last.write_bytes(first.read_bytes())
    head, anchor = app.store.resolve(), index.checkpoint.read_bytes()
    error("REPAIR_REQUIRED", restart(app).generation)
    error("REPAIR_REQUIRED", lambda: restart(app).submit(request))
    assert app.store.resolve() == head and index.checkpoint.read_bytes() == anchor
    assert rebuild_history_index(restart(app))["status"] == "rebuilt"


@pytest.mark.parametrize("case", ["statement", "arity", "instance", "ref", "contracts"])
def test_signed_delta_still_requires_fixed_vocabulary_and_binding(core, case):
    app, _, _, _, _ = prepared(core)
    index = app.history_index
    path = index._delta_path(1)
    raw = path.read_bytes()
    delta = json.loads(raw)
    if case == "statement":
        delta["payload"]["writes"][0] = ["DELETE FROM memberships", []]
    elif case == "arity":
        delta["payload"]["writes"][0][1] = []
    else:
        delta["payload"]["binding"][case] = "foreign"
    sign(path, delta, index.key_path.read_bytes())
    checkpoint = json.loads(index.checkpoint.read_bytes())
    checkpoint["payload"]["tail_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
    checkpoint["payload"]["tail_bytes"] += len(path.read_bytes()) - len(raw)
    sign(index.checkpoint, checkpoint, index.key_path.read_bytes())
    error("REPAIR_REQUIRED", restart(app).generation)


@pytest.mark.parametrize("table", ["memberships", "receipts", "operation_keys"])
def test_removed_base_rows_never_change_authenticated_absence(core, table):
    app, _, request, receipt, node = prepared(core)
    assert compact_history_index(app)["status"] == "compacted"
    connection = sqlite3.connect(app.history_index.database)
    connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()
    head = app.store.resolve()
    assert app.submit(request) == receipt
    assert app.store.resolve() == head
    denied = Core(
        replace(app.context, principal=replace(app.context.principal, grants=frozenset())),
        app.store,
        app.contracts,
    )
    error("REPAIR_REQUIRED", denied.generation)
    error("REPAIR_REQUIRED", restart(app).generation)
    assert read_node(app, node.id.root).records[0].root.id.root == node.id.root
    assert rebuild_history_index(app)["status"] == "rebuilt"
    assert app.submit(request) == receipt


@pytest.mark.parametrize(
    "point", ["git", "delta", "partial_delta", "checkpoint", "after_checkpoint"]
)
def test_mutation_interruption_boundaries(core, monkeypatch, point):
    import second_brain_core.history_index as module

    app, _, _, _, node = prepared(core)
    request, generation = update(app, node, body=point), app.generation()
    head, checkpoint = app.store.resolve(), app.history_index.checkpoint.read_bytes()
    original = module._atomic
    publication = app.store.publish

    def atomic(path, raw):
        if path.name.startswith("delta-") and point in ("delta", "partial_delta"):
            if point == "partial_delta":
                path.write_bytes(raw[:80])
            raise OSError("simulated delta interruption")
        if path == app.history_index.checkpoint and point == "checkpoint":
            raise OSError("simulated checkpoint interruption")
        original(path, raw)
        if path == app.history_index.checkpoint and point == "after_checkpoint":
            raise OSError("response interrupted after accepted checkpoint")

    def publish(*args):
        if point == "git":
            raise PublicationConflict("simulated CAS loss")
        publication(*args)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", atomic)
        patch.setattr(app.store, "publish", publish)
        error(
            "REVISION_CONFLICT" if point == "git" else "REPAIR_REQUIRED",
            lambda: app.execute(request, generation),
        )
    assert app.history_index.connection is None
    if point == "git":
        assert app.store.resolve() == head
        assert app.history_index.checkpoint.read_bytes() == checkpoint
        assert read_node(app, node.id.root).records[0].root.revision.root == 1
        return
    committed = app.store.resolve()
    assert committed != head
    recovered = restart(app)
    receipt = recovered.execute(request, generation)
    assert recovered.execute(request, generation) == receipt
    assert recovered.store.resolve() == committed
    assert read_node(recovered, node.id.root).records[0].root.revision.root == 2


@pytest.mark.parametrize("point", ["SAVEPOINT", "INSERT INTO commits"])
def test_sqlite_transaction_failure_never_advances_git(core, monkeypatch, point):
    app, _, _, _, node = prepared(core)
    request, generation = update(app, node), app.generation()
    head = app.store.resolve()
    original = ProjectionConnection.execute

    def execute(self, sql, parameters=(), /):
        if sql.startswith(point):
            raise sqlite3.OperationalError("simulated transaction interruption")
        return original(self, sql, parameters)

    with monkeypatch.context() as patch:
        patch.setattr(ProjectionConnection, "execute", execute)
        error("REPAIR_REQUIRED", lambda: app.execute(request, generation))
    assert app.store.resolve() == head
    assert not app.history_index.in_candidate
    assert app.history_index.connection is None
    assert read_node(app, node.id.root).records[0].root.revision.root == 1


@pytest.mark.parametrize("point", ["base", "checkpoint", "after_checkpoint"])
def test_compaction_interruption_keeps_old_base_and_accepted_git(core, monkeypatch, point):
    import second_brain_core.history_index as module

    app, _, request, receipt, _ = prepared(core)
    index = app.history_index
    old_base, raw = index.database, index.database.read_bytes()
    head = app.store.resolve()
    original = module._atomic

    def atomic(path, value):
        if point == "base" and path.suffix == ".sqlite3":
            raise OSError("new base preparation interrupted")
        if point == "checkpoint" and path == index.checkpoint:
            raise OSError("checkpoint switch interrupted")
        original(path, value)
        if point == "after_checkpoint" and path == index.checkpoint:
            raise OSError("compaction response interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", atomic)
        assert compact_history_index(app)["status"] == "repair_required"
    assert old_base.read_bytes() == raw and app.store.resolve() == head
    assert restart(app).submit(request) == receipt
    assert compact_history_index(restart(app))["status"] == "compacted"


@pytest.mark.parametrize("limit", ["count", "bytes"])
def test_capacity_rejects_before_git_and_explicit_compaction_restores_capacity(
    core, monkeypatch, limit
):
    import second_brain_core.history_index as module

    app, _, request, receipt, node = prepared(core)
    update_request, generation = update(app, node), app.generation()
    head = app.store.resolve()
    with monkeypatch.context() as patch:
        patch.setattr(
            module,
            "MAX_DELTAS" if limit == "count" else "MAX_DELTA_BYTES",
            1 if limit == "count" else app.history_index.accepted["tail_bytes"] + 1,
        )
        assert app.submit(request) == receipt
        error("REPAIR_REQUIRED", lambda: app.execute(update_request, generation))
        assert app.store.resolve() == head
    assert compact_history_index(app)["status"] == "compacted"
    assert app.history_index.accepted["sequence"] == app.history_index.accepted["base_sequence"]
    app.execute(update_request, generation)
    assert read_node(app, node.id.root).records[0].root.revision.root == 2


def test_tentative_rows_cannot_escape_to_reentrant_read(core, monkeypatch):
    app, _, _, _, node = prepared(core)
    other = restart(app)
    old_generation = other.generation()
    publication = app.store.publish

    def publish(*args):
        error("REPAIR_REQUIRED", lambda: read_node(app, node.id.root))
        assert other.generation() == old_generation
        return publication(*args)

    monkeypatch.setattr(app.store, "publish", publish)
    advance(app, node)
    assert read_node(other, node.id.root).records[0].root.revision.root == 2


def test_untrusted_wal_sidecars_are_never_consumed(core):
    app, _, request, receipt, _ = prepared(core)
    database = app.history_index.database
    database.with_name(database.name + "-wal").write_bytes(b"corrupt SQLite WAL")
    database.with_name(database.name + "-shm").write_bytes(b"truncated shared memory")
    assert restart(app).submit(request) == receipt


@pytest.mark.parametrize("change", ["key", "same_commit_checkpoint"])
def test_external_anchor_change_after_git_cannot_be_signed(core, monkeypatch, change):
    app, _, _, _, node = prepared(core)
    index = app.history_index
    old_checkpoint, key = index.checkpoint.read_bytes(), index.key_path.read_bytes()
    assert compact_history_index(app)["status"] == "compacted"
    current_checkpoint = index.checkpoint.read_bytes()
    assert current_checkpoint != old_checkpoint
    request, generation = update(app, node), app.generation()
    publication = app.store.publish

    def publish(*args):
        publication(*args)
        if change == "key":
            index.key_path.write_bytes(b"x" * 32)
        else:
            index.checkpoint.write_bytes(old_checkpoint)

    with monkeypatch.context() as patch:
        patch.setattr(app.store, "publish", publish)
        error("REPAIR_REQUIRED", lambda: app.execute(request, generation))
    assert index.connection is None
    assert index.checkpoint.read_bytes() == (
        current_checkpoint if change == "key" else old_checkpoint
    )
    if change == "key":
        error("REPAIR_REQUIRED", restart(app).generation)
        assert rebuild_history_index(restart(app))["code"] == "VERIFICATION_FAILED"
        # Disposable operator restores the original protected key; production never
        # reenrolls or invents a replacement key to recover this condition.
        index.key_path.write_bytes(key)
    receipt = restart(app).execute(request, generation)
    assert receipt.results[0].revisions[0].revision.root == 2


def test_external_catchup_over_capacity_requires_explicit_rebuild(core, monkeypatch):
    import second_brain_core.history_index as module

    app, _, _, _, node = prepared(core)
    other = restart(app)
    request, generation = update(other, node), other.generation()
    atomic = module._atomic

    def interrupted(path, raw):
        if path.name.startswith("delta-"):
            raise OSError("Git committed without derived advancement")
        atomic(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", interrupted)
        error("REPAIR_REQUIRED", lambda: other.execute(request, generation))
    committed, checkpoint = app.store.resolve(), app.history_index.checkpoint.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(module, "MAX_DELTAS", 1)
        error("REPAIR_REQUIRED", app.generation)
    assert app.store.resolve() == committed
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    assert rebuild_history_index(app)["status"] == "rebuilt"
    assert app.execute(request, generation).results[0].revisions[0].revision.root == 2


def test_alternating_warm_writers_refresh_only_new_authenticated_delta(core, monkeypatch):
    app, _, _, _, node = prepared(core)
    other = restart(app)
    other.generation()
    original = hashlib.sha256
    connection = app.history_index.connection
    other_connection = other.history_index.connection

    def forbidden(*args, **kwargs):
        pytest.fail("alternating warm writer reloaded/copied the full projection")

    def hashed(raw=b"", **kwargs):
        assert not raw.startswith(b"SQLite format 3")
        return original(raw, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", hashed)
        patch.setattr(ProjectionConnection, "serialize", forbidden)
        patch.setattr(ProjectionConnection, "deserialize", forbidden)
        for client in (app, other):
            for name in ("load", "fork", "rebuild"):
                patch.setattr(client.history_index, name, forbidden)
            for name in ("read", "entries", "ancestry"):
                patch.setattr(client.store, name, forbidden)
        for position, client in enumerate((app, other, app, other)):
            current = read_node(client, node.id.root).records[0].root
            advance(client, current, body=f"alternating {position}")
    assert app.history_index.connection is connection
    assert other.history_index.connection is other_connection
    assert read_node(app, node.id.root).records[0].root.revision.root == 5


def test_noncanonical_checkpoint_cannot_produce_unreplayable_delta(core):
    app, _, _, _, node = prepared(core)
    index = app.history_index
    head = app.store.resolve()
    envelope = json.loads(index.checkpoint.read_bytes())
    index.checkpoint.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    error("REPAIR_REQUIRED", lambda: advance(app, node))
    assert app.store.resolve() == head
    # Explicit operator restores the same signed payload's canonical bytes.
    index.checkpoint.write_bytes(_json(envelope))
    advance(app, node)
    assert read_node(restart(app), node.id.root).records[0].root.revision.root == 2


def test_compaction_requires_trusted_host_before_private_access(core, monkeypatch):
    app, _, _, _, _ = prepared(core)
    denied = Core(
        replace(app.context, principal=replace(app.context.principal, bootstrap=False)),
        app.store,
        app.contracts,
    )
    head, checkpoint = app.store.resolve(), app.history_index.checkpoint.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("unauthorized maintenance touched private projection")

    monkeypatch.setattr(denied.history_index, "compact", forbidden)
    error("FORBIDDEN", lambda: compact_history_index(denied))
    assert app.store.resolve() == head
    assert app.history_index.checkpoint.read_bytes() == checkpoint


def test_git_batch_hashing_is_exact_and_bounds_windows_arguments(core, monkeypatch):
    app, _ = core
    parent = app.store.resolve()
    raw = "Unicode Україна\r\nexact bytes\r\n".encode()
    app.store.run("config", "core.autocrlf", "true")
    files = {f"knowledge/test/{position}.bin": raw for position in range(250)}
    run, calls = app.store._run_bytes, []

    def tracked(*args, **kwargs):
        if args[0] == "hash-object":
            calls.append(args)
            assert "--no-filters" in args
            assert sum(len(arg) + 3 for arg in args) < 12500
        return run(*args, **kwargs)

    monkeypatch.setattr(app.store, "_run_bytes", tracked)
    candidate = app.store.prepare_delta(files, parent)
    assert len(calls) >= 2
    entries = app.store.entries(candidate)
    oids = {entries[path] for path in files}
    assert len(oids) == 1
    assert app.store.blobs(list(oids)) == dict.fromkeys(oids, raw)
    assert app.store.resolve() == parent


def test_warm_refresh_corrupt_json_is_repair_required_on_submit(core):
    app, _, request, _, node = prepared(core)
    other = restart(app)
    advance(other, node)
    other.history_index._delta_path(2).write_bytes(b"{")
    head = app.store.resolve()
    error("REPAIR_REQUIRED", lambda: app.submit(request))
    assert app.store.resolve() == head and app.history_index.connection is None


@pytest.mark.parametrize(
    "damage,expected",
    [
        ("healthy", "OK"),
        ("base_corrupt", "INDEX_CORRUPT"),
        ("base_missing", "INDEX_MISSING"),
        ("tail_corrupt", "INDEX_CORRUPT"),
        ("tail_missing", "INDEX_CORRUPT"),
    ],
)
def test_cold_audit_uses_authenticated_base_and_tail_without_prior_load(core, damage, expected):
    app, _, _, _, _ = prepared(core)
    index = app.history_index
    if damage == "base_corrupt":
        index.database.write_bytes(b"corrupt SQLite projection")
    elif damage == "base_missing":
        index.database.unlink()
    elif damage == "tail_corrupt":
        index._delta_path(1).write_bytes(b"corrupt accepted tail")
    elif damage == "tail_missing":
        index._delta_path(1).unlink()
    head = app.store.resolve()
    files = {path.name: path.read_bytes() for path in index.directory.iterdir() if path.is_file()}
    cold = restart(app)
    assert cold.history_index.connection is None
    assert cold.history_index.database.name == "history.sqlite3"
    result = audit_history(cold)
    assert result["status"] == "verified"
    assert result["index_status"] == expected
    assert app.store.resolve() == head
    assert {
        path.name: path.read_bytes() for path in index.directory.iterdir() if path.is_file()
    } == files
