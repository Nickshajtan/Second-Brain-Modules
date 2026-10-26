"""Immutable truth, explicit backfill and current authority using disposable Git."""

import copy
import subprocess
from dataclasses import replace

import pytest
from second_brain_core import (
    Core,
    GitStore,
    TrustedPrincipal,
    apply_history_migration,
    inspect_history,
)
from second_brain_core.boundary import GENERATION, digest
from second_brain_core.codec import decode, encode
from second_brain_core.git_store import PublicationConflict, StorageError
from second_brain_core.history import HISTORY
from test_core_m1 import batch, error, read_node, uid


def publish(app, files):
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    candidate = app.store.prepare(files, parent)
    app.store.publish(candidate, parent)


def legacy(app, cluster, monkeypatch, metadata_only=True):
    """Construct an actual old commit chain, not a newer head used as history."""
    original = app.store.prepare
    # Re-provision the disposable fixture's bootstrap as an old root commit.
    root = app.store.read(app.store.resolve())
    root.pop(HISTORY)
    old_root = original(root, None)
    app.store.publish(old_root, app.store.resolve())

    def old_prepare(files, parent):
        files = dict(files)
        for path in list(files):
            if path.startswith("knowledge/relation_revision/"):
                del files[path]
            elif metadata_only and path.startswith("knowledge/node_revision/"):
                record = decode(files[path])
                record.pop("snapshot", None)
                files[path] = encode(record)
        generation = decode(files[GENERATION])
        generation["digest"] = app.repository.content_digest(files)
        files[GENERATION] = encode(generation)
        for path in files:
            if path.startswith("control/receipts/"):
                receipt = decode(files[path])
                if receipt["generation"]["generation_id"] == generation["generation_id"]:
                    receipt["generation"] = generation
                    files[path] = encode(receipt)
        return original(files, parent)

    monkeypatch.setattr(app.store, "prepare", old_prepare)
    request = batch(app, cluster)
    app.submit(request)
    monkeypatch.setattr(app.store, "prepare", original)
    # Original method's returned receipt precedes the fixture-only legacy conversion.
    receipt_path = app.receipts.for_request(request)
    receipt = decode(app.store.read(app.store.resolve())[receipt_path])
    return request, receipt


def test_fresh_exact_history_and_replay_after_unrelated_commit(core):
    app, cluster = core
    request = batch(app, cluster)
    first = app.submit(request)
    _, files, _, records, _ = app.repository.snapshot()
    assert decode(files[HISTORY])["mode"] == "fresh"
    revisions = first.model_dump(mode="json")["results"]
    for operation, result in zip(request["operations"], revisions, strict=True):
        ref = result["revisions"][0]
        kind = "node_revision" if operation["operation"] == "node.create" else "relation_revision"
        history = records[kind, ref["revision_id"]]
        snapshot = operation["payload"].get("content", operation["payload"].get("relation"))
        assert history["snapshot"] == snapshot
        assert history["digest"] == digest(snapshot)
        assert history["logical_revision"] == 1
    app.submit(batch(app, cluster))
    head = app.store.resolve()
    restarted = Core(app.context, app.store, app.contracts)
    assert restarted.submit(request) == first
    assert app.store.resolve() == head
    changed = copy.deepcopy(request)
    changed["operations"][0]["payload"]["content"]["title"] = "changed"
    error("IDEMPOTENCY_CONFLICT", lambda: restarted.submit(changed))
    partial = copy.deepcopy(request)
    partial.update(
        transaction_id=uid(), idempotency_key=uid(), expected_generation=app.generation()
    )
    partial["operations"] = partial["operations"][:1]
    error("IDEMPOTENCY_CONFLICT", lambda: restarted.submit(partial))


@pytest.mark.parametrize(
    "defect",
    [
        "missing_relation",
        "missing_node",
        "hash",
        "duplicate_sequence",
        "cross_kind_id",
        "binding",
        "receipt_actor",
        "receipt_result",
        "admission",
        "marker",
        "receipt_removed",
    ],
)
def test_corrupt_or_missing_immutable_effects_fail_closed(core, defect):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    _, files, _, records, _ = app.repository.snapshot()
    relation = next(record for (kind, _), record in records.items() if kind == "relation_revision")
    node = next(record for (kind, _), record in records.items() if kind == "node_revision")
    relation_path = f"knowledge/relation_revision/{relation['id']}.yaml"
    node_path = f"knowledge/node_revision/{node['id']}.yaml"
    if defect == "missing_relation":
        del files[relation_path]
    elif defect == "missing_node":
        del files[node_path]
    elif defect == "hash":
        relation["snapshot"]["predicate"] = "tampered"
        files[relation_path] = encode(relation)
    elif defect == "duplicate_sequence":
        relation["id"] = uid()
        files[f"knowledge/relation_revision/{relation['id']}.yaml"] = encode(relation)
    elif defect == "cross_kind_id":
        del files[relation_path]
        relation["id"] = node["id"]
        files[f"knowledge/relation_revision/{relation['id']}.yaml"] = encode(relation)
    elif defect == "binding":
        relation["relation_id"] = uid()
        files[relation_path] = encode(relation)
    elif defect == "marker":
        del files[HISTORY]
    elif defect == "receipt_removed":
        path = app.receipts.for_request(request)
        del files[path]
        del files[app.receipts.request_path(path)]
    else:
        path = app.receipts.for_request(request)
        receipt = decode(files[path])
        if defect == "receipt_actor":
            receipt["actor"]["principal_id"] = uid()
            newpath = app.receipts.path(
                receipt["actor"]["principal_id"], receipt["idempotency_key"]
            )
            files[newpath] = encode(receipt)
            files[app.receipts.request_path(newpath)] = files.pop(app.receipts.request_path(path))
            del files[path]
        elif defect == "receipt_result":
            receipt["results"][0]["revisions"][0]["revision_id"] = uid()
            files[path] = encode(receipt)
        else:
            member = next(record for (kind, _), record in records.items() if kind == "membership")
            member["admitted_by"]["principal_id"] = uid()
            files[f"knowledge/membership/{member['id']}.yaml"] = encode(member)
            # Current membership may evolve; forge original receipt too to claim new admission.
            receipt["results"][0]["resources"][1]["id"] = uid()
            files[path] = encode(receipt)
    publish(app, files)
    error("REPAIR_REQUIRED", app.generation)


def test_historical_verifier_ignores_future_heads_and_live_admission(core):
    app, cluster = core
    request = batch(app, cluster)
    first = app.submit(request)
    commit, files, _, records, _ = app.repository.snapshot()
    original_member = copy.deepcopy(next(r for (k, _), r in records.items() if k == "membership"))
    for version in (2, 3):
        future = copy.deepcopy(records)
        for (kind, _), record in future.items():
            if kind == "node":
                record["revision"] = version
                record["content"]["body"] = f"future {version}"
            elif kind == "relation":
                record["revision"] = version + 1
                record["predicate"] = "future-predicate"
            elif kind == "membership":
                record["revision"] = version
                record["admitted_by"] = {"principal_id": uid()}
        # Isolated fixture: does not relax normal public snapshot/domain validation.
        app.receipts.history.validate(files, future, commit)
        assert app.receipts.replay(request, files, future) == first
    origin = app.receipts.history.origin(
        app.receipts.for_request(request), files, app.receipts.history.trees(commit)
    )[3]
    assert origin["membership", original_member["id"]] == original_member
    denied = Core(
        replace(
            app.context,
            principal=TrustedPrincipal(app.context.principal.principal_id, frozenset(), True),
        ),
        app.store,
        app.contracts,
    )
    error("NOT_FOUND", lambda: denied.receipts.replay(request, files, future))
    # Future retrieval guard fixture: resource reads never imply historical permission.
    error("NOT_FOUND", lambda: app.access.cluster(records, cluster, "node.history.read"))
    historical = Core(
        replace(
            app.context,
            principal=TrustedPrincipal(
                app.context.principal.principal_id,
                app.context.principal.grants | {(cluster, "node.history.read")},
            ),
        ),
        app.store,
        app.contracts,
    )
    historical.access.cluster(records, cluster, "node.history.read")
    assert (
        origin["node_revision", first.results[0].revisions[0].revision_id.root]["snapshot"]
        == request["operations"][0]["payload"]["content"]
    )


@pytest.mark.parametrize("metadata_only", [True, False])
def test_explicit_migration_preserves_original_bytes_and_receipts(core, monkeypatch, metadata_only):
    app, cluster = core
    request, receipt = legacy(app, cluster, monkeypatch, metadata_only)
    source = app.store.resolve()
    before = app.store.read(source)
    human = app.context.repository / "human-uncommitted.md"
    human.write_bytes(b"offline human bytes\r\n")
    objects_before = sorted((app.store.common / "objects").rglob("*"))
    import second_brain_core.repository as repository_module

    with monkeypatch.context() as patch:
        patch.setattr(repository_module, "uid", lambda: pytest.fail("dry-run allocated UUID"))
        plan = inspect_history(app)
        assert inspect_history(app) == plan
    assert app.store.resolve() == source
    assert sorted((app.store.common / "objects").rglob("*")) == objects_before
    assert plan["status"] == "eligible"
    assert len(plan["additions"]) == (3 if metadata_only else 1)
    result = apply_history_migration(app, plan)
    after = app.store.resolve()
    current = app.store.read(after)
    for path, value in before.items():
        if path != GENERATION:
            assert current[path] == value
    assert app.contracts.dump("transaction", app.submit(request)) == receipt
    assert apply_history_migration(app, plan) == result
    assert app.store.resolve() == after
    forged_plan = copy.deepcopy(plan)
    forged_plan["inventory"] = []
    error("REPAIR_REQUIRED", lambda: apply_history_migration(app, forged_plan))
    _, verified_files, _, verified_records, _ = app.repository.snapshot()
    payloads = [["knowledge", record] for record in verified_records.values()]
    payloads.append(["transaction", decode(verified_files[HISTORY])])
    external = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            """
        import {loadContracts} from './packages/typescript/validation.mjs';
        import fs from 'node:fs';
        const contracts = await loadContracts(process.cwd());
        for (const [family, payload] of JSON.parse(fs.readFileSync(0, 'utf8'))) {
            contracts.validate(family, payload);
        }
        """,
        ],
        input=encode(payloads),
        capture_output=True,
        cwd=app.contracts.root,
    )
    assert external.returncode == 0, external.stderr.decode()
    app.submit(batch(app, cluster))
    later = app.store.resolve()
    assert apply_history_migration(app, plan) == result
    assert app.store.resolve() == later
    assert human.read_bytes() == b"offline human bytes\r\n"
    assert (
        read_node(app, request["operations"][0]["request_id"]).records[0].root.content.body
        == request["operations"][0]["payload"]["content"]["body"]
    )


@pytest.mark.parametrize("failure", ["before_prepare", "cas", "after_publish"])
def test_migration_interruption_and_conditional_publication(core, monkeypatch, failure):
    app, cluster = core
    _, _ = legacy(app, cluster, monkeypatch)
    plan = inspect_history(app)
    before = app.store.resolve()
    prepare, publish_method = app.store.prepare, app.store.publish
    if failure == "before_prepare":

        def broken(*args):
            raise StorageError("private storage detail")

        monkeypatch.setattr(app.store, "prepare", broken)
    elif failure == "cas":

        def raced(candidate, expected):
            raise PublicationConflict("concurrent writer")

        monkeypatch.setattr(app.store, "publish", raced)
    else:

        def uncertain(candidate, expected):
            publish_method(candidate, expected)
            raise StorageError("uncertain result")

        monkeypatch.setattr(app.store, "publish", uncertain)
    error(
        "REVISION_CONFLICT" if failure == "cas" else "REPAIR_REQUIRED",
        lambda: apply_history_migration(app, plan),
    )
    if failure != "after_publish":
        assert app.store.resolve() == before
        assert HISTORY not in app.store.read(before)
    monkeypatch.setattr(app.store, "prepare", prepare)
    monkeypatch.setattr(app.store, "publish", publish_method)
    result = apply_history_migration(app, plan)
    assert result.mode == "migrated"


@pytest.mark.parametrize(
    "defect",
    ["origin_missing", "receipt_corrupt", "source_changed", "instance", "tampered_history"],
)
def test_migration_refuses_unverifiable_or_stale_source(core, monkeypatch, defect):
    app, cluster = core
    request, _ = legacy(app, cluster, monkeypatch)
    plan = inspect_history(app)
    source = app.store.resolve()
    if defect == "origin_missing":
        original = app.store.read

        def unavailable(commit):
            if commit == source:
                raise StorageError("original missing")
            return original(commit)

        monkeypatch.setattr(app.store, "read", unavailable)
        assert inspect_history(app)["status"] == "repair_required"
        error("REPAIR_REQUIRED", lambda: apply_history_migration(app, plan))
    elif defect == "source_changed":
        app.submit(batch(app, cluster))
        error("REVISION_CONFLICT", lambda: apply_history_migration(app, plan))
    elif defect == "instance":
        other = Core(replace(app.context, instance_id=uid()), app.store, app.contracts)
        assert inspect_history(other)["status"] == "repair_required"
        error("REPAIR_REQUIRED", lambda: apply_history_migration(other, plan))
    else:
        files = app.store.read(source)
        if defect == "receipt_corrupt":
            path = app.receipts.for_request(request)
            receipt = decode(files[path])
            receipt["request_digest"] = digest("forged")
            files[path] = encode(receipt)
        else:
            path = next(
                path
                for path in files
                if path.startswith("knowledge/node/") and path.endswith(".md")
            )
            files[path] = b"tampered old content"
        publish(app, files)
        assert inspect_history(app)["status"] == "repair_required"
        error("REPAIR_REQUIRED", lambda: apply_history_migration(app, plan))


def test_migration_host_only_and_fresh_repository_inventory(core):
    app, _ = core
    assert inspect_history(app)["status"] == "complete"
    untrusted = Core(
        replace(app.context, principal=replace(app.context.principal, bootstrap=False)),
        app.store,
        app.contracts,
    )
    error("FORBIDDEN", lambda: inspect_history(untrusted))
    error("FORBIDDEN", lambda: apply_history_migration(untrusted, {}))


def test_migration_loses_real_ref_race_without_partial_effects(core, monkeypatch):
    app, cluster = core
    legacy(app, cluster, monkeypatch)
    plan = inspect_history(app)
    original = app.store.publish
    competitor = None

    def raced(candidate, expected):
        nonlocal competitor
        files = app.store.read(expected)
        files[GENERATION] = encode(app.repository.generation(files))
        competitor = app.store.prepare(files, expected)
        original(competitor, expected)
        original(candidate, expected)

    monkeypatch.setattr(app.store, "publish", raced)
    error("REVISION_CONFLICT", lambda: apply_history_migration(app, plan))
    assert app.store.resolve() == competitor
    assert HISTORY not in app.store.read(competitor)
    assert not any(
        path.startswith("knowledge/node_revision_snapshot/") for path in app.store.read(competitor)
    )


@pytest.mark.parametrize("defect", ["marker_removed", "duplicate_supplement"])
def test_migration_marker_and_supplement_retention(core, monkeypatch, defect):
    app, cluster = core
    legacy(app, cluster, monkeypatch)
    apply_history_migration(app, inspect_history(app))
    parent = app.store.resolve()
    files = app.store.read(parent)
    if defect == "marker_removed":
        del files[HISTORY]
    else:
        path = next(path for path in files if path.startswith("knowledge/node_revision_snapshot/"))
        duplicate = decode(files[path])
        duplicate["id"] = uid()
        files[f"knowledge/node_revision_snapshot/{duplicate['id']}.yaml"] = encode(duplicate)
    publish(app, files)
    error("REPAIR_REQUIRED", app.generation)


def test_inventory_distinguishes_ambiguous_generation(core, monkeypatch):
    app, cluster = core
    legacy(app, cluster, monkeypatch)
    parent = app.store.resolve()
    # A copied logical generation in another commit is ambiguous, even unchanged.
    app.store.publish(app.store.prepare(app.store.read(parent), parent), parent)
    report = inspect_history(app)
    assert report["status"] == "repair_required"
    assert report["blocking"] == ["ambiguous_history"]


@pytest.mark.parametrize("keep_later_transaction", [False, True])
def test_joint_transaction_evidence_deletion_is_detected_from_ancestry(
    core, keep_later_transaction
):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.contracts.dump("transaction", app.submit(request))
    original = app.store.resolve()
    if keep_later_transaction:
        app.submit(batch(app, cluster))
    files = app.store.read(app.store.resolve())
    receipt_path = app.receipts.for_request(request)
    del files[receipt_path]
    del files[app.receipts.request_path(receipt_path)]
    for result in receipt["results"]:
        for resource in result["resources"]:
            kind, identifier = resource["resource_kind"], resource["id"]
            del files[f"knowledge/{kind}/{identifier}.yaml"]
            if kind == "node":
                del files[f"knowledge/node/{identifier}.md"]
        for revision in result["revisions"]:
            kind = revision["resource"]["resource_kind"] + "_revision"
            del files[f"knowledge/{kind}/{revision['revision_id']}.yaml"]
    publish(app, files)
    assert original in app.store.ancestry(app.store.resolve())
    assert (
        bool([path for path in files if path.startswith("control/receipts/")])
        == keep_later_transaction
    )
    error("REPAIR_REQUIRED", app.generation)


def test_shallow_managed_history_is_rejected(core, tmp_path):
    app, cluster = core
    app.submit(batch(app, cluster))
    target = tmp_path / "shallow backing repository"
    cloned = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-checkout",
            "--depth=1",
            "--branch=brain",
            app.context.repository.as_uri(),
            str(target),
        ],
        capture_output=True,
    )
    assert cloned.returncode == 0, cloned.stderr.decode()
    context = replace(app.context, repository=target)
    shallow = Core(context, GitStore(target, context.managed_ref), app.contracts)
    assert shallow.store.run("rev-parse", "--is-shallow-repository").strip() == "true"
    error("REPAIR_REQUIRED", shallow.generation)


def test_merge_in_managed_history_is_rejected(core):
    app, cluster = core
    bootstrap = app.store.resolve()
    app.submit(batch(app, cluster))
    head = app.store.resolve()
    tree = app.store.run("rev-parse", head + "^{tree}").strip()
    identity = {
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@localhost",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@localhost",
    }
    merge = app.store.run(
        "commit-tree",
        tree,
        "-p",
        head,
        "-p",
        bootstrap,
        data=b"isolated merge fixture\n",
        env=identity,
    ).strip()
    app.store.publish(merge, head)
    assert len(app.store.run("rev-list", "--parents", "-n", "1", merge).split()) == 3
    error("REPAIR_REQUIRED", app.generation)
