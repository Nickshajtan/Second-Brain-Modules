"""Authenticated projections, ordered integrity and bounded canonical deliveries."""

import copy
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from dataclasses import replace

import pytest
from second_brain_core import (
    Core,
    CoreError,
    GitStore,
    TrustedPrincipal,
    audit_history,
    rebuild_history_index,
)
from second_brain_core.boundary import GENERATION
from second_brain_core.codec import decode, encode
from test_core_m1 import batch, error, operation, read_node, uid
from test_core_m21_history import publish


def restart(app, context=None):
    context = context or app.context
    return Core(context, GitStore(context.repository, context.managed_ref), app.contracts)


def change_sql(path, statement, parameters=()):
    connection = sqlite3.connect(path)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()


def test_warm_deliveries_are_targeted_and_restart_is_authenticated(core, monkeypatch):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    for _ in range(5):
        app.submit(batch(app, cluster))
    assert app.history_index.query("SELECT count(*) FROM resources")[0][0] > 40
    app = restart(app)
    app.generation()  # Authenticate/deserialise once; no ancestry scan.
    counts = dict(blobs=0, records=0)
    original_blobs, original_parse = app.store.blobs, app.contracts.parse

    def blobs(oids):
        counts["blobs"] += len(oids)
        return original_blobs(oids)

    def parse(family, payload):
        counts["records"] += 1
        return original_parse(family, payload)

    def forbidden(*args, **kwargs):
        pytest.fail("warm lookup performed full-tree/history work")

    monkeypatch.setattr(app.store, "read", forbidden)
    monkeypatch.setattr(app.store, "entries", forbidden)
    monkeypatch.setattr(app.store, "ancestry", forbidden)
    monkeypatch.setattr(app.store, "changes", forbidden)
    monkeypatch.setattr(app.store, "blobs", blobs)
    monkeypatch.setattr(app.contracts, "parse", parse)
    identifier = request["operations"][0]["request_id"]
    read_node(app, identifier)
    assert counts["blobs"] <= 12 and counts["records"] <= 12
    counts.update(blobs=0, records=0)
    relation = request["operations"][2]["payload"]["relation"]["id"]
    app.read(operation(app, "relation.read", {"relation_id": relation}))
    assert counts["blobs"] <= 24 and counts["records"] <= 24
    counts.update(blobs=0, records=0)
    assert app.submit(request) == receipt
    assert counts["blobs"] <= 80 and counts["records"] <= 40


def test_warm_create_verifies_only_its_new_transition_and_receipt(core, monkeypatch):
    app, cluster = core
    for _ in range(6):
        app.submit(batch(app, cluster))
    assert app.history_index.query("SELECT count(*) FROM receipts")[0][0] == 6
    request = batch(app, cluster)
    parent = app.store.resolve()
    expected_receipt = app.receipts.for_request(request)
    pairs, transitions = [], []
    original_pair = app.receipts.validate_pair
    original_changes = app.store.changes

    def forbidden(*args, **kwargs):
        pytest.fail("warm create scanned the full tree or historical effects")

    def validate_pair(path, files):
        pairs.append(path)
        assert path == expected_receipt
        return original_pair(path, files)

    def changes(start, end):
        assert start == parent
        result = original_changes(start, end)
        assert len(result) == 1
        transitions.extend(result)
        return result

    monkeypatch.setattr(app.store, "read", forbidden)
    monkeypatch.setattr(app.store, "entries", forbidden)
    monkeypatch.setattr(app.store, "ancestry", forbidden)
    monkeypatch.setattr(app.receipts.history, "validate", forbidden)
    monkeypatch.setattr(app.receipts, "validate_pair", validate_pair)
    monkeypatch.setattr(app.store, "changes", changes)
    receipt = app.submit(request)
    assert len(receipt.results) == 3
    assert pairs == [expected_receipt]
    assert len(transitions) == 1
    assert transitions[0][0] == app.store.resolve() != parent
    assert app.history_index.query("SELECT count(*) FROM receipts")[0][0] == 7


@pytest.mark.parametrize("table", ["memberships", "receipts", "operation_keys", "commits"])
def test_restored_stat_row_deletion_cannot_change_trusted_memory_or_restart(core, table):
    from second_brain_core import compact_history_index

    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    assert compact_history_index(app)["status"] == "compacted"
    path = app.history_index.database
    before = path.stat()
    change_sql(path, f"DELETE FROM {table}")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    # Warm delivery uses the authenticated private DB, never mutable disk rows.
    read_node(app, request["operations"][0]["request_id"])
    error("REPAIR_REQUIRED", restart(app).generation)
    # Publication no longer hashes old base bytes. Exact replay still uses the
    # complete authenticated private set; it cannot rerun a missing disk row.
    assert app.submit(request) == receipt
    assert app.store.resolve() == app.history_index.frontier
    assert rebuild_history_index(app)["status"] == "rebuilt"
    assert app.submit(request) == receipt


@pytest.mark.parametrize("defect", ["missing", "truncated", "wrong_generation", "wrong_commit"])
def test_rebuildable_projection_damage_preserves_canonical_knowledge(core, defect):
    from second_brain_core import compact_history_index

    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    assert compact_history_index(app)["status"] == "compacted"
    source = app.store.resolve()
    path = app.history_index.database
    if defect == "missing":
        path.unlink()
    elif defect == "truncated":
        path.write_bytes(b"SQLite format 3\0partial")
    elif defect == "wrong_generation":
        change_sql(
            path,
            "UPDATE commits SET generation=? WHERE oid=?",
            (json.dumps({"generation_id": uid()}), source),
        )
    else:
        change_sql(path, "UPDATE receipts SET origin=?", ("0" * 40,))
    error("REPAIR_REQUIRED", restart(app).generation)
    assert rebuild_history_index(app)["status"] == "rebuilt"
    assert app.store.resolve() == source
    assert app.submit(request) == receipt
    assert audit_history(app)["index_status"] == "OK"


def test_wrong_instance_checkpoint_and_maintenance_authority(core):
    app, cluster = core
    app.submit(batch(app, cluster))
    foreign = restart(app, replace(app.context, instance_id=uid()))
    error("REPAIR_REQUIRED", foreign.generation)
    denied = restart(app, replace(app.context, principal=TrustedPrincipal(uid(), frozenset())))
    error("FORBIDDEN", lambda: audit_history(denied))
    error("FORBIDDEN", lambda: rebuild_history_index(denied))
    hidden = next(
        row[0] for row in app.history_index.query("SELECT id FROM resources WHERE kind='node'")
    )
    error("NOT_FOUND", lambda: read_node(denied, hidden))


def test_backward_ref_and_entire_intermediate_transaction_deletion_fail_closed(core):
    app, cluster = core
    root = app.store.resolve()
    request = batch(app, cluster)
    app.submit(request)
    accepted = app.store.resolve()
    app.store.publish(root, accepted)
    error("REPAIR_REQUIRED", app.generation)
    assert audit_history(app)["code"] == "MISSING_ANCESTOR"
    app.store.publish(accepted, root)
    original = app.store.read(accepted)
    broken = {
        path: raw
        for path, raw in original.items()
        if not path.startswith(
            (
                "knowledge/node/",
                "knowledge/node_revision/",
                "knowledge/membership/",
                "knowledge/relation/",
                "knowledge/relation_revision/",
                "control/requests/",
                "control/receipts/",
            )
        )
    }
    publish(app, broken)
    publish(app, dict(original))
    error("REPAIR_REQUIRED", app.generation)
    assert rebuild_history_index(app)["status"] == "repair_required"


@pytest.mark.parametrize(
    "defect", ["cluster", "node", "definition", "membership_repoint", "second_membership"]
)
def test_reverse_dependency_transition_is_not_hidden_by_targeted_validation(core, defect):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    files = app.store.read(app.store.resolve())
    if defect == "cluster":
        del files[f"knowledge/cluster/{cluster}.yaml"]
    elif defect == "node":
        del files[f"knowledge/node/{request['operations'][0]['request_id']}.yaml"]
    elif defect == "definition":
        del files[next(p for p in files if p.startswith("knowledge/node_type_definition/"))]
    else:
        path = next(p for p in files if p.startswith("knowledge/membership/"))
        record = decode(files[path])
        if defect == "membership_repoint":
            record["node_id"] = next(
                op["request_id"]
                for op in request["operations"][:2]
                if op["request_id"] != record["node_id"]
            )
        else:
            record["id"] = uid()
            path = f"knowledge/membership/{record['id']}.yaml"
        files[path] = encode(record)
    publish(app, files)
    error("REPAIR_REQUIRED", app.generation)


@pytest.mark.parametrize("boundary", ["before_delta", "before_checkpoint"])
def test_published_git_survives_projection_failure_and_explicit_recovery(
    core, monkeypatch, boundary
):
    import second_brain_core.history_index as module

    app, cluster = core
    request = batch(app, cluster)
    source = app.store.resolve()
    atomic = module._atomic

    def interrupted(path, raw):
        target = (
            app.history_index._delta_path(1)
            if boundary == "before_delta"
            else app.history_index.checkpoint
        )
        if path == target:
            raise OSError("simulated interrupted derived publication")
        atomic(path, raw)

    monkeypatch.setattr(module, "_atomic", interrupted)
    error("REPAIR_REQUIRED", lambda: app.submit(request))
    committed = app.store.resolve()
    assert committed != source
    stored = decode(app.store.read(committed)[app.receipts.for_request(request)])
    monkeypatch.setattr(module, "_atomic", atomic)
    recovered = restart(app)
    # An unanchored immutable delta does not invalidate the old base. Recovery
    # re-verifies canonical Git and safely replaces that nonaccepted slot.
    assert recovered.contracts.dump("transaction", recovered.submit(request)) == stored
    assert recovered.store.resolve() == committed


def test_competing_core_checkpoint_change_reloads_instead_of_sticking(core):
    app, cluster = core
    other = restart(app)
    other.generation()
    app.submit(batch(app, cluster))
    with pytest.raises(CoreError):
        other.history_index.coherent()
    assert other.generation() == app.generation()
    assert other.submit(batch(other, cluster)).status == "committed"


def test_delta_prepare_matches_full_tree_without_rehashing_unchanged_blobs(core, monkeypatch):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    parent = app.store.resolve()
    original = app.store.read(parent)
    changed = {
        GENERATION: encode(
            app.repository.generation(
                original, scheme=decode(original[GENERATION]).get("commitment_scheme")
            )
        )
    }
    calls = []
    run = app.store._run_bytes

    def tracked(*args, **kwargs):
        calls.append(args)
        return run(*args, **kwargs)

    monkeypatch.setattr(app.store, "_run_bytes", tracked)
    candidate = app.store.prepare_delta(changed, parent)
    assert sum(args[0] == "hash-object" for args in calls) == 1
    full = dict(original, **changed)
    assert app.store.entries(candidate) == app.store.entries(app.store.prepare(full, parent))


def test_missing_requested_original_commit_fails_replay(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    origin = app.store.resolve()
    files = app.store.read(origin)
    publish(app, files)
    app.generation()
    object_path = app.store.common / "objects" / origin[:2] / origin[2:]
    assert object_path.is_file()
    object_path.chmod(stat.S_IWRITE | stat.S_IREAD)
    object_path.unlink()
    error("REPAIR_REQUIRED", lambda: app.submit(request))


def test_real_backup_restore_without_sqlite_rebuilds_same_knowledge(core, tmp_path):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    destination = tmp_path / "restored backing"
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", str(app.context.repository), str(destination)],
        check=True,
        capture_output=True,
    )
    context = replace(app.context, repository=destination)
    restored = Core(context, GitStore(destination, context.managed_ref), app.contracts)
    error("REPAIR_REQUIRED", restored.generation)
    assert rebuild_history_index(restored)["status"] == "rebuilt"
    assert restored.submit(request) == receipt
    assert (
        read_node(restored, request["operations"][0]["request_id"]).records
        == read_node(app, request["operations"][0]["request_id"]).records
    )
    assert restored.store.resolve() == app.store.resolve()


def test_unrelated_root_graft_cannot_replace_the_accepted_ancestry(core):
    app, cluster = core
    app.submit(batch(app, cluster))
    accepted = app.store.resolve()
    files = app.store.read(accepted)
    unrelated = app.store.prepare(files, None)
    app.store.publish(unrelated, accepted)
    path = app.store.common / "info" / "grafts"
    path.parent.mkdir(exist_ok=True)
    path.write_text(f"{unrelated} {accepted}\n", encoding="ascii")
    error("REPAIR_REQUIRED", app.generation)
    assert audit_history(app)["code"] == "NONLINEAR_HISTORY"
    assert rebuild_history_index(app)["code"] == "NONLINEAR_HISTORY"


@pytest.mark.parametrize(
    "defect", ["key_missing", "key_changed", "checkpoint_changed", "enrollment_changed"]
)
def test_trust_anchor_damage_requires_operator_instead_of_index_rebuild(core, defect):
    app, _ = core
    index = app.history_index
    if defect == "key_missing":
        index.key_path.unlink()
    elif defect == "key_changed":
        index.key_path.write_bytes(b"x" * 32)
    elif defect == "checkpoint_changed":
        envelope = json.loads(index.checkpoint.read_bytes())
        envelope["payload"]["commit"] = "0" * 40
        index.checkpoint.write_text(json.dumps(envelope), encoding="utf-8")
    else:
        index.enrollment.write_bytes(b"invalid enrollment")
    result = audit_history(app)
    assert result["code"] == "VERIFICATION_FAILED"
    assert result["rebuild_sufficient"] is False
    assert rebuild_history_index(app)["code"] == "VERIFICATION_FAILED"


def test_actual_child_process_uses_authenticated_projection_without_history_scan(core):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    config = dict(
        instance=app.context.instance_id,
        repository=str(app.context.repository),
        ref=app.context.managed_ref,
        principal=app.context.principal.principal_id,
        grants=sorted(app.context.principal.grants),
    )
    script = """
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'packages/python'))
from second_brain_core import Core,GitStore,InstanceContext,TrustedPrincipal
config,read,request=json.loads(sys.stdin.buffer.read())
context=InstanceContext(config['instance'],Path(config['repository']),config['ref'],
 TrustedPrincipal(config['principal'],frozenset(map(tuple,config['grants']))))
store=GitStore(context.repository,context.managed_ref)
def forbidden(*args,**kwargs): raise AssertionError('full history/tree on restart')
store.read=store.entries=store.ancestry=store.changes=forbidden
app=Core(context,store)
result=app.read(read)
receipt=app.submit(request)
print(json.dumps([app.contracts.dump('transaction',result),app.contracts.dump('transaction',receipt)]))
"""
    child = subprocess.run(
        [sys.executable, "-c", script, str(app.contracts.root)],
        input=encode(
            [
                config,
                operation(app, "node.read", {"node_id": request["operations"][0]["request_id"]}),
                request,
            ]
        ),
        capture_output=True,
        check=False,
    )
    assert child.returncode == 0, child.stderr.decode()
    read, replay = json.loads(child.stdout)
    assert read["records"][0]["id"] == request["operations"][0]["request_id"]
    assert replay == app.contracts.dump("transaction", receipt)


def test_invalid_committed_metadata_schema_is_sanitized(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    files = app.store.read(app.store.resolve())
    files["control/metadata.json"] = encode({"local:note:1": {"type": 123}})
    publish(app, files)
    error("REPAIR_REQUIRED", app.generation)
    error("REPAIR_REQUIRED", lambda: read_node(app, request["operations"][0]["request_id"]))
    assert audit_history(app)["code"] == "CANONICAL_STATE_CORRUPT"


def test_unrelated_generation_reuses_verified_content_digest_without_accepting_a_wrong_one(
    core, monkeypatch
):
    from second_brain_core.verification import TransitionVerifier

    app, cluster = core
    app.submit(batch(app, cluster))
    files = app.store.read(app.store.resolve())
    publish(app, files)
    calls = []
    original = TransitionVerifier._generation

    def checked(verifier, content_digest=None):
        calls.append(content_digest)
        return original(verifier, content_digest)

    monkeypatch.setattr(TransitionVerifier, "_generation", checked)
    generation = app.generation()
    assert calls == [generation["digest"]]
    wrong = dict(generation, generation_id=uid(), digest=dict(algorithm="sha256", value="0" * 64))
    parent = app.store.resolve()
    candidate = app.store.prepare_delta({GENERATION: encode(wrong)}, parent)
    app.store.publish(candidate, parent)
    error("REPAIR_REQUIRED", app.generation)


def test_full_snapshot_pins_verified_frontier_despite_external_ref_advance(core, monkeypatch):
    app, cluster = core
    root_files = app.store.read(app.store.resolve())
    request = batch(app, cluster)
    receipt = app.submit(request)
    accepted = app.store.resolve()
    root_files[GENERATION] = encode(
        app.repository.generation(
            root_files, scheme=decode(root_files[GENERATION]).get("commitment_scheme")
        )
    )
    invalid = app.store.prepare(root_files, accepted)
    original = app.history_index.ensure

    def advance_after_verification(*, locked=False):
        original(locked=locked)
        app.store.publish(invalid, accepted)

    monkeypatch.setattr(app.history_index, "ensure", advance_after_verification)
    commit, _, generation, records, _ = app.repository.snapshot()
    assert commit == accepted
    assert generation == app.contracts.dump("transaction", receipt)["generation"]
    assert ("node", request["operations"][0]["request_id"]) in records
    monkeypatch.setattr(app.history_index, "ensure", original)
    error("REPAIR_REQUIRED", app.generation)


def test_rebuild_keeps_anchor_when_index_is_missing_and_ref_moves_backward(core):
    app, cluster = core
    old = app.store.resolve()
    app.submit(batch(app, cluster))
    accepted = app.store.resolve()
    app.history_index.database.unlink()
    app.store.publish(old, accepted)
    result = rebuild_history_index(app)
    assert result["code"] == "MISSING_ANCESTOR"
    assert result["rebuild_sufficient"] is False


def test_unrelated_history_without_grafts_is_rejected(core):
    app, cluster = core
    app.submit(batch(app, cluster))
    accepted = app.store.resolve()
    unrelated = app.store.prepare(app.store.read(accepted), None)
    app.store.publish(unrelated, accepted)
    error("REPAIR_REQUIRED", app.generation)
    assert rebuild_history_index(app)["code"] == "MISSING_ANCESTOR"


def test_interrupted_catchup_keeps_old_projection_and_restart_retries(core, monkeypatch):
    from second_brain_core.verification import TransitionVerifier

    app, cluster = core
    app.submit(batch(app, cluster))
    checkpoint = app.history_index.checkpoint.read_bytes()
    publish(app, app.store.read(app.store.resolve()))
    original = TransitionVerifier.transition

    def interrupted(verifier, *args):
        original(verifier, *args)
        raise OSError("interrupted uncommitted SQLite projection")

    monkeypatch.setattr(TransitionVerifier, "transition", interrupted)
    error("REPAIR_REQUIRED", app.generation)
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    monkeypatch.setattr(TransitionVerifier, "transition", original)
    assert restart(app).generation()


def test_rebuild_race_and_interruption_preserve_the_known_good_database(core, monkeypatch):
    import second_brain_core.history_index as module

    app, cluster = core
    app.submit(batch(app, cluster))
    original_bytes = app.history_index.database.read_bytes()
    atomic = module._atomic

    def interrupted(path, raw):
        if path.suffix == ".sqlite3":
            raise OSError("interrupted before atomic replacement")
        atomic(path, raw)

    monkeypatch.setattr(module, "_atomic", interrupted)
    assert rebuild_history_index(app)["status"] == "repair_required"
    assert app.history_index.database.read_bytes() == original_bytes
    monkeypatch.setattr(module, "_atomic", atomic)
    original_publish = app.history_index.publish

    def raced(connection, commit, generation):
        publish(app, app.store.read(commit))
        original_publish(connection, commit, generation)

    monkeypatch.setattr(app.history_index, "publish", raced)
    assert rebuild_history_index(app)["code"] == "INDEX_STALE"
    assert app.history_index.database.read_bytes() == original_bytes
    monkeypatch.setattr(app.history_index, "publish", original_publish)
    assert rebuild_history_index(app)["status"] == "rebuilt"


@pytest.mark.parametrize("missing", ["generation", "tree"])
def test_fast_generation_still_requires_its_canonical_tree_and_descriptor(core, missing):
    app, _ = core
    commit = app.store.resolve()
    oid = (
        app.store.locate(commit, GENERATION)
        if missing == "generation"
        else app.store.run("rev-parse", f"{commit}^{{tree}}").strip()
    )
    path = app.store.common / "objects" / oid[:2] / oid[2:]
    path.chmod(stat.S_IWRITE | stat.S_IREAD)
    path.unlink()
    error("REPAIR_REQUIRED", app.generation)
    assert audit_history(app)["code"] == "MISSING_ANCESTOR"


@pytest.mark.parametrize("destination_kind", ["repository", "ref"])
def test_copied_local_trust_files_cannot_authorize_another_repository_or_ref(
    core, tmp_path, destination_kind
):
    app, cluster = core
    app.submit(batch(app, cluster))
    if destination_kind == "repository":
        path = tmp_path / "copied instance files"
        subprocess.run(
            ["git", "clone", "--quiet", "--bare", str(app.context.repository), str(path)],
            check=True,
            capture_output=True,
        )
        context = replace(app.context, repository=path)
    else:
        ref = "refs/heads/other-managed-ref"
        app.store.run("update-ref", ref, app.store.resolve())
        context = replace(app.context, managed_ref=ref)
    other = Core(context, GitStore(context.repository, context.managed_ref), app.contracts)
    shutil.copytree(app.history_index.directory, other.history_index.directory)
    error("REPAIR_REQUIRED", other.generation)
    assert audit_history(other)["code"] == "INDEX_IDENTITY_MISMATCH"


def test_interrupted_first_enrollment_requires_explicit_authenticated_retry(
    core, tmp_path, monkeypatch
):
    import second_brain_core.history_index as module

    app, cluster = core
    app.submit(batch(app, cluster))
    path = tmp_path / "unenrolled restore"
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", str(app.context.repository), str(path)],
        check=True,
        capture_output=True,
    )
    context = replace(app.context, repository=path)
    restored = Core(context, GitStore(path, context.managed_ref), app.contracts)
    atomic = module._atomic

    def interrupted(target, raw):
        if target == restored.history_index.checkpoint:
            raise OSError("interrupted first checkpoint")
        atomic(target, raw)

    monkeypatch.setattr(module, "_atomic", interrupted)
    assert rebuild_history_index(restored)["status"] == "repair_required"
    assert restored.history_index.enrollment.exists()
    error("REPAIR_REQUIRED", restart(restored).generation)
    monkeypatch.setattr(module, "_atomic", atomic)
    assert rebuild_history_index(restored)["status"] == "rebuilt"
    assert restored.generation() == app.generation()


def remove_object(app, oid):
    path = app.store.common / "objects" / oid[:2] / oid[2:]
    path.chmod(stat.S_IWRITE | stat.S_IREAD)
    path.unlink()


@pytest.mark.parametrize(
    "missing", ["node", "relation", "endpoint", "receipt", "request", "origin"]
)
def test_denied_private_reads_and_replay_do_not_probe_missing_evidence(core, missing):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    node = request["operations"][0]["request_id"]
    relation = request["operations"][2]["payload"]["relation"]["id"]
    path = f"knowledge/node/{node}.md"
    if missing == "relation":
        path = f"knowledge/relation/{relation}.yaml"
    elif missing in {"receipt", "request"}:
        path = app.receipts.for_request(request)
        if missing == "request":
            path = app.receipts.request_path(path)
    oid = app.store.locate(app.store.resolve(), path)
    if missing == "origin":
        oid = app.store.resolve()
        publish(app, app.store.read(oid))
        app.generation()
    remove_object(app, oid)
    grants = frozenset({(cluster, "relation.read")}) if missing == "endpoint" else frozenset()
    denied = restart(
        app,
        replace(
            app.context, principal=replace(app.context.principal, grants=grants, bootstrap=False)
        ),
    )
    if missing in {"node", "relation", "endpoint"}:
        action = "node.read" if missing == "node" else "relation.read"
        key = "node_id" if action == "node.read" else "relation_id"
        identifier = node if missing == "node" else relation
        error("NOT_FOUND", lambda: denied.read(operation(denied, action, {key: identifier})))
        error("NOT_FOUND", lambda: denied.read(operation(denied, action, {key: uid()})))
    else:
        error("NOT_FOUND", lambda: denied.submit(request))
        unknown = copy.deepcopy(request)
        unknown["idempotency_key"] = uid()
        error("NOT_FOUND", lambda: denied.submit(unknown))


@pytest.mark.parametrize(
    "target",
    ["cluster", "node_collision", "relation_endpoint", "relation_collision", "expectation"],
)
def test_mutation_denial_precedes_hidden_dependency_blob_access(core, target):
    app, cluster = core
    original = batch(app, cluster)
    app.submit(original)
    generation = app.generation()
    node = original["operations"][0]["request_id"]
    relation = original["operations"][2]["payload"]["relation"]
    grants = frozenset((cluster, action) for action in ("node.create", "membership.admit"))
    path = f"knowledge/node/{node}.md"
    create = operation(app, "node.create", copy.deepcopy(original["operations"][0]["payload"]))
    if target == "cluster":
        path = f"knowledge/cluster/{cluster}.yaml"
        grants = frozenset()
    elif target == "node_collision":
        create["payload"]["node_id"] = node
    elif target == "expectation":
        create["expectations"] = [
            dict(
                resource=dict(instance_id=app.context.instance_id, resource_kind="node", id=node),
                expected_revision=1,
            )
        ]
    else:
        grants = frozenset({(cluster, "relation.create")})
        payload = copy.deepcopy(relation)
        if target == "relation_endpoint":
            payload["id"] = uid()
        else:
            path = f"knowledge/relation/{relation['id']}.yaml"
            grants |= frozenset({(cluster, "node.read")})
        create = operation(app, "relation.create", {"relation": payload})
    denied = restart(
        app, replace(app.context, principal=replace(app.context.principal, grants=grants))
    )
    error("NOT_FOUND", lambda: denied.execute(create, generation))
    remove_object(app, app.store.locate(app.store.resolve(), path))
    error("NOT_FOUND", lambda: denied.execute(create, generation))
    if target in {"cluster", "relation_endpoint", "expectation"}:
        unknown = copy.deepcopy(create)
        if target == "cluster":
            unknown["payload"]["target_cluster_id"] = uid()
        elif target == "relation_endpoint":
            unknown["payload"]["relation"]["source"]["id"] = uid()
        else:
            unknown["expectations"][0]["resource"]["id"] = uid()
        error("NOT_FOUND", lambda: denied.execute(unknown, generation))


def test_create_only_replay_does_not_acquire_read_requirements(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    generation = app.generation()
    node_creator = restart(
        app,
        replace(
            app.context,
            principal=replace(
                app.context.principal,
                grants=frozenset({(cluster, "node.create"), (cluster, "membership.admit")}),
            ),
        ),
    )
    node = operation(app, "node.create", copy.deepcopy(request["operations"][0]["payload"]))
    first = node_creator.execute(node, generation)
    assert restart(node_creator).execute(node, generation) == first
    error("NOT_FOUND", lambda: read_node(node_creator, node["request_id"]))
    relation_creator = restart(
        app,
        replace(
            app.context,
            principal=replace(
                app.context.principal,
                grants=frozenset({(cluster, "relation.create"), (cluster, "node.read")}),
            ),
        ),
    )
    relation = copy.deepcopy(request["operations"][2]["payload"]["relation"])
    relation["id"] = uid()
    create = operation(app, "relation.create", {"relation": relation})
    generation = relation_creator.generation()
    second = relation_creator.execute(create, generation)
    assert restart(relation_creator).execute(create, generation) == second
    error(
        "NOT_FOUND",
        lambda: relation_creator.read(
            operation(app, "relation.read", {"relation_id": relation["id"]})
        ),
    )


def test_preflight_supports_expectation_on_an_earlier_batch_created_node(core):
    app, cluster = core
    request = batch(app, cluster)
    request["operations"][1]["expectations"] = [
        dict(
            resource=dict(
                instance_id=app.context.instance_id,
                resource_kind="node",
                id=request["operations"][0]["request_id"],
            ),
            expected_revision=1,
        )
    ]
    assert app.submit(request).status == "committed"


@pytest.mark.parametrize("rollback", [False, True])
def test_empty_enrollment_directory_is_lost_trust_not_a_pristine_instance(core, rollback):
    app, cluster = core
    root = app.store.resolve()
    app.submit(batch(app, cluster))
    accepted = app.store.resolve()
    directory = app.history_index.directory
    for path in tuple(directory.iterdir()):
        assert path.is_file()
        path.unlink()
    if rollback:
        app.store.publish(root, accepted)
    source = app.store.resolve()
    assert list(directory.iterdir()) == []
    for result in (audit_history(app), rebuild_history_index(app)):
        assert result["code"] == "VERIFICATION_FAILED"
        assert result["rebuild_sufficient"] is False
    error("REPAIR_REQUIRED", lambda: app.history_index.begin(source))
    assert list(directory.iterdir()) == []
    assert app.store.resolve() == source


def test_lost_enrollment_cannot_publish_a_fresh_bootstrap_after_ref_deletion(core):
    app, _ = core
    _, records, metadata = app.repository.parse_tree(app.store.read(app.store.resolve()))
    directory = app.history_index.directory
    for path in tuple(directory.iterdir()):
        path.unlink()
    app.store.run("update-ref", "-d", app.context.managed_ref)
    objects = sorted((app.store.common / "objects").rglob("*"))
    error("REPAIR_REQUIRED", lambda: app.bootstrap(records.values(), metadata))
    assert app.store.resolve() is None
    assert list(directory.iterdir()) == []
    assert sorted((app.store.common / "objects").rglob("*")) == objects
