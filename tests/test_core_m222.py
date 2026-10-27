"""Versioned canonical roots and explicit authenticated projection maintenance."""

import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from conftest import core as core_fixture
from generated.v1.common_schema import GenerationRef
from second_brain_core import (
    Core,
    adopt_generation_commitment,
    audit_history,
    collect_history_index,
    compact_history_index,
    maintain_history_index,
    rebuild_history_index,
    upgrade_history_index,
)
from second_brain_core.boundary import GENERATION
from second_brain_core.codec import encode
from second_brain_core.commitment import SCHEME
from second_brain_core.history_index import PREDECESSOR_CONTRACTS, _json
from test_core_m1 import batch, error, read_node
from test_core_m22 import empowered, update


def restarted(app):
    return Core(app.context, app.store, app.contracts)


def test_generated_generation_consumer_remains_canonically_checked(core):
    app, _ = core
    payload = app.generation()
    validator = app.contracts.validators["common"].evolve(
        schema=app.contracts.schemas["common"]["$defs"]["GenerationRef"]
    )
    validator.validate(payload)
    model = GenerationRef.model_validate(payload)
    assert model.commitment_scheme == SCHEME
    legacy = model.model_dump(mode="json", exclude_unset=True)
    legacy.pop("commitment_scheme")
    validator.validate(legacy)
    assert GenerationRef.model_validate(legacy).commitment_scheme is None


def legacy(tmp_path, contracts, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr("second_brain_core.bootstrap.SCHEME", None)
        app, cluster = core_fixture.__wrapped__(tmp_path, contracts)
    return empowered(app, cluster), cluster


def old_projection(app):
    """Create exact format-3 table/encoding semantics, not a relabeled new database."""
    index = app.history_index
    index.ensure()
    db = sqlite3.connect(":memory:")
    db.deserialize(index.connection.serialize())
    db.executescript(
        "DROP TABLE commitment_leaves; DROP TABLE commitment_nodes; PRAGMA user_version=2;"
    )
    raw = db.serialize()
    db.close()
    binding = dict(index.binding, format=3, contracts=PREDECESSOR_CONTRACTS)
    filename = f"history-{uuid4().hex}.sqlite3"
    (index.directory / filename).write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    sequence = index.accepted["sequence"]
    payload = dict(
        binding=binding,
        commit=index.frontier,
        generation=index.generation,
        database_sha256=sha,
        base_filename=filename,
        base_commit=index.frontier,
        base_generation=index.generation,
        base_sequence=sequence,
        sequence=sequence,
        tail_hash=index._base_state(filename, sha, index.frontier, index.generation, sequence),
        tail_bytes=0,
        base_previous_state=None,
        previous_state=None,
    )
    key = index.key_path.read_bytes()

    def sign(value):
        return _json(dict(payload=value, mac=hmac.digest(key, _json(value), "sha256").hex()))

    index.checkpoint.write_bytes(sign(payload))
    enrollment = json.loads(index.enrollment.read_bytes())["payload"]
    enrollment["binding"] = binding
    index.enrollment.write_bytes(sign(enrollment))
    return filename, index.checkpoint.read_bytes(), key


def test_new_commitment_bounded_update_preserves_old_receipts(core, monkeypatch):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    original = app.submit(creation)
    identifier = creation["operations"][0]["request_id"]
    node = read_node(app, identifier).records[0].root
    assert app.generation()["commitment_scheme"] == SCHEME
    connection = app.history_index.connection
    sql = []
    connection.set_trace_callback(sql.append)
    try:
        app.execute(update(app, node, body="new immutable content"), app.generation())
    finally:
        connection.set_trace_callback(None)
    assert not any("SELECT path,sha FROM files" in query for query in sql)
    assert all(
        "WHERE bucket=" in query
        for query in sql
        if "SELECT path,sha FROM commitment_leaves" in query
    )
    assert app.submit(creation) == original
    assert restarted(app).submit(creation) == original
    assert audit_history(app)["status"] == "verified"


def test_explicit_legacy_adoption_mixed_audit_and_no_downgrade(tmp_path, contracts, monkeypatch):
    app, cluster = legacy(tmp_path, contracts, monkeypatch)
    request = batch(app, cluster)
    original = app.submit(request)
    old = app.generation()
    assert "commitment_scheme" not in old
    result = adopt_generation_commitment(app)
    assert result["status"] == "adopted"
    assert adopt_generation_commitment(app)["status"] == "already_adopted"
    assert app.submit(request) == original
    assert audit_history(app)["status"] == "verified"
    files = app.store.read(app.store.resolve())
    descriptor = app.repository.generation(files)
    parent = app.store.resolve()
    app.store.publish(app.store.prepare_delta({GENERATION: encode(descriptor)}, parent), parent)
    error("REPAIR_REQUIRED", restarted(app).generation)


@pytest.mark.parametrize("fault", ["wrong_root", "hidden_adoption", "unknown_scheme"])
def test_invalid_first_adoption_fails_closed(tmp_path, contracts, monkeypatch, fault):
    app, _ = legacy(tmp_path, contracts, monkeypatch)
    parent = app.store.resolve()
    files = app.store.read(parent)
    generation = app.repository.generation(files, scheme=SCHEME)
    changes = {}
    if fault == "wrong_root":
        generation["digest"]["value"] = "00" * 32
    elif fault == "unknown_scheme":
        generation["commitment_scheme"] = "sha256-bucket16-v0"
    else:
        changes["control/metadata.json"] = (
            b"{}"  # Even otherwise valid content is not adoption-only.
        )
    changes[GENERATION] = encode(generation)
    app.store.publish(app.store.prepare_delta(changes, parent), parent)
    error("REPAIR_REQUIRED", restarted(app).generation)


def test_authenticated_predecessor_upgrade_preserves_key_frontier_and_receipt(
    tmp_path, contracts, monkeypatch
):
    app, cluster = legacy(tmp_path, contracts, monkeypatch)
    request = batch(app, cluster)
    receipt = app.submit(request)
    head = app.store.resolve()
    filename, anchor, key = old_projection(app)
    fresh = restarted(app)
    error("REPAIR_REQUIRED", fresh.generation)
    assert upgrade_history_index(fresh)["status"] == "upgraded"
    assert fresh.store.resolve() == head
    assert fresh.history_index.key_path.read_bytes() == key
    assert fresh.history_index.binding["format"] == 4
    assert (fresh.history_index.directory / filename).exists()
    archive = (
        fresh.history_index.directory / f"checkpoint-{hashlib.sha256(anchor).hexdigest()}.json"
    )
    assert archive.read_bytes() == anchor
    assert fresh.submit(request) == receipt
    assert "commitment_scheme" not in fresh.generation()  # Upgrade does not silently adopt.
    assert adopt_generation_commitment(fresh)["status"] == "adopted"
    assert restarted(fresh).submit(request) == receipt


@pytest.mark.parametrize("point", ["base", "archive", "checkpoint", "enrollment"])
def test_upgrade_interruption_retains_recoverable_anchor(tmp_path, contracts, monkeypatch, point):
    import second_brain_core.history_index as module

    app, _ = legacy(tmp_path, contracts, monkeypatch)
    _, old, key = old_projection(app)
    original = module._atomic

    def interrupted(path, raw):
        match = (
            (point == "base" and path.name.startswith("history-"))
            or (point == "archive" and path.name.startswith("checkpoint-"))
            or (point == "checkpoint" and path.name == "checkpoint.json")
            or (point == "enrollment" and path.name == "enrollment.json")
        )
        if match:
            raise OSError("injected upgrade interruption")
        original(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", interrupted)
        assert upgrade_history_index(restarted(app))["status"] == "repair_required"
    assert app.history_index.key_path.read_bytes() == key
    if point != "enrollment":
        assert app.history_index.checkpoint.read_bytes() == old
    fresh = restarted(app)
    assert upgrade_history_index(fresh)["status"] == "upgraded"
    assert fresh.generation() == app.generation()


def test_capacity_preflight_gc_retention_and_repeatability(core, monkeypatch):
    import second_brain_core.maintenance as module

    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    initial = app.history_index.database
    with monkeypatch.context() as patch:
        patch.setattr(module, "MAINTENANCE_DELTAS", 1)
        report = maintain_history_index(app)
    assert report["status"] == "compacted" and report["delta_reserve"] == 1024
    assert initial.exists()  # Current checkpoint retains one complete previous state.
    assert compact_history_index(app)["status"] == "compacted"
    unknown = app.history_index.directory / "operator-notes.txt"
    unknown.write_text("preserved", encoding="utf-8")
    head = app.store.resolve()
    plan = collect_history_index(app)
    assert plan["status"] == "planned" and plan["reclaimable_bytes"] > 0
    assert initial.name in {item["file"] for item in plan["candidates"]}
    assert initial.exists()  # Dry run performs no removal.
    result = collect_history_index(app, apply=True)
    assert result["status"] == "collected" and result["reclaimed_bytes"] > 0
    assert not initial.exists() and unknown.exists()
    assert collect_history_index(app, apply=True)["reclaimed_bytes"] == 0
    assert app.store.resolve() == head and restarted(app).submit(request) == receipt
    assert audit_history(app)["status"] == "verified"


@pytest.mark.parametrize("fault", ["key", "checkpoint", "archive", "base"])
def test_gc_missing_or_corrupt_trust_never_deletes(core, fault):
    app, _ = core
    assert compact_history_index(app)["status"] == "compacted"
    index = app.history_index
    if fault == "key":
        index.key_path.unlink()
    elif fault == "checkpoint":
        index.checkpoint.unlink()
    elif fault == "archive":
        (index.directory / f"checkpoint-{index.accepted['base_previous_state']}.json").unlink()
    else:
        index.database.write_bytes(b"corrupt base")
    before = {p.name: p.read_bytes() for p in index.directory.iterdir() if p.is_file()}
    assert collect_history_index(app, apply=True)["status"] == "repair_required"
    assert before == {p.name: p.read_bytes() for p in index.directory.iterdir() if p.is_file()}


@pytest.mark.parametrize(
    "action",
    [
        adopt_generation_commitment,
        upgrade_history_index,
        maintain_history_index,
        collect_history_index,
    ],
)
def test_maintenance_requires_trusted_host(core, action):
    app, _ = core
    principal = replace(app.context.principal, bootstrap=False)
    untrusted = Core(replace(app.context, principal=principal), app.store, app.contracts)
    error("FORBIDDEN", lambda: action(untrusted))


def test_gc_interruption_preserves_reachable_state_and_reruns(core, monkeypatch):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    for _ in range(3):
        assert compact_history_index(app)["status"] == "compacted"
    original = Path.unlink
    deleted = []

    def interrupted(path, *args, **kwargs):
        if path.parent == app.history_index.directory:
            if deleted:
                raise OSError("interrupted derived cleanup")
            deleted.append(path)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        assert collect_history_index(app, apply=True)["status"] == "repair_required"
    assert deleted and not deleted[0].exists()
    assert restarted(app).submit(request) == receipt
    assert collect_history_index(app, apply=True)["status"] == "collected"
    assert collect_history_index(app, apply=True)["reclaimed_bytes"] == 0


def test_partial_derived_backup_needs_rebuild_without_trust_reset(core):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    vault = app.context.repository / "unmanaged human note.md"
    vault.write_bytes(b"offline human bytes\r\n")
    assert compact_history_index(app)["status"] == "compacted"
    with app.store.writer():
        backup = {
            path.name: path.read_bytes()
            for path in app.history_index.directory.iterdir()
            if path.is_file()
        }
    key = app.history_index.key_path.read_bytes()
    app.history_index.database.unlink()  # A partial derived-file backup is not usable.
    error("REPAIR_REQUIRED", restarted(app).generation)
    recovered = restarted(app)
    assert rebuild_history_index(recovered)["status"] == "rebuilt"
    assert recovered.history_index.key_path.read_bytes() == key
    assert recovered.submit(request) == receipt
    assert vault.read_bytes() == b"offline human bytes\r\n"
    assert backup["checkpoint.key"] == key
    assert audit_history(recovered)["status"] == "verified"


def test_cross_process_cold_reader_and_gc_are_serialized(core, tmp_path):
    app, cluster = core
    app.submit(batch(app, cluster))
    ready, release, queued = (
        tmp_path / name for name in ("reader-ready", "release-reader", "gc-queued")
    )
    context = dict(
        instance=app.context.instance_id,
        repository=str(app.context.repository),
        ref=app.context.managed_ref,
        principal=app.context.principal.principal_id,
        grants=list(app.context.principal.grants),
        packages=str(Path(__file__).resolve().parents[1] / "packages/python"),
    )
    script = r"""
import json,sys,time
from pathlib import Path
c=json.loads(sys.argv[1]);sys.path.insert(0,c['packages'])
from second_brain_core import Core,GitStore,InstanceContext,TrustedPrincipal,compact_history_index,collect_history_index
app=Core(InstanceContext(c['instance'],Path(c['repository']),c['ref'],TrustedPrincipal(c['principal'],frozenset(map(tuple,c['grants'])),True)),GitStore(c['repository'],c['ref']))
if sys.argv[2]=='reader':
    original=app.history_index.anchor
    def pinned(*args,**kwargs):
        payload=original(*args,**kwargs)
        Path(sys.argv[3]).write_text('pinned',encoding='utf-8')
        deadline=time.monotonic()+30
        while not Path(sys.argv[4]).exists():
            if time.monotonic()>deadline: raise RuntimeError('reader release timeout')
            time.sleep(.02)
        return payload
    app.history_index.anchor=pinned
    app.generation()
    print('reader-ok',flush=True)
else:
    Path(sys.argv[3]).write_text('queued',encoding='utf-8')
    result=compact_history_index(app)
    assert result['status']=='compacted', result
    result=compact_history_index(app)
    assert result['status']=='compacted', result
    result=collect_history_index(app,apply=True)
    assert result['status']=='collected', result
    print('gc-ok',flush=True)
"""

    def wait_file(path, child):
        deadline = time.monotonic() + 30
        while not path.exists():
            if child.poll() is not None:
                pytest.fail(str(child.communicate()))
            assert time.monotonic() < deadline
            time.sleep(0.02)

    reader = subprocess.Popen(
        [sys.executable, "-c", script, json.dumps(context), "reader", str(ready), str(release)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    collector = None
    try:
        wait_file(
            ready, reader
        )  # Actual load has read its signed checkpoint while holding the lock.
        collector = subprocess.Popen(
            [sys.executable, "-c", script, json.dumps(context), "gc", str(queued)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        wait_file(queued, collector)
        assert collector.poll() is None
        release.write_text("continue", encoding="utf-8")
        reader_out = reader.communicate(timeout=30)
        gc_out = collector.communicate(timeout=30)
        assert reader.returncode == 0 and "reader-ok" in reader_out[0], reader_out
        assert collector.returncode == 0 and "gc-ok" in gc_out[0], gc_out
    finally:
        release.touch(exist_ok=True)
        for child in (reader, collector):
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate()
    assert audit_history(restarted(app))["status"] == "verified"


@pytest.mark.skipif(os.name != "nt", reason="Windows byte-lock initialization race")
def test_windows_fresh_lock_initialization_race(tmp_path):
    lock, start, log = (tmp_path / name for name in ("fresh.lock", "start", "entries"))
    ready = [tmp_path / f"ready-{number}" for number in range(2)]
    packages = Path(__file__).resolve().parents[1] / "packages/python"
    script = r"""
import os,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from second_brain_core.locking import writer_lock
original=os.fstat; observed=False
def stat(fd):
    global observed
    result=original(fd)
    if not observed and result.st_size==0:
        observed=True
        Path(sys.argv[3]).write_text('empty',encoding='utf-8')
        deadline=time.monotonic()+20
        while not Path(sys.argv[4]).exists():
            if time.monotonic()>deadline: raise RuntimeError('barrier timeout')
            time.sleep(.02)
    return result
os.fstat=stat
with writer_lock(Path(sys.argv[2])):
    with Path(sys.argv[5]).open('a',encoding='utf-8') as out:
        out.write('start'+sys.argv[6]+'\n');out.flush()
        time.sleep(.1)
        out.write('end'+sys.argv[6]+'\n');out.flush()
print('ok',flush=True)
"""
    children = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(packages),
                str(lock),
                str(ready[number]),
                str(start),
                str(log),
                str(number),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for number in range(2)
    ]
    try:
        deadline = time.monotonic() + 30
        while not all(path.exists() for path in ready):
            assert all(child.poll() is None for child in children)
            assert time.monotonic() < deadline
            time.sleep(0.02)
        start.touch()
        for child in children:
            output = child.communicate(timeout=20)
            assert child.returncode == 0 and "ok" in output[0], output
    finally:
        start.touch(exist_ok=True)
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate()
    entries = log.read_text(encoding="utf-8").splitlines()
    assert entries in (["start0", "end0", "start1", "end1"], ["start1", "end1", "start0", "end0"])
