"""M1.2 resource identity and immutable snapshot regressions in disposable Git."""

import copy
import importlib
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest
from second_brain_core import Core, TrustedPrincipal
from second_brain_core.codec import decode, encode
from test_core_m1 import batch, error, operation, read_node, uid

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_node_identity_batch_retry_restart_and_authorization(core):
    app, cluster = core
    request = batch(app, cluster)
    allocated = [uid(), uid()]
    for request_op, identifier in zip(request["operations"][:2], allocated, strict=True):
        request_op["payload"]["node_id"] = identifier
        assert identifier != request_op["request_id"]
    relation = request["operations"][2]["payload"]["relation"]
    relation["source"]["id"], relation["target"]["id"] = allocated
    receipt = app.submit(request)
    restarted = Core(app.context, app.store, app.contracts)
    assert restarted.submit(request) == receipt
    for identifier in allocated:
        assert read_node(restarted, identifier).records[0].root.id.root == identifier
    for request_op in request["operations"][:2]:
        error("NOT_FOUND", lambda op=request_op: read_node(restarted, op["request_id"]))
    denied_context = replace(
        app.context, principal=TrustedPrincipal(app.context.principal.principal_id)
    )
    denied = Core(denied_context, app.store, app.contracts)
    error("NOT_FOUND", lambda: denied.submit(request))
    changed = copy.deepcopy(request)
    changed["operations"][0]["payload"]["node_id"] = uid()
    error("IDEMPOTENCY_CONFLICT", lambda: restarted.submit(changed))


def test_distinct_requests_cannot_reallocate_same_explicit_node(core):
    app, cluster = core
    first = batch(app, cluster)
    identifier = uid()
    first["operations"] = first["operations"][:1]
    first["operations"][0]["payload"]["node_id"] = identifier
    app.submit(first)
    generation = app.generation()
    second = batch(app, cluster)
    second["operations"] = second["operations"][:1]
    second["operations"][0]["payload"]["node_id"] = identifier
    error("REVISION_CONFLICT", lambda: app.submit(second))
    assert app.generation() == generation


@pytest.mark.parametrize("mode", ["new", "legacy", "tampered"])
def test_node_revision_snapshot_restart_integrity_and_legacy(core, mode):
    app, cluster = core
    app.submit(batch(app, cluster))
    parent = app.store.resolve()
    files = app.store.read(parent)
    path = next(p for p in files if p.startswith("knowledge/node_revision/"))
    revision = decode(files[path])
    assert "snapshot" in revision
    if mode == "legacy":
        del revision["snapshot"]
    elif mode == "tampered":
        revision["snapshot"]["body"] += "changed historical bytes"
    files[path] = encode(revision)
    generation = app.repository.generation(files)
    files["control/generation.json"] = encode(generation)
    app.store.publish(app.store.prepare(files, parent), parent)
    restarted = Core(app.context, app.store, app.contracts)
    # Removing a snapshot from a newly marked history is corruption, not legacy.
    # Actual metadata-only legacy origins are covered by the M2.1 migration suite.
    if mode in {"tampered", "legacy"}:
        error("REPAIR_REQUIRED", restarted.generation)
    else:
        assert restarted.generation()


def test_m12_catalogue_and_canonical_coverage_references():
    """Check inventory references/coverage, not the truth of semantic claims."""
    catalogue = (ROOT / "docs/domain/operations-catalog.md").read_text(encoding="utf-8")
    names = set()
    for line in catalogue.splitlines():
        if line.startswith("| `"):
            names.update(re.findall(r"`([^`]+)`", line.split("|")[1]))
    matrix = (ROOT / "docs/contracts/contract-coverage-matrix.md").read_text(encoding="utf-8")
    covered = set(re.findall(r"\| CAP-\d+ \| `([^`]+)`", matrix))
    assert names <= covered
    ids = re.findall(r"\| (CAP-\d+) \|", matrix)
    assert len(ids) == len(set(ids)) == 101
    operations = json.loads((ROOT / "contracts/schemas/v1/operations.schema.json").read_text())
    for definition in operations["$defs"].values():
        operation = definition.get("properties", {}).get("operation", {}).get("const")
        if operation:
            assert operation in covered
    schemas = {
        p.name: json.loads(p.read_text())
        for p in (ROOT / "contracts/schemas/v1").glob("*.schema.json")
    }
    for filename, definition in re.findall(r"([a-z]+\.schema\.json)#/\$defs/(\w+)", matrix):
        assert definition in schemas[filename]["$defs"]
    aliases = {
        "O": "operations",
        "T": "transaction",
        "K": "knowledge",
        "C": "control",
        "G": "governance",
        "S": "snapshots",
        "A": "authoring",
    }
    for alias, definition in re.findall(r"([OTKCGSA])#/\$defs/(\w+)", matrix):
        assert definition in schemas[aliases[alias] + ".schema.json"]["$defs"]
    for family, model in re.findall(r"generated\.v1\.([a-z]+)_schema\.(\w+)", matrix):
        assert hasattr(importlib.import_module("generated.v1." + family + "_schema"), model)
    for family, model in re.findall(r"`([a-z]+)\.js:(\w+)`", matrix):
        typescript = (ROOT / "packages/typescript/generated/v1" / (family + ".d.ts")).read_text()
        assert re.search(r"export (?:interface|type|enum) " + model + r"\b", typescript)
    decisions = (ROOT / "docs/domain/accepted-decisions.md").read_text(encoding="utf-8")
    requirements = re.findall(r"\| (M12-[A-Z]+-\d+) \|", decisions)
    assert len(requirements) == len(set(requirements)) == 135
    deferred = (ROOT / "docs/contracts/contract-gaps.md").read_text(encoding="utf-8")
    assert set(ids) == set(re.findall(r"\| (CAP-\d+) \|", deferred))
    for milestone in range(2, 9):
        assert f"## DF-M{milestone}" in deferred
    for field in (
        "Prerequisites:",
        "Owner decision:",
        "Activation / planned conformance:",
        "Compatibility/migration risk:",
    ):
        assert deferred.count(field) == 7


@pytest.mark.parametrize("kind", ["node", "relation"])
def test_historical_read_contracts_do_not_enable_runtime_history(core, kind):
    app, cluster = core
    receipt = app.submit(batch(app, cluster))
    revision = next(
        revision
        for result in receipt.results
        for revision in result.revisions
        if revision.resource.resource_kind == kind
    )
    request = operation(
        app, kind + ".revision.read", {"revision": revision.model_dump(mode="json")}
    )
    app.contracts.parse("operations", request)
    error("VALIDATION_FAILED", lambda: app.read(request))


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("visible", [False, True])
def test_node_collision_conceals_inaccessible_identity_and_is_atomic(core, explicit, visible):
    app, cluster = core
    original = batch(app, cluster)
    app.submit(original)
    identifier = original["operations"][0]["request_id"]
    actions = {"node.create", "membership.admit"}
    if visible:
        actions.add("node.read")
    context = replace(
        app.context,
        principal=replace(
            app.context.principal, grants=frozenset((cluster, action) for action in actions)
        ),
    )
    creator = Core(context, app.store, app.contracts)
    request = batch(creator, cluster)
    request["operations"] = request["operations"][:2]
    fresh_identifier = request["operations"][0]["request_id"]
    duplicate = request["operations"][1]
    if explicit:
        duplicate["payload"]["node_id"] = identifier
    else:
        duplicate["request_id"] = identifier
    before = creator.generation()
    error("REVISION_CONFLICT" if visible else "NOT_FOUND", lambda: creator.submit(request))
    assert creator.generation() == before
    error("NOT_FOUND", lambda: read_node(app, fresh_identifier))
    # Creation does not acquire an implicit read requirement for a fresh identity.
    fresh = batch(creator, cluster)
    fresh["operations"] = fresh["operations"][:1]
    if explicit:
        fresh["operations"][0]["payload"]["node_id"] = uid()
    assert creator.submit(fresh)


@pytest.mark.parametrize("visible", [False, True])
def test_relation_collision_uses_relation_and_endpoint_visibility(core, visible):
    app, cluster = core
    original = batch(app, cluster)
    app.submit(original)
    actions = {"relation.create", "node.read"}
    if visible:
        actions.add("relation.read")
    context = replace(
        app.context,
        principal=replace(
            app.context.principal, grants=frozenset((cluster, action) for action in actions)
        ),
    )
    creator = Core(context, app.store, app.contracts)
    request = batch(creator, cluster)
    duplicate = copy.deepcopy(original["operations"][2])
    duplicate["request_id"], duplicate["idempotency_key"] = uid(), uid()
    request["operations"] = [duplicate]
    before = creator.generation()
    error("REVISION_CONFLICT" if visible else "NOT_FOUND", lambda: creator.submit(request))
    assert creator.generation() == before
    fresh = copy.deepcopy(request)
    fresh["transaction_id"], fresh["idempotency_key"] = uid(), uid()
    fresh["operations"][0]["payload"]["relation"]["id"] = uid()
    assert creator.submit(fresh)
