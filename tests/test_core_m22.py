"""Node mutations preserve immutable effects and current authority."""

import copy
import hmac
import json
from dataclasses import replace

import pytest
from second_brain_core import Core, GitStore, audit_history, inspect_history, rebuild_history_index
from second_brain_core.boundary import GENERATION, digest
from second_brain_core.codec import decode, encode
from second_brain_core.history_index import _json
from test_core_m1 import batch, error, operation, read_node, uid


def empowered(app, cluster):
    principal = replace(
        app.context.principal,
        grants=app.context.principal.grants
        | {(cluster, "node.update"), (cluster, "node.history.read")},
    )
    return Core(
        replace(app.context, principal=principal),
        GitStore(app.context.repository, app.context.managed_ref),
        app.contracts,
    )


def update(app, node, **content):
    replacement = node.content.model_dump(mode="json", exclude_unset=True)
    replacement.update(content)
    request = operation(app, "node.update", dict(node_id=node.id.root, content=replacement))
    request.update(
        idempotency_key=uid(),
        expectations=[
            dict(
                resource=app.boundary.resource("node", node.id.root),
                expected_revision=node.revision.root,
            )
        ],
    )
    return request


def test_revision_chain_history_and_receipt_replay(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    created = app.submit(creation)
    identifier = creation["operations"][0]["request_id"]
    first = read_node(app, identifier).records[0].root
    request = update(app, first, body="revision two")
    generation = app.generation()
    second_receipt = app.execute(request, generation)
    second = read_node(app, identifier).records[0].root
    app.execute(update(app, second, body="revision three"), app.generation())
    third = read_node(app, identifier).records[0].root
    assert third.revision.root == 3
    assert (
        len(
            {
                first.revision_ref.revision_id.root,
                second.revision_ref.revision_id.root,
                third.revision_ref.revision_id.root,
            }
        )
        == 3
    )
    for node in (first, second):
        result = app.read(
            operation(
                app, "node.revision.read", {"revision": node.revision_ref.model_dump(mode="json")}
            )
        )
        historical = result.records[0].root
        assert historical.snapshot == node.content
        assert historical.digest.model_dump(mode="json") == digest(
            node.content.model_dump(mode="json", exclude_unset=True)
        )
    head = app.store.resolve()
    assert app.submit(creation) == created
    assert app.execute(request, generation) == second_receipt
    assert app.store.resolve() == head
    assert audit_history(app)["status"] == "verified"
    assert inspect_history(app)["status"] == "complete"


def single(app, operation):
    return dict(
        kind="batch_request",
        schema_version="1.0.0",
        instance_id=app.context.instance_id,
        transaction_id=uid(),
        idempotency_key=uid(),
        expected_generation=app.generation(),
        operations=[operation],
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing", "VALIDATION_FAILED"),
        ("duplicate", "VALIDATION_FAILED"),
        ("stale", "REVISION_CONFLICT"),
        ("digest", "REVISION_CONFLICT"),
        ("metadata", "VALIDATION_FAILED"),
        ("type", "VALIDATION_FAILED"),
        ("version", "VALIDATION_FAILED"),
        ("foreign", "NOT_FOUND"),
    ],
)
def test_update_preconditions_leave_no_effect(core, case, code):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = update(app, node, title="changed")
    if case == "missing":
        request["expectations"] = []
    if case == "duplicate":
        request["expectations"] *= 2
    if case == "stale":
        request["expectations"][0]["expected_revision"] = 2
    if case == "digest":
        request["expectations"][0]["expected_digest"] = digest("wrong")
    if case == "metadata":
        request["payload"]["content"]["properties"] = {"status": 3}
    if case == "type":
        request["payload"]["content"]["node_type"] = "unknown"
    if case == "version":
        request["payload"]["content"]["node_type_version"] = "9.0.0"
    if case == "foreign":
        request["expectations"][0]["resource"]["instance_id"] = uid()
    head = app.store.resolve()
    error(code, lambda: app.execute(request, app.generation()))
    assert app.store.resolve() == head


def test_update_only_and_separate_historical_permissions(core):
    app, cluster = core
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    principal = replace(app.context.principal, grants={(cluster, "node.update")})
    writer = Core(replace(app.context, principal=principal), app.store, app.contracts)
    request = update(writer, node, body="mutation without read")
    generation = writer.generation()
    receipt = writer.execute(request, generation)
    assert writer.execute(request, generation) == receipt
    # Replay uses original generation; mutation authority conveys no history content.
    history = operation(
        app, "node.revision.read", {"revision": node.revision_ref.model_dump(mode="json")}
    )
    for grants in ({(cluster, "node.read")}, {(cluster, "node.history.read")}, set()):
        client = Core(
            replace(app.context, principal=replace(principal, grants=grants)),
            app.store,
            app.contracts,
        )
        error("NOT_FOUND", lambda client=client: client.read(history))
    allowed = empowered(app, cluster)
    assert allowed.read(history).records[0].root.snapshot == node.content


def test_identical_fresh_replacement_and_batch_identity_rules(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    app.execute(update(app, node), app.generation())
    node = read_node(app, node.id.root).records[0].root
    assert node.revision.root == 2
    request = single(app, update(app, node))
    request["operations"].append(update(app, node))
    head = app.store.resolve()
    error("VALIDATION_FAILED", lambda: app.submit(request))
    assert app.store.resolve() == head
    create = batch(app, cluster)["operations"][0]
    request = single(app, create)
    later = update(app, node)
    later["payload"]["node_id"] = create["request_id"]
    request["operations"].append(later)
    error("VALIDATION_FAILED", lambda: app.submit(request))


def test_mixed_distinct_nodes_batch_and_restart_replay(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = single(app, update(app, node, title="updated"))
    request["operations"].append(batch(app, cluster)["operations"][0])
    receipt = app.submit(request)
    restart = Core(
        app.context, GitStore(app.context.repository, app.context.managed_ref), app.contracts
    )
    assert restart.submit(request) == receipt
    assert read_node(restart, node.id.root).records[0].root.revision.root == 2


def downgrade_projection(app, version=1):
    from second_brain_core import compact_history_index

    assert compact_history_index(app)["status"] == "compacted"
    index = app.history_index
    import sqlite3

    connection = sqlite3.connect(":memory:")
    connection.deserialize(index.database.read_bytes())
    if version == 1:
        connection.executescript(
            "DROP TABLE endpoints; DROP TABLE replay_scopes; PRAGMA user_version=1;"
        )
    raw = connection.serialize()
    index.database = index.directory / "history.sqlite3"
    index.database.write_bytes(raw)
    import hashlib

    key = index.key_path.read_bytes()
    for path in (index.checkpoint, index.enrollment):
        envelope = json.loads(path.read_bytes())
        payload = envelope["payload"]
        payload["binding"]["format"] = version
        if path == index.checkpoint:
            payload = {key: payload[key] for key in ("binding", "commit", "generation")}
            payload["database_sha256"] = hashlib.sha256(raw).hexdigest()
        path.write_bytes(
            _json(dict(payload=payload, mac=hmac.digest(key, _json(payload), "sha256").hex()))
        )


@pytest.mark.parametrize("version", [1, 2])
def test_explicit_legacy_projection_rebuild_preserves_anchor(core, version):
    app, cluster = core
    app.submit(batch(app, cluster))
    downgrade_projection(app, version)
    key = app.history_index.key_path.read_bytes()
    restart = Core(app.context, app.store, app.contracts)
    error("REPAIR_REQUIRED", restart.generation)
    assert rebuild_history_index(restart)["status"] == "rebuilt"
    assert restart.history_index.key_path.read_bytes() == key
    assert restart.generation() == app.history_index.generation


def test_warm_update_and_history_do_not_scan_chain(core, monkeypatch):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    first = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    for number in range(8):
        node = read_node(app, first.id.root).records[0].root
        app.execute(update(app, node, body=str(number)), app.generation())

    def forbidden(*args, **kwargs):
        raise AssertionError("full corpus/history path")

    monkeypatch.setattr(app.store, "ancestry", forbidden)
    monkeypatch.setattr(app.store, "read", forbidden)
    monkeypatch.setattr(app.store, "entries", forbidden)
    monkeypatch.setattr(app.history_index, "rebuild", forbidden)
    monkeypatch.setattr(app.history_index, "load", forbidden)
    app.read(
        operation(
            app, "node.revision.read", {"revision": first.revision_ref.model_dump(mode="json")}
        )
    )
    node = read_node(app, first.id.root).records[0].root
    app.execute(update(app, node, body="bounded"), app.generation())


@pytest.mark.parametrize("point", ["database", "checkpoint", "enrollment"])
def test_interrupted_format_upgrade_is_explicitly_recoverable(core, monkeypatch, point):
    import second_brain_core.history_index as module

    app, cluster = core
    app.submit(batch(app, cluster))
    downgrade_projection(app)
    restart = Core(app.context, app.store, app.contracts)
    original = module._atomic
    target = {
        "database": restart.history_index.database,
        "checkpoint": restart.history_index.checkpoint,
        "enrollment": restart.history_index.enrollment,
    }[point]

    def interrupted(path, raw):
        if path == target or (point == "database" and path.suffix == ".sqlite3"):
            raise OSError("simulated interruption")
        original(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_atomic", interrupted)
        assert rebuild_history_index(restart)["status"] == "repair_required"
    recover = Core(app.context, app.store, app.contracts)
    assert rebuild_history_index(recover)["status"] == "rebuilt"
    assert recover.generation() == app.history_index.generation


@pytest.mark.parametrize("case", ["badmac", "wronginstance", "rollback"])
def test_old_projection_anchor_rebuild_fails_closed(core, case):
    app, cluster = core
    initial = app.store.resolve()
    app.submit(batch(app, cluster))
    downgrade_projection(app)
    if case == "rollback":
        app.store.run("update-ref", app.context.managed_ref, initial, app.store.resolve())
    else:
        path = app.history_index.checkpoint
        envelope = json.loads(path.read_bytes())
        if case == "badmac":
            envelope["mac"] = "00" * 32
        else:
            envelope["payload"]["binding"]["instance"] = uid()
            envelope["mac"] = hmac.digest(
                app.history_index.key_path.read_bytes(), _json(envelope["payload"]), "sha256"
            ).hex()
        path.write_bytes(_json(envelope))
    restart = Core(app.context, app.store, app.contracts)
    assert rebuild_history_index(restart)["status"] == "repair_required"


@pytest.mark.parametrize("mutation", ["head", "membership", "revision", "receipt"])
def test_external_unsupported_changes_rejected(core, mutation):
    app, cluster = core
    app = empowered(app, cluster)
    request = batch(app, cluster)
    app.submit(request)
    identifier = request["operations"][0]["request_id"]
    files = app.store.read(app.store.resolve())
    if mutation == "head":
        path = f"knowledge/node/{identifier}.yaml"
        record = decode(files[path])
        record["content"]["title"] = "unreceipted"
        files[path] = encode(record)
    elif mutation == "membership":
        path = next(p for p in files if p.startswith("knowledge/membership/"))
        record = decode(files[path])
        record["revision"] += 1
        files[path] = encode(record)
    elif mutation == "revision":
        path = next(p for p in files if p.startswith("knowledge/node_revision/"))
        record = decode(files[path])
        record["snapshot"]["title"] = "tampered"
        files[path] = encode(record)
    else:
        path = next(p for p in files if p.startswith("control/receipts/"))
        del files[path]
        del files[path.replace("/receipts/", "/requests/")]
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    candidate = app.store.prepare(files, parent)
    app.store.publish(candidate, parent)
    error("REPAIR_REQUIRED", app.generation)


def test_publish_then_index_failure_catches_up_once(core, monkeypatch):
    app, cluster = core
    app = empowered(app, cluster)
    request = batch(app, cluster)
    app.submit(request)
    node = read_node(app, request["operations"][0]["request_id"]).records[0].root
    update_request = update(app, node, title="published")
    generation = app.generation()
    with monkeypatch.context() as patch:

        def failed(*args):
            raise OSError("index unavailable")

        patch.setattr(app.history_index, "publish", failed)
        error("REPAIR_REQUIRED", lambda: app.execute(update_request, generation))
    committed = app.store.resolve()
    restart = Core(app.context, app.store, app.contracts)
    receipt = restart.execute(update_request, generation)
    assert receipt.results[0].revisions[0].revision.root == 2
    assert restart.store.resolve() == committed
    assert read_node(restart, node.id.root).records[0].root.revision.root == 2


def test_two_writers_stale_cas_no_lost_update(core):
    app, cluster = core
    app = empowered(app, cluster)
    request = batch(app, cluster)
    app.submit(request)
    node = read_node(app, request["operations"][0]["request_id"]).records[0].root
    other = Core(
        app.context, GitStore(app.context.repository, app.context.managed_ref), app.contracts
    )
    generation = app.generation()
    app.execute(update(app, node, body="winner"), generation)
    head = app.store.resolve()
    error("REVISION_CONFLICT", lambda: other.execute(update(other, node, body="loser"), generation))
    assert app.store.resolve() == head


def test_legacy_snapshot_supplement_history_and_update(core, monkeypatch):
    from second_brain_core import apply_history_migration
    from test_core_m21_history import legacy

    app, cluster = core
    creation, _ = legacy(app, cluster, monkeypatch, metadata_only=True)
    apply_history_migration(app, inspect_history(app))
    app = empowered(app, cluster)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    historical = operation(
        app, "node.revision.read", {"revision": node.revision_ref.model_dump(mode="json")}
    )
    assert app.read(historical).records[0].root.snapshot == node.content
    app.execute(update(app, node, title="after migration"), app.generation())
    assert app.read(historical).records[0].root.snapshot == node.content
    assert inspect_history(app)["status"] == "complete"


def test_request_blob_reuse_and_bounded_transition_counts(core, monkeypatch):
    from second_brain_core.verification import TransitionVerifier

    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = update(app, node, title="one bounded update")
    generation = app.generation()
    original = app.store.blobs
    seen = []

    def blobs(oids):
        seen.extend(oids)
        return original(oids)

    transitions = []
    verify = TransitionVerifier.transition

    def transition(self, *args):
        transitions.append(args[0])
        return verify(self, *args)

    with monkeypatch.context() as patch:
        patch.setattr(app.store, "blobs", blobs)
        patch.setattr(TransitionVerifier, "transition", transition)
        receipt = app.execute(request, generation)
    assert len(transitions) == 1
    assert len(seen) == len(set(seen))
    assert len(seen) <= 20
    seen.clear()
    with monkeypatch.context() as patch:
        patch.setattr(app.store, "blobs", blobs)
        app.read(
            operation(
                app, "node.revision.read", {"revision": node.revision_ref.model_dump(mode="json")}
            )
        )
    assert len(seen) == len(set(seen))
    assert len(seen) <= 12
    seen.clear()
    with monkeypatch.context() as patch:
        patch.setattr(app.store, "blobs", blobs)
        assert app.execute(request, generation) == receipt
    assert len(seen) == len(set(seen))
    assert app.history_index.blob_cache is None


@pytest.mark.parametrize("permission", ["update", "history"])
def test_denied_private_evidence_does_not_leak_missing_bytes(core, permission):
    app, cluster = core
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    principal = replace(app.context.principal, grants=set())
    hidden = Core(replace(app.context, principal=principal), app.store, app.contracts)
    hidden.generation()
    # Remove a real requested blob after verified enrollment; denial must precede loading it.
    oid = app.store.locate(app.store.resolve(), f"knowledge/node/{node.id.root}.md")
    object_path = app.store.common / "objects" / oid[:2] / oid[2:]
    object_path.chmod(0o600)
    object_path.unlink()
    if permission == "update":
        error("NOT_FOUND", lambda: hidden.execute(update(hidden, node), hidden.generation()))
    else:
        error(
            "NOT_FOUND",
            lambda: hidden.read(
                operation(
                    hidden,
                    "node.revision.read",
                    {"revision": node.revision_ref.model_dump(mode="json")},
                )
            ),
        )


@pytest.mark.parametrize("fault", ["unknown", "wrongnode", "wronginstance", "wronglogical"])
def test_historical_exact_reference_not_found(core, fault):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    reference = node.revision_ref.model_dump(mode="json")
    if fault == "unknown":
        reference["revision_id"] = uid()
    if fault == "wrongnode":
        reference["resource"]["id"] = creation["operations"][1]["request_id"]
    if fault == "wronginstance":
        reference["resource"]["instance_id"] = uid()
    if fault == "wronglogical":
        reference["revision"] = 2
    error(
        "NOT_FOUND", lambda: app.read(operation(app, "node.revision.read", {"revision": reference}))
    )


def test_type_change_checks_incident_relations_and_mixed_batch(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    files = app.store.read(app.store.resolve())
    path = next(p for p in files if p.startswith("knowledge/node_type_definition/"))
    definition = decode(files[path])
    definition["id"] = uid()
    definition["type_key"] = "other"
    app.repository.pack(definition, files)
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    app.store.publish(app.store.prepare(files, parent), parent)
    app.generation()
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = single(app, update(app, node, node_type="other"))
    head = app.store.resolve()
    error("VALIDATION_FAILED", lambda: app.submit(request))
    assert app.store.resolve() == head
    relation = copy.deepcopy(creation["operations"][2])
    relation["request_id"] = uid()
    relation["idempotency_key"] = uid()
    relation["payload"]["relation"]["id"] = uid()
    request["operations"].append(relation)
    error("VALIDATION_FAILED", lambda: app.submit(request))
    assert app.store.resolve() == head


def test_changed_update_request_conflicts_and_replay_revocation(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = single(app, update(app, node, title="original"))
    receipt = app.submit(request)
    changed = copy.deepcopy(request)
    changed["operations"][0]["payload"]["content"]["title"] = "changed"
    head = app.store.resolve()
    error("IDEMPOTENCY_CONFLICT", lambda: app.submit(changed))
    denied = Core(
        replace(
            app.context, principal=replace(app.context.principal, grants={(cluster, "node.read")})
        ),
        app.store,
        app.contracts,
    )
    error("NOT_FOUND", lambda: denied.submit(request))
    assert app.store.resolve() == head
    assert app.submit(request) == receipt


@pytest.mark.parametrize("fault", ["previous", "digest", "logical", "actor", "timestamp"])
def test_invalid_new_update_evidence_never_publishes(core, monkeypatch, fault):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = update(app, node, title="candidate")
    prepare = app.store.prepare_delta

    def tampered(files, parent):
        files = dict(files)
        path = next(p for p in files if p.startswith("knowledge/node_revision/"))
        record = decode(files[path])
        if fault == "previous":
            record["previous"]["revision_id"] = uid()
        if fault == "digest":
            record["digest"] = digest("wrong")
        if fault == "logical":
            record["logical_revision"] = 1
        if fault == "actor":
            record["recorded_by"]["principal_id"] = uid()
        if fault == "timestamp":
            record["recorded_at"] = "2020-01-01T00:00:00Z"
        files[path] = encode(record)
        return prepare(files, parent)

    head = app.store.resolve()
    monkeypatch.setattr(app.store, "prepare_delta", tampered)
    error("REPAIR_REQUIRED", lambda: app.execute(request, app.generation()))
    assert app.store.resolve() == head


@pytest.mark.parametrize("fault", ["missing", "digest"])
def test_requested_old_history_evidence_failure_and_denial(core, monkeypatch, fault):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    first = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    for body in ("two", "three"):
        node = read_node(app, first.id.root).records[0].root
        app.execute(update(app, node, body=body), app.generation())
    request = operation(
        app, "node.revision.read", {"revision": first.revision_ref.model_dump(mode="json")}
    )
    path = f"knowledge/node_revision/{first.revision_ref.revision_id.root}.yaml"
    if fault == "missing":
        oid = app.store.locate(app.store.resolve(), path)
        target = app.store.common / "objects" / oid[:2] / oid[2:]
        target.chmod(0o600)
        target.unlink()
    else:
        original = app.history_index.raw

        def corrupt(location):
            raw = original(location)
            if location == path:
                record = decode(raw)
                record["snapshot"]["title"] = "tampered content"
                return encode(record)
            return raw

        monkeypatch.setattr(app.history_index, "raw", corrupt)
    error("REPAIR_REQUIRED", lambda: app.read(request))
    principal = replace(app.context.principal, grants={(cluster, "node.read")})
    denied = Core(replace(app.context, principal=principal), app.store, app.contracts)
    error("NOT_FOUND", lambda: denied.read(request))


@pytest.mark.parametrize("protection", ["archived", "shared", "approved", "multiple"])
def test_unsupported_protected_update_state_fails_closed(core, protection):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    request = update(app, node, title="must not apply")
    files = app.store.read(app.store.resolve())
    if protection == "archived":
        path = f"knowledge/node/{node.id.root}.yaml"
        record = decode(files[path])
        record["lifecycle"] = "archived"
    elif protection == "shared":
        path = f"knowledge/cluster/{cluster}.yaml"
        record = decode(files[path])
        record["publication_mode"] = "shared"
    else:
        path = next(
            p
            for p in files
            if p.startswith("knowledge/membership/") and decode(files[p])["node_id"] == node.id.root
        )
        record = decode(files[path])
        if protection == "approved":
            record["approved_revision"] = node.revision_ref.model_dump(mode="json")
        else:
            record["id"] = uid()
            path = f"knowledge/membership/{record['id']}.yaml"
    files[path] = encode(record)
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    app.store.publish(app.store.prepare(files, parent), parent)
    external = app.store.resolve()
    error("REPAIR_REQUIRED", lambda: app.execute(request, creation["expected_generation"]))
    assert app.store.resolve() == external


@pytest.mark.parametrize("meaning", ["type", "metadata"])
def test_versioned_meaning_cannot_change_in_place(core, meaning):
    app, cluster = core
    creation = batch(app, cluster)
    app.submit(creation)
    files = app.store.read(app.store.resolve())
    if meaning == "type":
        path = next(p for p in files if p.startswith("knowledge/node_type_definition/"))
        record = decode(files[path])
        record["description"] = "changed existing definition"
        files[path] = encode(record)
    else:
        metadata = decode(files["control/metadata.json"])
        metadata["local:note:1"]["properties"]["status"]["maxLength"] = 100
        files["control/metadata.json"] = encode(metadata)
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    app.store.publish(app.store.prepare(files, parent), parent)
    error("REPAIR_REQUIRED", app.generation)


def test_new_type_version_does_not_reinterpret_old_history(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    files = app.store.read(app.store.resolve())
    path = next(p for p in files if p.startswith("knowledge/node_type_definition/"))
    definition = decode(files[path])
    definition["id"] = uid()
    definition["type_version"] = "2.0.0"
    definition["metadata_schema_id"] = "local:note:2"
    metadata = decode(files["control/metadata.json"])
    metadata["local:note:2"] = copy.deepcopy(metadata["local:note:1"])
    files["control/metadata.json"] = encode(metadata)
    app.repository.pack(definition, files)
    files[GENERATION] = encode(app.repository.generation(files))
    parent = app.store.resolve()
    app.store.publish(app.store.prepare(files, parent), parent)
    app.execute(update(app, node, node_type_version="2.0.0"), app.generation())
    historical = (
        app.read(
            operation(
                app, "node.revision.read", {"revision": node.revision_ref.model_dump(mode="json")}
            )
        )
        .records[0]
        .root
    )
    assert historical.snapshot.node_type_version.root == "1.0.0"
    assert historical.snapshot == node.content


@pytest.mark.parametrize(
    "change",
    ["definition_removed_then_restored", "metadata_removed_then_restored", "shadow_version"],
)
def test_registered_meaning_retention_incremental_and_rebuild(core, change):
    app, cluster = core
    app.submit(batch(app, cluster))
    files = app.store.read(app.store.resolve())
    checkpoint = app.history_index.checkpoint.read_bytes()
    database = app.history_index.database.read_bytes()
    changed = dict(files)
    if change == "shadow_version":
        path = next(p for p in files if p.startswith("knowledge/node_type_definition/"))
        definition = decode(files[path])
        definition["id"] = uid()
        app.repository.pack(definition, changed)
    elif change.startswith("definition"):
        path = next(p for p in files if p.startswith("knowledge/node_type_definition/"))
        del changed[path]
    else:
        changed["control/metadata.json"] = encode({})
    changed[GENERATION] = encode(app.repository.generation(changed))
    parent = app.store.resolve()
    app.store.publish(app.store.prepare(changed, parent), parent)
    if change != "shadow_version":
        restored = dict(files)
        restored[GENERATION] = encode(app.repository.generation(restored))
        parent = app.store.resolve()
        app.store.publish(app.store.prepare(restored, parent), parent)
    error("REPAIR_REQUIRED", app.generation)
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    assert rebuild_history_index(app)["status"] == "repair_required"
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    assert app.history_index.database.read_bytes() == database


def test_history_inspection_without_index_is_read_only_and_checks_transitions(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    app.execute(update(app, node, body="updated"), app.generation())
    checkpoint = app.history_index.checkpoint.read_bytes()
    head = app.store.resolve()
    app.history_index.database.unlink()
    assert inspect_history(app)["status"] == "complete"
    assert not app.history_index.database.exists()
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    assert app.store.resolve() == head


def test_verified_update_candidate_loses_late_publication_cas(core, monkeypatch):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    other = Core(
        app.context, GitStore(app.context.repository, app.context.managed_ref), app.contracts
    )
    winner = single(other, update(other, node, body="competing winner"))
    loser = single(app, update(app, node, body="must stay unpublished"))
    parent = app.store.resolve()
    publish = app.store.publish

    def race(candidate, expected):
        # Simulate an out-of-process trusted writer at the CAS boundary. Calling
        # the internal commit under this already-held lock avoids nested locking.
        other._commit(winner)
        publish(candidate, expected)

    monkeypatch.setattr(app.store, "publish", race)
    error("REVISION_CONFLICT", lambda: app.submit(loser))
    assert app.history_index.frontier == parent
    assert app.store.resolve() == other.history_index.frontier != parent
    assert read_node(other, node.id.root).records[0].root.content.body == "competing winner"
    app.generation()
    assert app.history_index.frontier == other.history_index.frontier
    assert app.history_index.query(
        "SELECT count(*) FROM revisions WHERE resource=?", (node.id.root,)
    ) == [(2,)]
    assert not app.history_index.query(
        "SELECT 1 FROM receipts WHERE tx=?", (loser["transaction_id"],)
    )


def test_second_distinct_node_stale_update_rolls_back_whole_batch(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    nodes = [read_node(app, o["request_id"]).records[0].root for o in creation["operations"][:2]]
    request = single(app, update(app, nodes[0], title="must not apply"))
    second = update(app, nodes[1], title="invalid second")
    second["expectations"][0]["expected_revision"] = 2
    request["operations"].append(second)
    head = app.store.resolve()
    checkpoint = app.history_index.checkpoint.read_bytes()
    error("REVISION_CONFLICT", lambda: app.submit(request))
    assert app.store.resolve() == head
    assert app.history_index.checkpoint.read_bytes() == checkpoint
    assert [read_node(app, n.id.root).records[0].root for n in nodes] == nodes


def test_mixed_batch_update_cannot_replay_individually(core):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    node = read_node(app, creation["operations"][0]["request_id"]).records[0].root
    mutation = update(app, node, body="whole batch")
    request = single(app, mutation)
    request["operations"].append(batch(app, cluster)["operations"][0])
    receipt = app.submit(request)
    head = app.store.resolve()
    error("IDEMPOTENCY_CONFLICT", lambda: app.execute(mutation, app.generation()))
    assert app.store.resolve() == head
    assert app.submit(request) == receipt


@pytest.mark.parametrize("api", ["read", "submit", "execute"])
def test_unexpected_ingress_failure_is_sanitized(core, monkeypatch, api):
    from second_brain_core import CoreError

    app, cluster = core
    payload = (
        batch(app, cluster) if api == "submit" else operation(app, "node.read", {"node_id": uid()})
    )

    def broken(*args, **kwargs):
        raise RuntimeError("private ingress diagnostic")

    monkeypatch.setattr(app.boundary, "ingest", broken)
    with pytest.raises(CoreError) as caught:
        if api == "execute":
            app.execute(payload, app.generation())
        else:
            getattr(app, api)(payload)
    assert caught.value.code == "INTERNAL"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert caught.value.error.message == "INTERNAL"


def publish_unchecked_fixture(app, request, monkeypatch):
    """Construct a structurally canonical external transaction, not a public API."""
    records, metadata = app._mutation_context(request)
    files = {}
    with monkeypatch.context() as patch:
        patch.setattr(app.access, "check_expectations", lambda *args: None)
        results = [app._create(op, records, files, metadata) for op in request["operations"]]
    generation = app._next_generation(files)
    files[GENERATION] = encode(generation)
    app.receipts.record(request, generation, results, files)
    parent = app.store.resolve()
    app.store.publish(app.store.prepare_delta(files, parent), parent)


@pytest.mark.parametrize(
    "fault",
    [
        "foreign_operation",
        "foreign_expectation",
        "node_revision",
        "node_digest",
        "cluster_revision",
        "cluster_digest",
        "relation_revision",
        "relation_digest",
        "stale_overlay",
    ],
)
def test_external_operation_instance_and_all_original_cas_fail_closed(core, monkeypatch, fault):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    nodes = [read_node(app, o["request_id"]).records[0].root for o in creation["operations"][:2]]
    request = single(app, update(app, nodes[0], body="first update"))
    if fault == "foreign_operation":
        request["operations"][0]["instance_id"] = uid()
    elif fault == "foreign_expectation":
        resource = app.boundary.resource("node", nodes[1].id.root)
        resource["instance_id"] = uid()
        request["operations"][0]["expectations"].append(
            dict(resource=resource, expected_revision=1)
        )
    elif fault == "stale_overlay":
        second = update(app, nodes[1], body="second update")
        second["expectations"].append(
            dict(resource=app.boundary.resource("node", nodes[0].id.root), expected_revision=1)
        )
        request["operations"].append(second)
    else:
        kind, failure = fault.split("_")
        identifier = (
            nodes[1].id.root
            if kind == "node"
            else cluster
            if kind == "cluster"
            else creation["operations"][2]["payload"]["relation"]["id"]
        )
        expectation = dict(
            resource=app.boundary.resource(kind, identifier),
            expected_revision=999 if failure == "revision" else 1,
        )
        if failure == "digest":
            expectation["expected_digest"] = digest("wrong original bytes")
        request["operations"][0]["expectations"].append(expectation)
    checkpoint = app.history_index.checkpoint.read_bytes()
    publish_unchecked_fixture(app, request, monkeypatch)
    error("REPAIR_REQUIRED", app.generation)
    assert audit_history(app)["status"] == "repair_required"
    assert rebuild_history_index(app)["status"] == "repair_required"
    assert app.history_index.checkpoint.read_bytes() == checkpoint


@pytest.mark.parametrize("order", ["updated_first", "updated_later", "stale_overlay"])
def test_ordered_two_node_cas_uses_original_operation_prestate(core, order):
    app, cluster = core
    app = empowered(app, cluster)
    creation = batch(app, cluster)
    app.submit(creation)
    a, b = [read_node(app, o["request_id"]).records[0].root for o in creation["operations"][:2]]
    first = update(app, a, body="A2")
    second = update(app, b, body="B2")
    expectation = dict(
        resource=app.boundary.resource("node", a.id.root),
        expected_revision=2 if order == "updated_first" else 1,
    )
    if order == "updated_later":
        expectation["expected_digest"] = digest(a.model_dump(mode="json", exclude_unset=True))
    second["expectations"].append(expectation)
    request = single(app, first)
    request["operations"] = [second, first] if order == "updated_later" else [first, second]
    if order == "stale_overlay":
        head = app.store.resolve()
        error("REVISION_CONFLICT", lambda: app.submit(request))
        assert app.store.resolve() == head
        return
    receipt = app.submit(request)
    assert len(receipt.results) == 2
    auditor = Core(
        replace(app.context, principal=replace(app.context.principal, grants=set())),
        app.store,
        app.contracts,
    )
    assert audit_history(auditor)["status"] == "verified"
    assert rebuild_history_index(auditor)["status"] == "rebuilt"
    assert app.submit(request) == receipt


def test_create_then_relation_cas_observes_earlier_batch_node(core):
    app, cluster = core
    request = batch(app, cluster)
    request["operations"][2]["expectations"] = [
        dict(
            resource=app.boundary.resource("node", request["operations"][0]["request_id"]),
            expected_revision=1,
        )
    ]
    receipt = app.submit(request)
    assert len(receipt.results) == 3
    assert audit_history(app)["status"] == "verified"
    assert rebuild_history_index(app)["status"] == "rebuilt"
