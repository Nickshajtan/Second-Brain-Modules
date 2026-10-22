"""Real disposable Git repositories exercise the public M1 boundary."""

import copy
import subprocess
import sys
from dataclasses import replace
from uuid import uuid4

import pytest
from generated.v1.knowledge_schema import Node, Relation
from second_brain_contracts import ContractValidator
from second_brain_core import Core, CoreError, GitStore, InstanceContext, TrustedPrincipal
from second_brain_core.codec import decode, encode
from second_brain_core.git_store import StorageError


def uid():
    return str(uuid4())


def ref(instance, identifier, kind="node"):
    return dict(instance_id=instance, resource_kind=kind, id=identifier)


@pytest.fixture(scope="module")
def contracts():
    return ContractValidator()


@pytest.fixture
def core(tmp_path, contracts):
    path = tmp_path / "managed repo with spaces"
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    instance, principal, cluster = uid(), uid(), uid()
    grants = frozenset(
        (cluster, a)
        for a in (
            "node.create",
            "membership.admit",
            "node.read",
            "relation.create",
            "relation.read",
        )
    )
    context = InstanceContext(
        instance, path, "refs/heads/brain", TrustedPrincipal(principal, grants, True)
    )
    app = Core(context, GitStore(path, context.managed_ref), contracts)
    records = [
        dict(
            kind="cluster",
            id=cluster,
            schema_version="1.0.0",
            revision=1,
            name="Приватний",
            owner={"principal_id": principal},
            policy={"policy_id": uid(), "version": 1},
            publication_mode="private",
            lifecycle="active",
        ),
        dict(
            kind="node_type_definition",
            id=uid(),
            schema_version="1.0.0",
            revision=1,
            type_key="note",
            type_version="1.0.0",
            metadata_schema_id="local:note:1",
            description="Fabricated note",
            flat_properties_required=True,
        ),
        dict(
            kind="relation_type_definition",
            id=uid(),
            schema_version="1.0.0",
            revision=1,
            predicate="supports",
            type_version="1.0.0",
            symmetric=False,
            source_node_types=["note"],
            target_node_types=["note"],
            self_links_allowed=False,
            description="Fabricated predicate",
        ),
    ]
    app.bootstrap(
        records,
        {
            "local:note:1": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
                "additionalProperties": False,
            }
        },
    )
    return app, cluster


def operation(app, action, payload):
    value = dict(
        schema_version="1.0.0",
        operation=action,
        operation_version="1.0.0",
        request_id=uid(),
        instance_id=app.context.instance_id,
        payload=payload,
    )
    if action.endswith("create"):
        value.update(idempotency_key=uid(), expectations=[])
    return value


def batch(app, cluster):
    content = dict(
        node_type="note",
        node_type_version="1.0.0",
        title="Знання 🧠",
        body="Україна\r\n---\n\u0065\u0301\n",
        properties={"status": "draft"},
        provenance=[],
    )
    a = operation(
        app, "node.create", dict(target_cluster_id=cluster, content=copy.deepcopy(content))
    )
    b = operation(
        app, "node.create", dict(target_cluster_id=cluster, content=copy.deepcopy(content))
    )
    relation = dict(
        kind="relation",
        schema_version="1.0.0",
        id=uid(),
        revision=1,
        owner_cluster_id=cluster,
        source=ref(app.context.instance_id, a["request_id"]),
        target=ref(app.context.instance_id, b["request_id"]),
        predicate="supports",
        predicate_version="1.0.0",
        provenance=[],
        lifecycle="active",
    )
    r = operation(app, "relation.create", {"relation": relation})
    return dict(
        kind="batch_request",
        schema_version="1.0.0",
        instance_id=app.context.instance_id,
        transaction_id=uid(),
        idempotency_key=uid(),
        expected_generation=app.generation(),
        operations=[a, b, r],
    )


def read_node(app, identifier, **selection):
    return app.read(operation(app, "node.read", dict(node_id=identifier, **selection)))


def error(code, fn):
    with pytest.raises(CoreError) as caught:
        fn()
    assert caught.value.code == code
    assert caught.value.error.message == code


def test_atomic_vertical_slice_and_committed_reads(core):
    app, cluster = core
    request = batch(app, cluster)
    before = app.store.resolve()
    result = app.submit(request)
    after = app.store.resolve()
    assert before != after
    assert app.store.run("rev-parse", after + "^").strip() == before
    assert len(result.results) == 3
    a = request["operations"][0]["request_id"]
    read = read_node(app, a)
    node = read.records[0].root
    assert isinstance(node, Node)
    assert node.content.body == request["operations"][0]["payload"]["content"]["body"]
    assert read.generation == result.generation
    relation_id = request["operations"][2]["payload"]["relation"]["id"]
    relation_read = app.read(operation(app, "relation.read", {"relation_id": relation_id}))
    assert isinstance(relation_read.records[0].root, Relation)
    assert read_node(app, a).records[0].root.revision_ref == node.revision_ref
    # Uncommitted edits and arbitrary untracked files never enter Core reads/writes.
    target = app.context.repository / f"knowledge/node/{a}.md"
    target.parent.mkdir(parents=True)
    target.write_text("unaccepted edits", encoding="utf-8")
    (app.context.repository / "untracked-secret").write_text("private", encoding="utf-8")
    assert read_node(app, a).records[0].root.content.body == node.content.body
    files = app.store.read(after)
    assert "untracked-secret" not in files
    assert len([p for p in files if p.startswith("knowledge/membership/")]) == 2


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("missing_endpoint", "NOT_FOUND"),
        ("foreign_endpoint", "NOT_FOUND"),
        ("unknown_type", "VALIDATION_FAILED"),
        ("unknown_predicate", "VALIDATION_FAILED"),
        ("metadata", "VALIDATION_FAILED"),
        ("inverted_time", "VALIDATION_FAILED"),
        ("self_link", "VALIDATION_FAILED"),
        ("bad_revision", "VALIDATION_FAILED"),
        ("unknown_field", "VALIDATION_FAILED"),
        ("wrong_version", "VALIDATION_FAILED"),
        ("duplicate_request", "VALIDATION_FAILED"),
        ("stale_revision", "REVISION_CONFLICT"),
        ("foreign_operation", "NOT_FOUND"),
        ("unauthorized_cluster", "NOT_FOUND"),
    ],
)
def test_invalid_batch_has_zero_committed_effects(core, mutation, code):
    app, cluster = core
    request = batch(app, cluster)
    a, b, r = request["operations"]
    relation = r["payload"]["relation"]
    if mutation == "missing_endpoint":
        relation["target"]["id"] = uid()
    elif mutation == "foreign_endpoint":
        relation["target"]["instance_id"] = uid()
    elif mutation == "unknown_type":
        b["payload"]["content"]["node_type"] = "unknown"
    elif mutation == "unknown_predicate":
        relation["predicate"] = "unknown"
    elif mutation == "metadata":
        b["payload"]["content"]["properties"] = {}
    elif mutation == "inverted_time":
        relation.update(valid_from="2026-02-01T00:00:00Z", valid_until="2026-01-01T00:00:00Z")
    elif mutation == "self_link":
        relation["target"] = relation["source"]
    elif mutation == "bad_revision":
        relation["revision"] = 2
    elif mutation == "unknown_field":
        b["owner"] = uid()
    elif mutation == "wrong_version":
        b["operation_version"] = "2.0.0"
    elif mutation == "duplicate_request":
        b["request_id"] = a["request_id"]
    elif mutation == "stale_revision":
        a["expectations"] = [
            {"resource": ref(app.context.instance_id, cluster, "cluster"), "expected_revision": 2}
        ]
    elif mutation == "foreign_operation":
        b["instance_id"] = uid()
    elif mutation == "unauthorized_cluster":
        b["payload"]["target_cluster_id"] = uid()
    before = app.store.resolve()
    error(code, lambda: app.submit(request))
    assert app.store.resolve() == before
    assert not any(p.startswith("knowledge/node/") for p in app.store.read(before))


def test_retry_restart_and_changed_payload(core):
    app, cluster = core
    request = batch(app, cluster)
    first = app.submit(request)
    head = app.store.resolve()
    restarted = Core(
        app.context, GitStore(app.context.repository, app.context.managed_ref), app.contracts
    )
    assert restarted.submit(request) == first
    assert app.store.resolve() == head
    changed = copy.deepcopy(request)
    changed["operations"][0]["payload"]["content"]["title"] = "changed"
    error("IDEMPOTENCY_CONFLICT", lambda: restarted.submit(changed))
    assert app.store.resolve() == head
    # A separate interpreter has no access to any in-memory Core state.
    script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'packages/python'))
from second_brain_core import Core, GitStore, InstanceContext, TrustedPrincipal
from second_brain_core.codec import decode, encode
config, request = decode(sys.stdin.buffer.read())
principal = TrustedPrincipal(config['principal'], frozenset(map(tuple, config['grants'])))
context = InstanceContext(config['instance'], Path(config['repository']), config['ref'], principal)
core = Core(context, GitStore(context.repository, context.managed_ref))
receipt = core.submit(request)
sys.stdout.buffer.write(encode(core.contracts.dump('transaction', receipt)))
"""
    config = dict(
        principal=app.context.principal.principal_id,
        grants=sorted(app.context.principal.grants),
        instance=app.context.instance_id,
        repository=str(app.context.repository),
        ref=app.context.managed_ref,
    )
    child = subprocess.run(
        [sys.executable, "-I", "-c", script, str(app.contracts.root)],
        input=encode([config, request]),
        capture_output=True,
        cwd=app.context.repository,
    )
    assert child.returncode == 0, child.stderr.decode()
    assert decode(child.stdout) == app.contracts.dump("transaction", first)
    assert app.store.resolve() == head


def test_stale_generation_and_entity_collision(core):
    app, cluster = core
    first, stale = batch(app, cluster), batch(app, cluster)
    app.submit(first)
    error("REVISION_CONFLICT", lambda: app.submit(stale))
    collision = batch(app, cluster)
    collision["operations"][0]["request_id"] = first["operations"][0]["request_id"]
    error("REVISION_CONFLICT", lambda: app.submit(collision))


def test_direct_calls_authorization_and_receipt_revocation(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    denied_context = replace(
        app.context, principal=TrustedPrincipal(app.context.principal.principal_id)
    )
    denied = Core(denied_context, app.store, app.contracts)
    error("NOT_FOUND", lambda: read_node(denied, request["operations"][0]["request_id"]))
    error("NOT_FOUND", lambda: read_node(denied, uid()))
    error("NOT_FOUND", lambda: denied.submit(request))
    error("NOT_FOUND", lambda: denied.submit(batch(app, cluster)))
    error("FORBIDDEN", lambda: denied.bootstrap([], {}))
    relation_id = request["operations"][2]["payload"]["relation"]["id"]
    partial = replace(
        app.context,
        principal=replace(app.context.principal, grants=frozenset({(cluster, "relation.read")})),
    )
    reader = Core(partial, app.store, app.contracts)
    error(
        "NOT_FOUND",
        lambda: reader.read(operation(app, "relation.read", {"relation_id": relation_id})),
    )


@pytest.mark.parametrize("phase", ["before", "after"])
def test_failure_publication_boundary_recovers(core, monkeypatch, phase):
    app, cluster = core
    request = batch(app, cluster)
    before = app.store.resolve()
    publish = app.store.publish

    def fail(candidate, expected):
        if phase == "after":
            publish(candidate, expected)
        raise StorageError("simulated transport failure")

    monkeypatch.setattr(app.store, "publish", fail)
    error("REPAIR_REQUIRED", lambda: app.submit(request))
    if phase == "before":
        assert app.store.resolve() == before
        error("NOT_FOUND", lambda: read_node(app, request["operations"][0]["request_id"]))
    else:
        assert app.store.resolve() != before
        assert read_node(app, request["operations"][0]["request_id"])
    monkeypatch.setattr(app.store, "publish", publish)
    restarted = Core(app.context, app.store, app.contracts)
    head = app.store.resolve()
    result = restarted.submit(request)
    assert result.status == "committed"
    if phase == "after":
        assert app.store.resolve() == head


def test_expected_old_ref_rejects_competing_writer(core, monkeypatch):
    app, cluster = core
    request = batch(app, cluster)
    original = app.store.publish

    def race(candidate, expected):
        competing = app.store.prepare(app.store.read(expected), expected)
        original(competing, expected)
        original(candidate, expected)

    monkeypatch.setattr(app.store, "publish", race)
    error("REVISION_CONFLICT", lambda: app.submit(request))
    error("NOT_FOUND", lambda: read_node(app, request["operations"][0]["request_id"]))


def test_prepared_objects_invisible_and_missing_committed_blob_fails_closed(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    current = app.store.resolve()
    candidate_files = app.store.read(current)
    candidate_files["unpublished"] = b"ignored"
    candidate = app.store.prepare(candidate_files, current)
    assert candidate != current
    assert app.store.resolve() == current
    assert app.generation()
    node_path = f"knowledge/node/{request['operations'][0]['request_id']}.md"
    oid = app.store.run("rev-parse", f"{current}:{node_path}").strip()
    blob = app.store.common / "objects" / oid[:2] / oid[2:]
    blob.chmod(0o600)  # Git loose objects are read-only on Windows.
    blob.unlink()
    error("REPAIR_REQUIRED", app.generation)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}',
        b"x: 1\nx: 2",
        b"!!python/object:evil {}",
        b"x: &anchor [*anchor]",
        b'{"x":1e999}',
    ],
)
def test_strict_managed_yaml_subset(raw):
    with pytest.raises(ValueError):
        decode(raw)


def test_ingress_generated_models_revalidated_and_null_rejected(core):
    app, cluster = core
    request = batch(app, cluster)
    model = app.contracts.parse("transaction", request).root
    model.operations[0].root.payload.content.title = ""  # Pydantic assignment isn't validation.
    error("VALIDATION_FAILED", lambda: app.submit(model))
    request["operations"][0]["payload"]["content"]["metadata_schema_id"] = None
    error("VALIDATION_FAILED", lambda: app.submit(request))
    error(
        "VALIDATION_FAILED", lambda: app.submit('{"kind":"batch_request","kind":"batch_request"}')
    )


def test_instances_are_explicit_and_isolated(core, tmp_path):
    app, cluster = core
    path = tmp_path / "other"
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    context = replace(app.context, repository=path, instance_id=uid())
    other = Core(context, GitStore(path, context.managed_ref), app.contracts)
    # Explicitly initialize a separate instance with only its own desired registry.
    _, _, _, records, metadata = app.repository.snapshot()
    other.bootstrap(list(records.values()), metadata)
    assert other.store.common != app.store.common
    request = batch(app, cluster)
    app.submit(request)
    error("NOT_FOUND", lambda: other.submit(request))
    error("NOT_FOUND", lambda: read_node(other, request["operations"][0]["request_id"]))
    mismatched = Core(replace(app.context, instance_id=uid()), app.store, app.contracts)
    error("REPAIR_REQUIRED", mismatched.generation)


def test_committed_corrupt_metadata_and_foreign_generation_rejected(core):
    app, _ = core
    parent = app.store.resolve()
    files = app.store.read(parent)
    generation = decode(files["control/generation.json"])
    generation["instance_id"] = uid()
    files["control/generation.json"] = encode(generation)
    app.store.publish(app.store.prepare(files, parent), parent)
    error("REPAIR_REQUIRED", app.generation)


def test_single_typed_operation_and_retry_without_read_grant(core):
    app, cluster = core
    request = batch(app, cluster)
    node_op = app.contracts.parse("operations", request["operations"][0]).root
    context = replace(
        app.context,
        principal=replace(
            app.context.principal,
            grants=frozenset({(cluster, "node.create"), (cluster, "membership.admit")}),
        ),
    )
    creator = Core(context, app.store, app.contracts)
    generation = app.generation()
    receipt = creator.execute(node_op, generation)
    head = app.store.resolve()
    assert creator.execute(node_op, generation) == receipt
    assert app.store.resolve() == head
    error("NOT_FOUND", lambda: read_node(creator, request["operations"][0]["request_id"]))


def test_constituent_idempotency_key_cannot_be_replayed_in_new_batch(core):
    app, cluster = core
    first = batch(app, cluster)
    app.submit(first)
    second = batch(app, cluster)
    second["operations"][0]["idempotency_key"] = first["operations"][0]["idempotency_key"]
    head = app.store.resolve()
    error("IDEMPOTENCY_CONFLICT", lambda: app.submit(second))
    assert app.store.resolve() == head
    error("NOT_FOUND", lambda: read_node(app, second["operations"][0]["request_id"]))


def test_actor_isolation_for_same_idempotency_key(core):
    app, cluster = core
    first = batch(app, cluster)
    app.submit(first)
    other_context = replace(
        app.context, principal=replace(app.context.principal, principal_id=uid())
    )
    other = Core(other_context, app.store, app.contracts)
    second = batch(other, cluster)
    second["idempotency_key"] = first["idempotency_key"]
    assert other.submit(second).actor.principal_id.root == other_context.principal.principal_id


@pytest.mark.parametrize(
    "corruption", ["receipt_digest", "missing_request", "metadata_ref", "duplicate_yaml"]
)
def test_restart_rejects_corrupt_committed_control_or_knowledge(core, corruption):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    parent = app.store.resolve()
    files = app.store.read(parent)
    receipt_path = next(p for p in files if p.startswith("control/receipts/"))
    if corruption == "receipt_digest":
        receipt = decode(files[receipt_path])
        receipt["request_digest"]["value"] = "0" * 64
        files[receipt_path] = encode(receipt)
    elif corruption == "missing_request":
        del files[receipt_path.replace("/receipts/", "/requests/")]
    elif corruption == "metadata_ref":
        files["control/metadata.json"] = encode(
            {"local:note:1": {"$ref": "https://invalid.example"}}
        )
        generation = decode(files["control/generation.json"])
        generation["digest"] = app.repository.generation(files)["digest"]
        files["control/generation.json"] = encode(generation)
    elif corruption == "duplicate_yaml":
        path = next(p for p in files if p.startswith("knowledge/node/") and p.endswith(".yaml"))
        files[path] = b'{"kind":"node","kind":"node"}'
        generation = decode(files["control/generation.json"])
        generation["digest"] = app.repository.generation(files)["digest"]
        files["control/generation.json"] = encode(generation)
    app.store.publish(app.store.prepare(files, parent), parent)
    restarted = Core(app.context, app.store, app.contracts)
    error("REPAIR_REQUIRED", restarted.generation)


def test_ajv_independently_accepts_actual_core_outputs(core):
    app, cluster = core
    request = batch(app, cluster)
    receipt = app.submit(request)
    read = read_node(app, request["operations"][0]["request_id"])
    payloads = [app.contracts.dump("transaction", model) for model in (receipt, read)]
    script = """
        import {loadContracts} from './packages/typescript/validation.mjs';
        import fs from 'node:fs';
        const contracts = await loadContracts(process.cwd());
        for (const payload of JSON.parse(fs.readFileSync(0, 'utf8'))) {
            contracts.validate('transaction', payload);
        }
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=encode(payloads),
        capture_output=True,
        cwd=app.contracts.root,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_cross_cluster_relation_requires_both_endpoint_grants(core, tmp_path):
    app, cluster = core
    _, _, _, registry, metadata = app.repository.snapshot()
    other_cluster = copy.deepcopy(registry["cluster", cluster])
    other_cluster["id"] = uid()
    path = tmp_path / "two private clusters"
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    grants = app.context.principal.grants | frozenset(
        (other_cluster["id"], action) for _, action in app.context.principal.grants
    )
    context = replace(
        app.context,
        instance_id=uid(),
        repository=path,
        principal=replace(app.context.principal, grants=grants),
    )
    full = Core(context, GitStore(path, context.managed_ref), app.contracts)
    full.bootstrap([*registry.values(), other_cluster], metadata)
    request = batch(full, cluster)
    request["operations"][1]["payload"]["target_cluster_id"] = other_cluster["id"]
    full.submit(request)
    relation = request["operations"][2]["payload"]["relation"]
    assert full.read(operation(full, "relation.read", {"relation_id": relation["id"]}))
    limited = Core(
        replace(context, principal=replace(context.principal, grants=app.context.principal.grants)),
        full.store,
        full.contracts,
    )
    error(
        "NOT_FOUND",
        lambda: limited.read(operation(limited, "relation.read", {"relation_id": relation["id"]})),
    )
    retry_relation = copy.deepcopy(relation)
    retry_relation["id"] = uid()
    create = operation(limited, "relation.create", {"relation": retry_relation})
    generation, head = full.generation(), full.store.resolve()
    error("NOT_FOUND", lambda: limited.execute(create, generation))
    assert full.store.resolve() == head


def test_unsupported_operation_never_reaches_a_creation_or_read_strategy(core):
    app, cluster = core
    request = batch(app, cluster)
    create = request["operations"][0]
    update = dict(
        create,
        operation="node.update",
        payload={
            "node_id": create["request_id"],
            "content": create["payload"]["content"],
        },
    )
    # This is a valid registered contract, but intentionally unsupported by M1.
    app.contracts.validate("operations", update)
    before = app.store.resolve()
    error("VALIDATION_FAILED", lambda: app.read(update))
    error("VALIDATION_FAILED", lambda: app.execute(update, request["expected_generation"]))
    request["operations"] = [update]
    error("VALIDATION_FAILED", lambda: app.submit(request))
    assert app.store.resolve() == before


def test_node_read_strategy_checks_explicit_revision_and_cluster(core):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)
    identifier = request["operations"][0]["request_id"]
    node = read_node(app, identifier).records[0].root
    revision = node.revision_ref.model_dump(mode="json")
    assert read_node(app, identifier, revision=revision, selected_cluster_id=cluster)
    revision["revision_id"] = uid()
    error("NOT_FOUND", lambda: read_node(app, identifier, revision=revision))
    error("NOT_FOUND", lambda: read_node(app, identifier, selected_cluster_id=uid()))


def test_git_adapter_keeps_blob_io_binary(core):
    app, _ = core
    parent = app.store.resolve()
    payload = b"\xff\x00\r\n\n\x80"
    candidate = app.store.prepare({"fabricated-blob": payload}, parent)
    assert app.store.read(candidate) == {"fabricated-blob": payload}
    assert app.store.resolve() == parent
