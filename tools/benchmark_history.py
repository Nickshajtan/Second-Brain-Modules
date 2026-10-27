"""Disposable history benchmark; counters are observations, never time guarantees."""

from __future__ import annotations

# Callbacks below execute synchronously before their enclosing loop advances.
# ruff: noqa: B023
import argparse
import copy
import cProfile
import hashlib
import json
import os
import platform
import pstats
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, suppress
from dataclasses import replace
from functools import partial
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/python"))
sys.path.insert(0, str(ROOT / "tests"))

from conftest import core as core_fixture  # noqa: E402
from second_brain_contracts import ContractValidator  # noqa: E402
from second_brain_core import (  # noqa: E402
    Core,
    CoreError,
    GitStore,
    audit_history,
    inspect_history,
    rebuild_history_index,
)
from second_brain_core.boundary import GENERATION  # noqa: E402
from second_brain_core.codec import encode  # noqa: E402
from second_brain_core.domain import DomainRules  # noqa: E402
from second_brain_core.verification import TransitionVerifier  # noqa: E402
from test_core_m1 import batch, operation, uid  # noqa: E402


class BudgetExceeded(RuntimeError):
    pass


def extend(app, cluster, count: int, *, varied: bool = False) -> dict[str, object]:
    """Fixture bulk plumbing; every twentieth commit runs existing create strategies."""
    parent = app.store.resolve()
    files = app.store.read(parent)
    generation, records, metadata = app.repository.parse_tree(files)
    stream = bytearray()
    for number in range(count):
        before = set(files)
        if number % 20 == 0:
            with patch.object(app, "generation", return_value=generation):
                request = batch(app, cluster)
            if varied:
                for offset, op in enumerate(request["operations"][:2]):
                    op["payload"]["content"]["body"] = (
                        "fixture note\n" * (16, 256, 1024)[(number // 20 + offset) % 3]
                    )
            results = [app._create(op, records, files, metadata) for op in request["operations"]]
            generation = app.repository.generation(files)
            app.receipts.record(request, generation, results, files)
        else:
            generation = dict(generation, generation_id=str(UUID(int=number + 1, version=4)))
        files[GENERATION] = encode(generation)
        stream.extend(
            f"commit {app.store.ref}\nmark :{number + 1}\ncommitter Benchmark <bench@localhost> {1700000000 + number} +0000\ndata 7\nfixture\nfrom {parent}\n".encode()
        )
        for path in sorted((set(files) - before) | {GENERATION}):
            raw = files[path]
            stream.extend(f"M 100644 inline {path}\ndata {len(raw)}\n".encode())
            stream.extend(raw + b"\n")
        stream.extend(b"\n")
        # fast-import's branch identity names the immediately preceding commit.
        parent = f":{number + 1}"
    if stream:
        app.store.run("fast-import", "--quiet", data=bytes(stream))
    return generation


def measure(app, name, callback, limit: int) -> dict[str, object]:
    counts = dict(
        git_processes=0,
        blob_reads=0,
        trees_read=0,
        commits_traversed=0,
        records_validated=0,
        receipts_validated=0,
    )
    original_run = app.store._run_bytes
    original_read = app.store.read
    original_ancestry = app.store.ancestry
    original_parse = app.contracts.parse
    original_pair = app.receipts.validate_pair
    exhausted = False

    def run(*args, **kwargs):
        nonlocal exhausted
        if counts["git_processes"] >= limit:
            exhausted = True
            raise BudgetExceeded("Git subprocess budget reached")
        counts["git_processes"] += 1
        counts["blob_reads"] += int(args[:2] == ("cat-file", "blob"))
        return original_run(*args, **kwargs)

    def read(commit):
        counts["trees_read"] += 1
        return original_read(commit)

    def ancestry(commit):
        result = original_ancestry(commit)
        counts["commits_traversed"] += len(result)
        return result

    def parse(family, payload):
        counts["records_validated"] += 1
        return original_parse(family, payload)

    def pair(*args):
        counts["receipts_validated"] += 1
        return original_pair(*args)

    started = time.perf_counter()
    status, detail = "complete", None
    with (
        patch.object(app.store, "_run_bytes", run),
        patch.object(app.store, "read", read),
        patch.object(app.store, "ancestry", ancestry),
        patch.object(app.contracts, "parse", parse),
        patch.object(app.receipts, "validate_pair", pair),
    ):
        try:
            callback()
        except Exception as exc:
            # Public boundaries sanitize the intentional budget exception; retain its cause.
            cause = exc
            while cause.__cause__ is not None:
                cause = cause.__cause__
            status = "budget_exhausted" if isinstance(cause, BudgetExceeded) else "failed"
            detail = type(cause).__name__
    if exhausted:
        status, detail = "budget_exhausted", "BudgetExceeded"
    return dict(
        operation=name,
        status=status,
        detail=detail,
        elapsed_seconds=round(time.perf_counter() - started, 6),
        **counts,
    )


def memory_peak() -> int | None:
    """Process-lifetime native+Python working-set high-water mark, not per-call allocation."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in ("peak", "working", "qpeak", "q", "ppeak", "p", "page", "pagepeak")
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess
    process.restype = wintypes.HANDLE
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not get_memory(process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.peak or None


def optimized_measure(app, name, mode, callback, limit):
    counts = dict(
        git_processes=0,
        blob_reads=0,
        duplicate_blob_requests=0,
        trees_read=0,
        tree_enumerations=0,
        commits_traversed=0,
        commits_enumerated=0,
        records_validated=0,
        domain_records_checked=0,
        receipts_validated=0,
        sqlite_statements=0,
    )
    methods = {
        key: getattr(GitStore, key)
        for key in ("_run_bytes", "blobs", "read", "entries", "changes", "ancestry")
    }
    parse, pair = ContractValidator.parse, type(app.receipts).validate_pair
    transition, connect = TransitionVerifier.transition, sqlite3.connect
    domain_validate = DomainRules.validate
    connections = []
    seen_blobs = set()

    def sql(_statement):
        counts["sqlite_statements"] += 1

    def traced_connect(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connection.set_trace_callback(sql)
        connections.append(connection)
        return connection

    def run(store, *args, **kwargs):
        if counts["git_processes"] >= limit:
            raise BudgetExceeded("Git subprocess budget reached")
        counts["git_processes"] += 1
        return methods["_run_bytes"](store, *args, **kwargs)

    def blobs(store, oids):
        counts["blob_reads"] += len(oids)
        for oid in oids:
            if oid in seen_blobs:
                counts["duplicate_blob_requests"] += 1
            seen_blobs.add(oid)
        return methods["blobs"](store, oids)

    def read(store, commit):
        counts["trees_read"] += 1
        return methods["read"](store, commit)

    def entries(store, commit):
        counts["tree_enumerations"] += 1
        return methods["entries"](store, commit)

    def changes(store, *args, **kwargs):
        result = methods["changes"](store, *args, **kwargs)
        counts["commits_enumerated"] += len(result)
        return result

    def ancestry(store, *args, **kwargs):
        result = methods["ancestry"](store, *args, **kwargs)
        counts["commits_enumerated"] += len(result)
        return result

    def parsed(validator, *args, **kwargs):
        counts["records_validated"] += 1
        return parse(validator, *args, **kwargs)

    def domain_checked(domain, records, metadata, **kwargs):
        counts["domain_records_checked"] += len(records)
        return domain_validate(domain, records, metadata, **kwargs)

    def paired(receipts, *args, **kwargs):
        counts["receipts_validated"] += 1
        return pair(receipts, *args, **kwargs)

    def transitioned(verifier, *args, **kwargs):
        counts["commits_traversed"] += 1
        return transition(verifier, *args, **kwargs)

    if app.history_index.connection is not None:
        app.history_index.connection.set_trace_callback(sql)
        connections.append(app.history_index.connection)
    started = time.perf_counter()
    status, detail, result = "complete", None, None
    with (
        patch.object(GitStore, "_run_bytes", run),
        patch.object(GitStore, "blobs", blobs),
        patch.object(GitStore, "read", read),
        patch.object(GitStore, "entries", entries),
        patch.object(GitStore, "changes", changes),
        patch.object(GitStore, "ancestry", ancestry),
        patch.object(ContractValidator, "parse", parsed),
        patch.object(DomainRules, "validate", domain_checked),
        patch.object(type(app.receipts), "validate_pair", paired),
        patch.object(TransitionVerifier, "transition", transitioned),
        patch.object(sqlite3, "connect", traced_connect),
    ):
        try:
            result = callback()
            if isinstance(result, dict) and result.get("status") == "repair_required":
                status, detail = "failed", result
        except Exception as exc:
            status, detail = "failed", repr(exc)
        finally:
            for connection in connections:
                with suppress(sqlite3.Error):
                    connection.set_trace_callback(None)
    return dict(
        operation=name,
        mode=mode,
        status=status,
        detail=detail,
        elapsed_seconds=round(time.perf_counter() - started, 6),
        **counts,
        database_bytes=app.history_index.database.stat().st_size
        if app.history_index.database.exists()
        else 0,
        process_lifetime_peak_working_set_bytes=memory_peak(),
    )


def optimized(args):
    contracts, rows = ContractValidator(), []
    runtime = ROOT / "packages/python/second_brain_core"
    fingerprint = hashlib.sha256(
        b"".join(path.name.encode() + path.read_bytes() for path in sorted(runtime.glob("*.py")))
    ).hexdigest()
    report = dict(
        runtime_sha256=fingerprint,
        contracts_sha256=hashlib.sha256(
            json.dumps(contracts.schemas, sort_keys=True).encode()
        ).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=platform.python_version(),
        platform=platform.platform(),
        git=subprocess.check_output(["git", "--version"], text=True).strip(),
        rows=rows,
    )

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for size in args.sizes:
        with tempfile.TemporaryDirectory(prefix="second-brain-benchmark-") as directory:
            app, cluster = core_fixture.__wrapped__(Path(directory), contracts)
            first = batch(app, cluster)
            first["operations"][0]["payload"]["content"]["body"] = "small\n" * 32
            first["operations"][1]["payload"]["content"]["body"] = "large\n" * 2048
            app.submit(first)
            for _ in range(2):
                app.submit(batch(app, cluster))
            extend(app, cluster, size - 4, varied=True)
            node = first["operations"][0]["request_id"]
            relation = first["operations"][2]["payload"]["relation"]["id"]

            def fresh():
                return Core(app.context, GitStore(app.store.repository, app.store.ref), contracts)

            def action(client, name):
                if name == "node_read":
                    return client.read(operation(client, "node.read", {"node_id": node}))
                if name == "relation_read":
                    return client.read(
                        operation(client, "relation.read", {"relation_id": relation})
                    )
                if name == "generation":
                    return client.generation()
                if name == "exact_replay":
                    return client.submit(first)
                if name == "bounded_create":
                    request = copy.deepcopy(first)
                    request.update(
                        transaction_id=uid(),
                        idempotency_key=uid(),
                        expected_generation=client.generation(),
                    )
                    request["operations"] = [
                        operation(client, "node.create", first["operations"][0]["payload"])
                    ]
                    return client.submit(request)
                if name == "full_history_audit":
                    return audit_history(client)
                return rebuild_history_index(client)

            def record(name, mode, callback):
                row = dict(
                    commits_at_corpus_start=size,
                    **optimized_measure(app, name, mode, callback, args.git_budget),
                )
                rows.append(row)
                save()
                print(json.dumps(row), flush=True)
                if row["status"] != "complete":
                    raise RuntimeError("Benchmark operation failed; partial evidence saved")

            record("index_rebuild", "cold_initial_full_build", lambda: rebuild_history_index(app))
            for name in (
                "node_read",
                "relation_read",
                "generation",
                "exact_replay",
                "bounded_create",
            ):
                record(name, "cold_new_core_healthy_index", lambda name=name: action(fresh(), name))
                # Refresh this client's authenticated frontier after a separate writer's create.
                app.generation()
                record(name, "warm", lambda name=name: action(app, name))
                app.history_index.database.unlink()
                recovered = fresh()

                # The recovery row explicitly includes full rebuild after loss of SQLite.
                def recovery(name=name, client=recovered):
                    rebuilt = rebuild_history_index(client)
                    if rebuilt.get("status") != "rebuilt":
                        return rebuilt
                    return action(client, name)

                record(name, "recovery_missing_index_includes_rebuild", recovery)
                app = recovered
            for name in ("full_history_audit", "index_rebuild"):
                record(name, "cold_new_core_healthy_index", lambda name=name: action(fresh(), name))
                app.history_index.database.unlink()
                record(name, "recovery_missing_index", lambda name=name: action(fresh(), name))
                if not app.history_index.database.exists():
                    rebuilt = rebuild_history_index(app)
                    if rebuilt.get("status") != "rebuilt":
                        raise RuntimeError(rebuilt)
    final_fingerprint = hashlib.sha256(
        b"".join(path.name.encode() + path.read_bytes() for path in sorted(runtime.glob("*.py")))
    ).hexdigest()
    report["runtime_unchanged_during_measurement"] = fingerprint == final_fingerprint
    save()


def mutation_request(app, node, content, revision, generation):
    """Existing canonical full replacement and explicit target CAS."""
    op = operation(app, "node.update", {"node_id": node, "content": copy.deepcopy(content)})
    op.update(
        idempotency_key=uid(),
        expectations=[
            {
                "resource": {
                    "instance_id": app.context.instance_id,
                    "resource_kind": "node",
                    "id": node,
                },
                "expected_revision": revision,
            }
        ],
    )
    return dict(
        kind="batch_request",
        schema_version="1.0.0",
        instance_id=app.context.instance_id,
        transaction_id=uid(),
        idempotency_key=uid(),
        expected_generation=generation,
        operations=[op],
    )


def extend_mutations(app, cluster, count, hot):
    """Disposable fixture plumbing, subsequently checked by real full rebuild."""
    parent = app.store.resolve()
    files = app.store.read(parent)
    generation, records, metadata = app.repository.parse_tree(files)
    stream = bytearray()
    for number in range(count):
        before = files.copy()
        request = None
        if number % 20 == 0:
            with patch.object(app, "generation", return_value=generation):
                request = batch(app, cluster)
        elif number % 20 == 10:
            head = records["node", hot]
            content = copy.deepcopy(head["content"])
            content["body"] = "revision fixture\n" * (16, 256, 768)[number // 20 % 3]
            content["title"] = f"hot revision {head['revision'] + 1}"
            request = mutation_request(app, hot, content, head["revision"], generation)
        if request:
            results = [app._create(op, records, files, metadata) for op in request["operations"]]
            generation = app.repository.generation(files)
            app.receipts.record(request, generation, results, files)
        else:
            generation = dict(generation, generation_id=uid())
        files[GENERATION] = encode(generation)
        stream.extend(
            f"commit {app.store.ref}\nmark :{number + 1}\ncommitter Benchmark <bench@localhost> {1700000000 + number} +0000\ndata 7\nfixture\nfrom {parent}\n".encode()
        )
        for path in sorted(path for path, raw in files.items() if before.get(path) != raw):
            raw = files[path]
            stream.extend(f"M 100644 inline {path}\ndata {len(raw)}\n".encode())
            stream.extend(raw + b"\n")
        stream.extend(b"\n")
        parent = f":{number + 1}"
    if stream:
        app.store.run("fast-import", "--quiet", data=bytes(stream))
    return records


def node_mutation(args):
    contracts, rows = ContractValidator(), []
    runtime = ROOT / "packages/python/second_brain_core"

    def fingerprint():
        return hashlib.sha256(
            b"".join(p.name.encode() + p.read_bytes() for p in sorted(runtime.glob("*.py")))
        ).hexdigest()

    report = dict(
        milestone="M2.2",
        runtime_sha256=fingerprint(),
        contracts_sha256=hashlib.sha256(
            json.dumps(contracts.schemas, sort_keys=True).encode()
        ).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=platform.python_version(),
        platform=platform.platform(),
        git=subprocess.check_output(["git", "--version"], text=True).strip(),
        rows=rows,
    )

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for size in args.sizes:
        if size < 20:
            raise ValueError("Mutation corpus needs at least twenty committed generations")
        with tempfile.TemporaryDirectory(prefix="second-brain-m22-benchmark-") as directory:
            app, cluster = core_fixture.__wrapped__(Path(directory), contracts)
            principal = app.context.principal
            app = Core(
                replace(
                    app.context,
                    principal=replace(
                        principal,
                        grants=principal.grants
                        | frozenset(
                            (cluster, action) for action in ("node.update", "node.history.read")
                        ),
                    ),
                ),
                app.store,
                contracts,
            )
            first = batch(app, cluster)
            first_receipt = app.submit(first)
            unaffected = batch(app, cluster)
            unaffected_receipt = app.submit(unaffected)
            app.submit(batch(app, cluster))
            hot, cold = [op["request_id"] for op in first["operations"][:2]]
            relation = first["operations"][2]["payload"]["relation"]["id"]
            records = extend_mutations(app, cluster, size - 4, hot)
            initial_revision = records["node", hot]["revision"]

            corpus_receipts = sum(
                path.startswith("control/receipts/") for path in app.store.read(app.store.resolve())
            )

            committed_generations = size
            hot_revision_count = initial_revision

            def record(
                name,
                callback,
                validate=lambda result: None,
                mode="warm",
                generation_delta=0,
                hot_revision_delta=0,
                **metadata,
            ):
                nonlocal committed_generations, hot_revision_count
                captured = []

                def observed():
                    result = callback()
                    captured.append(result)
                    return result

                row = dict(
                    commits_at_corpus_start=size,
                    hot_revisions_at_corpus_start=initial_revision,
                    receipts_at_corpus_start=corpus_receipts,
                    committed_generations_at_operation_start=committed_generations,
                    hot_revision_count_at_operation_start=hot_revision_count,
                    revision_count=metadata.pop("revision_count", hot_revision_count),
                    committed_generations_added=generation_delta,
                    **metadata,
                    **optimized_measure(app, name, mode, observed, args.git_budget),
                )
                if row["status"] == "complete":
                    try:
                        validate(captured[0])
                    except Exception as exc:
                        row.update(status="failed", detail=repr(exc))
                rows.append(row)
                save()
                print(json.dumps(row), flush=True)
                if row["status"] != "complete":
                    raise RuntimeError("Benchmark failed; partial observations saved")
                committed_generations += generation_delta
                hot_revision_count += hot_revision_delta

            def assert_rebuilt(result):
                assert result["status"] == "rebuilt", result
                assert len(app.store.ancestry(app.store.resolve())) == size

            record(
                "initial_full_rebuild",
                lambda: rebuild_history_index(app),
                assert_rebuilt,
                mode="explicit_full_rebuild",
            )

            def read(identifier):
                model = app.read(operation(app, "node.read", {"node_id": identifier}))
                return app.boundary.dump("transaction", model)["records"][0]

            updates = {}
            for identifier, name in ((cold, "node_update"), (hot, "node_update_many_revisions")):
                before = read(identifier)
                content = copy.deepcopy(before["content"])
                content["title"] += " updated"
                request = mutation_request(
                    app, identifier, content, before["revision"], app.generation()
                )

                def validate_update(receipt):
                    after = read(identifier)
                    assert after["id"] == identifier and after["revision"] == before["revision"] + 1
                    wire = app.boundary.dump("transaction", receipt)
                    assert (
                        after["content"] == content
                        and after["revision_ref"] == wire["results"][0]["revisions"][0]
                    )
                    updates[identifier] = (request, receipt)

                record(
                    name,
                    lambda: app.submit(request),
                    validate_update,
                    target_revision_before=before["revision"],
                    revision_count=before["revision"],
                    generation_delta=1,
                    hot_revision_delta=int(identifier == hot),
                )
            for logical, name in (
                (1, "node_revision_read_first"),
                (initial_revision, "node_revision_read_previous"),
            ):
                refs = [
                    r
                    for (kind, _), r in records.items()
                    if kind == "node_revision"
                    and r["node_id"] == hot
                    and r["logical_revision"] == logical
                ]
                assert len(refs) == 1
                revision = refs[0]
                reference = dict(
                    resource=dict(
                        instance_id=app.context.instance_id, resource_kind="node", id=hot
                    ),
                    revision_id=revision["id"],
                    revision=logical,
                )
                request = operation(app, "node.revision.read", {"revision": reference})

                def validate_history(result):
                    delivered = app.boundary.dump("transaction", result)["records"][0]
                    assert (
                        delivered["id"] == revision["id"]
                        and delivered["snapshot"] == revision["snapshot"]
                    )

                record(
                    name, lambda: app.read(request), validate_history, requested_revision=logical
                )

            def record_replay(name, request, expected):
                commit = app.store.resolve()

                def validate(result):
                    assert result == expected and app.store.resolve() == commit

                record(name, lambda: app.submit(request), validate)

            record_replay("node_update_replay", *updates[hot])
            record_replay("creation_replay_after_updates", first, first_receipt)
            request = copy.deepcopy(updates[hot][0])
            request.update(
                transaction_id=uid(), idempotency_key=uid(), expected_generation=app.generation()
            )
            request["operations"][0].update(request_id=uid(), idempotency_key=uid())
            commit = app.store.resolve()

            def conflict():
                try:
                    app.submit(request)
                except CoreError as exc:
                    return exc.code
                raise AssertionError("Stale CAS unexpectedly succeeded")

            def validate_conflict(code):
                assert code == "REVISION_CONFLICT", code
                assert app.store.resolve() == commit

            record("node_update_cas_conflict", conflict, validate_conflict)
            before = read(hot)
            content = dict(before["content"], title="published before index failure")
            request = mutation_request(app, hot, content, before["revision"], app.generation())
            old = app.store.resolve()

            def recover():
                nonlocal app
                with patch.object(
                    app.history_index,
                    "publish",
                    side_effect=OSError("injected derived publication interruption"),
                ):
                    try:
                        app.submit(request)
                    except CoreError as exc:
                        assert exc.code == "REPAIR_REQUIRED", exc.code
                    else:
                        raise AssertionError("Injected projection interruption was ignored")
                published = app.store.resolve()
                assert published != old
                app = Core(app.context, GitStore(app.store.repository, app.store.ref), contracts)
                receipt = app.submit(request)
                assert app.store.resolve() == published
                return receipt

            def validate_recovery(receipt):
                assert read(hot)["revision"] == before["revision"] + 1
                commit = app.store.resolve()
                assert app.submit(request) == receipt and app.store.resolve() == commit

            record(
                "published_git_index_failure_recovery",
                recover,
                validate_recovery,
                generation_delta=1,
                hot_revision_delta=1,
            )

            def validate_node(result):
                delivered = app.boundary.dump("transaction", result)["records"][0]
                assert delivered["id"] == hot and delivered["revision"] == initial_revision + 2

            record(
                "node_read",
                lambda: app.read(operation(app, "node.read", {"node_id": hot})),
                validate_node,
            )

            def validate_relation(result):
                delivered = app.boundary.dump("transaction", result)["records"][0]
                assert delivered["id"] == relation and delivered["revision"] == 1

            record(
                "relation_read",
                lambda: app.read(operation(app, "relation.read", {"relation_id": relation})),
                validate_relation,
            )
            expected_generation = app.generation()

            def validate_generation(result):
                assert result == expected_generation

            record("generation", app.generation, validate_generation)
            request = batch(app, cluster)
            request["operations"] = request["operations"][:1]

            def validate_create(receipt):
                assert len(receipt.results) == 1
                assert read(request["operations"][0]["request_id"])["revision"] == 1

            record(
                "bounded_create",
                lambda: app.submit(request),
                validate_create,
                generation_delta=1,
                revision_count=0,
            )
            record_replay("exact_replay", unaffected, unaffected_receipt)
    report["runtime_unchanged_during_measurement"] = report["runtime_sha256"] == fingerprint()
    report["harness_unchanged_during_measurement"] = (
        report["harness_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    report["contracts_unchanged_during_measurement"] = (
        report["contracts_sha256"]
        == hashlib.sha256(
            json.dumps(ContractValidator().schemas, sort_keys=True).encode()
        ).hexdigest()
    )
    save()


def hardening_measure(app, name, callback, limit, mode="warm"):
    """Observe real SQLite serialization, full database hashes and derived writes.

    File bytes are Python write payloads, not hardware-sector writes or fsync
    durability. CPU is this Python process only, excluding child Git CPU.
    """
    writes, descriptors, hashes, components = [], {}, [], {}
    original_open, original_fdopen, sha256 = os.open, os.fdopen, hashlib.sha256
    directory = app.history_index.directory.resolve()

    def opened(path, flags, *args, **kwargs):
        descriptor = original_open(path, flags, *args, **kwargs)
        if isinstance(path, (str, os.PathLike)):
            candidate = Path(path).resolve()
            if candidate.is_relative_to(directory):
                descriptors[descriptor] = candidate.name
        return descriptor

    class Writer:
        def __init__(self, handle, name):
            self.handle, self.name = handle, name

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def write(self, raw):
            result = self.handle.write(raw)
            writes.append(dict(file=self.name, bytes=result))
            return result

    def fdopened(descriptor, *args, **kwargs):
        handle = original_fdopen(descriptor, *args, **kwargs)
        name = descriptors.pop(descriptor, None)
        return Writer(handle, name) if name else handle

    def hashed(raw=b"", *args, **kwargs):
        if (
            isinstance(raw, (bytes, bytearray, memoryview))
            and bytes(raw[:16]) == b"SQLite format 3\x00"
        ):
            hashes.append(len(raw))
        return sha256(raw, *args, **kwargs)

    def timed(owner, method, label):
        original = getattr(owner, method)

        def observed(*args, **kwargs):
            wall, cpu = time.perf_counter(), time.process_time()
            try:
                return original(*args, **kwargs)
            finally:
                metric = components.setdefault(
                    label, dict(calls=0, wall_seconds=0.0, python_cpu_seconds=0.0)
                )
                metric["calls"] += 1
                metric["wall_seconds"] += time.perf_counter() - wall
                metric["python_cpu_seconds"] += time.process_time() - cpu

        return patch.object(owner, method, observed)

    profile = cProfile.Profile()
    original_connection = app.history_index.connection
    changes_before = original_connection.total_changes if original_connection is not None else None
    cpu = time.process_time()
    with (
        patch.object(os, "open", opened),
        patch.object(os, "fdopen", fdopened),
        patch.object(hashlib, "sha256", hashed),
        ExitStack() as stack,
    ):
        from second_brain_core.history_index import HistoryIndex

        for owner, method, label in (
            (GitStore, "prepare_delta", "git_prepare_delta"),
            (Core, "_next_generation", "generation_path_digest"),
            (Core, "_mutation_context", "authorization_dependencies"),
            (TransitionVerifier, "verify", "incremental_verification"),
            (HistoryIndex, "publish", "derived_publication"),
            (HistoryIndex, "coherent", "frontier_coherence"),
        ):
            stack.enter_context(timed(owner, method, label))
        profile.enable()
        try:
            row = optimized_measure(app, name, mode, callback, limit)
        finally:
            profile.disable()
    serializations = sum(
        count
        for (_, _, function), (_, count, _, _, _) in pstats.Stats(profile).stats.items()
        if "serialize" in function
        and "deserialize" not in function
        and "sqlite3.Connection" in function
    )
    copies = sum(
        count
        for (_, _, function), (_, count, _, _, _) in pstats.Stats(profile).stats.items()
        if "backup" in function and "sqlite3.Connection" in function
    )
    deserializations = sum(
        count
        for (_, _, function), (_, count, _, _, _) in pstats.Stats(profile).stats.items()
        if "deserialize" in function and "sqlite3.Connection" in function
    )
    commitment_calls = {}
    for (filename, _, function), (_, count, _, _, _) in pstats.Stats(profile).stats.items():
        if Path(filename).name == "commitment.py":
            commitment_calls[function] = commitment_calls.get(function, 0) + count
    row.update(
        python_cpu_seconds=round(time.process_time() - cpu, 6),
        components=components,
        full_sqlite_serializations=serializations,
        full_sqlite_backups=copies,
        full_sqlite_deserializations=deserializations,
        projection_rows_changed=(original_connection.total_changes - changes_before)
        if original_connection is not None
        and original_connection is app.history_index.connection
        and changes_before is not None
        else None,
        projection_row_count_scope="same private connection; changed connection/rebuild reports null",
        full_sqlite_hash_calls=len(hashes),
        full_sqlite_hash_bytes=sum(hashes),
        derived_bytes_written=sum(write["bytes"] for write in writes),
        sqlite_snapshot_bytes_written=sum(
            write["bytes"] for write in writes if ".sqlite3" in write["file"]
        ),
        authenticated_delta_bytes_written=sum(
            write["bytes"] for write in writes if write["file"].startswith("delta-")
        ),
        checkpoint_bytes_written=sum(
            write["bytes"] for write in writes if write["file"].startswith("checkpoint.json")
        ),
        derived_writes=writes,
        derived_directory_bytes=sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()),
        commitment_function_calls=commitment_calls,
    )
    return row


def merkle_measure(app, name, callback, limit, mode="warm"):
    """Count actual hash input and metadata work around the existing measurement.

    These counters include canonical records and checkpoint authentication, not
    only Merkle construction. Git byte counts are subprocess payloads; they are
    neither physical writes nor a count of newly allocated unique Git objects.
    """
    from second_brain_core.commitment import PREFIX, ContentCommitment
    from second_brain_core.history_index import HistoryIndex

    counters = dict(
        sha256_calls=0,
        sha256_bytes=0,
        sqlite_rows_returned=0,
        file_metadata_rows_returned=0,
        full_file_metadata_scans=0,
    )
    commands = {}
    original_hash, original_run = hashlib.sha256, GitStore._run_bytes
    original_query = HistoryIndex.query
    original_commitment_hash = ContentCommitment._hash
    commitments = {}
    file_metadata_queries = {}

    def commitment_hash(tag, parts):
        metric = commitments.setdefault(tag.decode(), dict(calls=0, bytes=0))
        metric["calls"] += 1
        metric["bytes"] += len(PREFIX) + 2 + len(tag) + 4 + sum(8 + len(part) for part in parts)
        if tag == b"bucket":
            cardinality = int.from_bytes(parts[2], "big")
            metric["bucket_entries_processed"] = (
                metric.get("bucket_entries_processed", 0) + cardinality
            )
            metric["maximum_bucket_cardinality"] = max(
                metric.get("maximum_bucket_cardinality", 0), cardinality
            )
        return original_commitment_hash(tag, parts)

    class ObservedHash:
        def __init__(self, raw=b"", **kwargs):
            counters["sha256_calls"] += 1
            counters["sha256_bytes"] += len(raw)
            self.value = original_hash(raw, **kwargs)

        def __getattr__(self, attribute):
            return getattr(self.value, attribute)

        def update(self, raw):
            counters["sha256_bytes"] += len(raw)
            return self.value.update(raw)

        def copy(self):
            result = object.__new__(ObservedHash)
            result.value = self.value.copy()
            return result

    def run(store, *args, **kwargs):
        result = original_run(store, *args, **kwargs)
        command = str(args[0])
        metric = commands.setdefault(command, dict(calls=0, input_bytes=0, output_bytes=0))
        metric["calls"] += 1
        metric["input_bytes"] += len(kwargs.get("data") or b"")
        metric["output_bytes"] += len(result)
        if command == "ls-tree":
            metric["entries_returned"] = metric.get("entries_returned", 0) + (
                len(result.rstrip(b"\0\n").split(b"\0" if b"\0" in result else b"\n"))
                if result
                else 0
            )
        if command in ("hash-object", "mktree", "write-tree", "commit-tree"):
            metric["object_oid_results"] = metric.get("object_oid_results", 0) + len(
                result.splitlines()
            )
        return result

    def query(index, *args, **kwargs):
        result = original_query(index, *args, **kwargs)
        counters["sqlite_rows_returned"] += len(result)
        sql = " ".join(str(args[0]).lower().split())
        if "from files" in sql:
            counters["file_metadata_rows_returned"] += len(result)
            metric = file_metadata_queries.setdefault(sql, dict(calls=0, rows_returned=0))
            metric["calls"] += 1
            metric["rows_returned"] += len(result)
            if " where " not in sql:
                counters["full_file_metadata_scans"] += 1
        return result

    with (
        patch.object(hashlib, "sha256", ObservedHash),
        patch.object(GitStore, "_run_bytes", run),
        patch.object(HistoryIndex, "query", query),
        patch.object(ContentCommitment, "_hash", staticmethod(commitment_hash)),
    ):
        row = hardening_measure(app, name, callback, limit, mode)
    row.update(
        counters,
        git_command_work=commands,
        commitment_hash_work=commitments,
        file_metadata_queries=file_metadata_queries,
    )
    return row


def mutation_hardening(args):
    """M2.2.1 fixed corpus and repeated API workloads; no wall-clock gates."""
    from second_brain_core import maintenance

    contracts, rows = ContractValidator(), []
    runtime = ROOT / "packages/python/second_brain_core"

    def fingerprint():
        return hashlib.sha256(
            b"".join(p.name.encode() + p.read_bytes() for p in sorted(runtime.glob("*.py")))
        ).hexdigest()

    report = dict(
        milestone="M2.2.2" if args.merkle_hardening else "M2.2.1",
        comparison_baseline_artifact="docs/engineering/history-performance-m221-baseline.json",
        comparison_baseline_sha256=hashlib.sha256(
            (ROOT / "docs/engineering/history-performance-m221-baseline.json").read_bytes()
        ).hexdigest(),
        runtime_sha256=fingerprint(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        contracts_sha256=hashlib.sha256(
            json.dumps(contracts.schemas, sort_keys=True).encode()
        ).hexdigest(),
        python=platform.python_version(),
        platform=platform.platform(),
        git=subprocess.check_output(["git", "--version"], text=True).strip(),
        measurement_notes=[
            "Instrumented elapsed times; Python CPU excludes Git subprocess CPU.",
            "Derived write bytes count Python fdopen write payloads, not physical sector writes.",
            "Peak memory is process-lifetime working set including corpus construction and rebuild.",
            "p99 requires at least 1000 samples; n=100 supports p50/p95 only.",
            "Request construction, generation lookup and postcondition reads are outside submit measurement.",
        ],
        rows=rows,
        summaries=[],
    )
    if args.merkle_hardening:
        helper_paths = [ROOT / "tests/conftest.py", ROOT / "tests/test_core_m1.py"]
        report.update(
            comparison_baseline_artifact="docs/engineering/history-performance-m222-baseline.json",
            comparison_baseline_sha256=hashlib.sha256(
                (ROOT / "docs/engineering/history-performance-m222-baseline.json").read_bytes()
            ).hexdigest(),
            previous_milestone_artifact="docs/engineering/history-performance-m221.json",
            previous_milestone_sha256=hashlib.sha256(
                (ROOT / "docs/engineering/history-performance-m221.json").read_bytes()
            ).hexdigest(),
            sizes=args.sizes,
            hardening_samples=args.hardening_samples,
            fixture_helper_sha256={
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in helper_paths
            },
        )
        report["measurement_notes"].extend(
            [
                "Git object OID results count commands' outputs, not newly allocated unique objects.",
                "Git metadata paths/tree entries count observed plumbing outputs, not internal read-tree/write-tree path visits.",
                "sqlite_rows_returned covers HistoryIndex.query materialized results; direct connection SELECTs are excluded.",
                "Commitment bucket_entries_processed counts exact complete touched buckets, including preview and verifier separately.",
                "SHA256 bytes include all instrumented hashlib.sha256 calls and update chunks, including checkpoint and record hashes.",
                "SHA256 counters exclude child Git hashing and C-internal HMAC hashing; only instrumented Python constructor/update input is counted.",
                "Explicit host capacity maintenance is outside mutation service time and reported separately.",
            ]
        )

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for size in args.sizes:
        if size < 20:
            raise ValueError("Mutation corpus needs at least twenty generations")
        with tempfile.TemporaryDirectory(prefix="second-brain-m221-benchmark-") as directory:
            with ExitStack() as fixture_stack:
                if args.merkle_hardening:
                    fixture_stack.enter_context(patch("second_brain_core.bootstrap.SCHEME", None))
                app, cluster = core_fixture.__wrapped__(Path(directory), contracts)
            principal = app.context.principal
            app = Core(
                replace(
                    app.context,
                    principal=replace(
                        principal,
                        grants=principal.grants
                        | frozenset(
                            (cluster, action) for action in ("node.update", "node.history.read")
                        ),
                    ),
                ),
                app.store,
                contracts,
            )
            first = batch(app, cluster)
            creation_receipt = app.submit(first)
            hot = first["operations"][0]["request_id"]
            records = extend_mutations(app, cluster, size - 2, hot)
            hot_initial = records["node", hot]["revision"]
            receipt_count = sum(
                path.startswith("control/receipts/") for path in app.store.read(app.store.resolve())
            )

            def record(name, callback, mode="warm", **metadata):
                if args.merkle_hardening and name in (
                    "hot_node_update",
                    "distributed_node_update",
                    "large_body_update",
                    "mixed_create_update_batch",
                ):
                    accepted = app.history_index.accepted
                    if (
                        accepted["sequence"] - accepted["base_sequence"]
                        >= maintenance.MAINTENANCE_DELTAS
                        or accepted["tail_bytes"] >= maintenance.MAINTENANCE_BYTES
                    ):
                        record(
                            "restart_at_maintenance_threshold",
                            lambda: Core(
                                app.context,
                                GitStore(app.store.repository, app.store.ref),
                                contracts,
                            ).generation(),
                            mode="cold_restart",
                        )
                        record(
                            "host_preemptive_maintenance",
                            lambda: maintenance.maintain_history_index(app),
                            mode="trusted_maintenance",
                        )
                captured_results = []

                def observed():
                    result = callback()
                    if mode in ("trusted_maintenance", "trusted_upgrade", "explicit_compaction"):
                        captured_results.append(result)
                    return result

                row = dict(
                    commits_at_corpus_start=size,
                    hot_revisions_at_corpus_start=hot_initial,
                    receipts_at_corpus_start=receipt_count,
                    corpus_mix="bootstrap plus first creation batch; every twentieth bulk commit creates two Nodes and Relation, offset ten updates hot Node; other commits generation-only",
                    **metadata,
                    **(merkle_measure if args.merkle_hardening else hardening_measure)(
                        app, name, observed, args.git_budget, mode
                    ),
                )
                if captured_results:
                    row["maintenance_result"] = captured_results[0]
                rows.append(row)
                save()
                print(json.dumps(row), flush=True)
                if row["status"] != "complete":
                    raise RuntimeError("Benchmark failed; partial evidence saved")
                return row

            record(
                "initial_full_rebuild",
                lambda: rebuild_history_index(app),
                mode="explicit_full_rebuild",
            )
            if args.merkle_hardening:
                record(
                    "explicit_commitment_adoption",
                    lambda: maintenance.adopt_generation_commitment(app),
                    mode="trusted_upgrade",
                )

            def head(identifier):
                return app.boundary.dump(
                    "transaction", app.read(operation(app, "node.read", {"node_id": identifier}))
                )["records"][0]

            def compact():
                return maintenance.compact_history_index(app)

            profile_head = head(hot)
            profile_request = mutation_request(
                app,
                hot,
                dict(profile_head["content"], title="profile measured replacement"),
                profile_head["revision"],
                app.generation(),
            )
            record(
                "baseline_matched_update",
                lambda: app.submit(profile_request),
                target_revision_before=profile_head["revision"],
            )
            record("node_read", lambda: app.read(operation(app, "node.read", {"node_id": hot})))
            relation = first["operations"][2]["payload"]["relation"]["id"]
            record(
                "relation_read",
                lambda: app.read(operation(app, "relation.read", {"relation_id": relation})),
            )
            record("generation", app.generation)
            if args.merkle_hardening:
                stale = head(hot)
                request = mutation_request(
                    app,
                    hot,
                    dict(stale["content"], title="stale CAS probe"),
                    stale["revision"] - 1,
                    app.generation(),
                )
                accepted_commit = app.store.resolve()

                def cas_conflict():
                    try:
                        app.submit(request)
                    except CoreError as exc:
                        assert exc.code == "REVISION_CONFLICT", exc.code
                        assert app.store.resolve() == accepted_commit
                        return exc.code
                    raise AssertionError("Stale CAS was accepted")

                record("stale_cas_conflict", cas_conflict)
                large = head(hot)
                request = mutation_request(
                    app,
                    hot,
                    dict(large["content"], body="large body evidence\n" * 32768),
                    large["revision"],
                    app.generation(),
                )
                record(
                    "large_body_update",
                    lambda: app.submit(request),
                    replacement_body_bytes=len(
                        request["operations"][0]["payload"]["content"]["body"].encode()
                    ),
                )
                before = head(hot)
                request = mutation_request(
                    app,
                    hot,
                    dict(before["content"], body="bounded high churn body\n" * 16),
                    before["revision"],
                    app.generation(),
                )
                record("large_body_to_small_update", lambda: app.submit(request))
            create_request = batch(app, cluster)
            create_request["operations"] = create_request["operations"][:1]
            record("bounded_create", lambda: app.submit(create_request))
            record("exact_create_replay", lambda: app.submit(create_request))
            last_request = last_receipt = None
            samples = (
                args.hardening_samples
                if args.hardening_samples is not None
                else (1000 if size >= 10000 else 100)
            )
            targets = [identifier for (kind, identifier) in records if kind == "node"]
            for workload, identifiers in (
                ("hot_node_update", [hot] * samples),
                ("distributed_node_update", targets[:10]),
            ):
                measured = []
                loop_started = time.perf_counter()
                for position, identifier in enumerate(identifiers):
                    before = head(identifier)
                    content = dict(before["content"], title=f"{workload} {position}")
                    request = mutation_request(
                        app, identifier, content, before["revision"], app.generation()
                    )
                    captured = []

                    def submit():
                        receipt = app.submit(request)
                        captured.append(receipt)
                        return receipt

                    row = record(
                        workload, submit, sample=position, target_revision_before=before["revision"]
                    )
                    assert head(identifier)["revision"] == before["revision"] + 1
                    measured.append(row)
                    last_request, last_receipt = request, captured[0]
                times = sorted(row["elapsed_seconds"] for row in measured)
                import math

                def percentile(fraction):
                    return times[math.ceil(len(times) * fraction) - 1]

                report["summaries"].append(
                    dict(
                        commits_at_corpus_start=size,
                        operation=workload,
                        samples=len(times),
                        successful_updates_per_second=len(times) / sum(times),
                        observed_loop_wall_seconds=time.perf_counter() - loop_started,
                        observed_loop_updates_per_second=len(times)
                        / (time.perf_counter() - loop_started),
                        loop_scope="includes dependency reads, request construction, host maintenance, instrumentation and JSON report/log IO",
                        minimum_seconds=min(times),
                        maximum_seconds=max(times),
                        p50_seconds=percentile(0.5) if len(times) >= 100 else None,
                        p95_seconds=percentile(0.95) if len(times) >= 100 else None,
                        p99_seconds=percentile(0.99) if len(times) >= 1000 else None,
                        p99_limitation=None if len(times) >= 1000 else "insufficient tail coverage",
                    )
                )
                save()
            commit = app.store.resolve()
            record("exact_update_replay", lambda: app.submit(last_request))
            assert app.submit(last_request) == last_receipt and app.store.resolve() == commit
            record("creation_replay_after_updates", lambda: app.submit(first))
            assert app.submit(first) == creation_receipt
            original = next(
                r
                for (kind, _), r in records.items()
                if kind == "node_revision" and r["node_id"] == hot and r["logical_revision"] == 1
            )
            reference = dict(
                resource=dict(instance_id=app.context.instance_id, resource_kind="node", id=hot),
                revision_id=original["id"],
                revision=1,
            )
            history_request = operation(app, "node.revision.read", {"revision": reference})
            record("historical_revision_one", lambda: app.read(history_request))
            before = head(hot)
            request = mutation_request(
                app,
                hot,
                dict(before["content"], title="mixed batch replacement"),
                before["revision"],
                app.generation(),
            )
            create = batch(app, cluster)["operations"][0]
            request["operations"].append(create)
            record("mixed_create_update_batch", lambda: app.submit(request))
            if size >= 10000 and args.hardening_samples is None and not args.merkle_hardening:
                from second_brain_core.history_index import MAX_DELTAS

                while (
                    app.history_index.accepted["sequence"]
                    - app.history_index.accepted["base_sequence"]
                ) < MAX_DELTAS:
                    before = head(hot)
                    request = mutation_request(
                        app,
                        hot,
                        dict(before["content"], title=f"tail capacity {before['revision']}"),
                        before["revision"],
                        app.generation(),
                    )
                    record("tail_capacity_fill_update", lambda: app.submit(request))
                report["maximum_tail_observation"] = dict(
                    transitions=MAX_DELTAS,
                    authenticated_tail_bytes=app.history_index.accepted["tail_bytes"],
                )
                before = head(hot)
                request = mutation_request(
                    app,
                    hot,
                    dict(before["content"], title="capacity rejection"),
                    before["revision"],
                    app.generation(),
                )
                accepted_commit = app.store.resolve()

                def capacity_rejection():
                    try:
                        app.submit(request)
                    except CoreError as exc:
                        assert exc.code == "REPAIR_REQUIRED", exc.code
                        assert app.store.resolve() == accepted_commit
                        return exc.code
                    raise AssertionError("Full projection tail accepted another mutation")

                record("tail_capacity_rejection", capacity_rejection)

            def restart():
                nonlocal app
                app = Core(app.context, GitStore(app.store.repository, app.store.ref), contracts)
                return app.generation()

            record("cold_restart", restart, mode="cold_restart")
            record("explicit_compaction", compact, mode="explicit_compaction")
            record("restart_after_compaction", restart, mode="cold_restart")
            if args.merkle_hardening:
                record(
                    "derived_gc_dry_run",
                    lambda: maintenance.collect_history_index(app),
                    mode="trusted_maintenance",
                )
                record(
                    "derived_gc_apply",
                    lambda: maintenance.collect_history_index(app, apply=True),
                    mode="trusted_maintenance",
                )
                record("restart_after_gc", restart, mode="cold_restart")
            reader = Core(app.context, GitStore(app.store.repository, app.store.ref), contracts)
            reader.generation()
            before = head(hot)
            accepted_request = mutation_request(
                app,
                hot,
                dict(before["content"], title="accepted frontier catch-up"),
                before["revision"],
                app.generation(),
            )
            app.submit(accepted_request)
            writer, app = app, reader
            record("accepted_frontier_catch_up", app.generation, mode="accepted_frontier_catch_up")
            assert app.generation() == writer.generation()
            reader = writer
            before = head(hot)
            request = mutation_request(
                app,
                hot,
                dict(before["content"], title="catch-up mutation"),
                before["revision"],
                app.generation(),
            )
            with patch.object(
                app.history_index,
                "publish",
                side_effect=OSError("benchmark derived publication interruption"),
            ):
                try:
                    app.submit(request)
                except CoreError as exc:
                    assert exc.code == "REPAIR_REQUIRED", exc.code
                else:
                    raise AssertionError("Injected derived publication interruption was ignored")
            old_app, app = app, reader
            record("incremental_catch_up", app.generation, mode="recovery_catch_up")
            assert app.generation() == old_app.generation()
            record(
                "final_full_rebuild",
                lambda: rebuild_history_index(app),
                mode="explicit_full_rebuild",
            )
            if args.merkle_hardening:
                record(
                    "full_historical_audit", lambda: audit_history(app), mode="explicit_full_audit"
                )
    report["runtime_unchanged_during_measurement"] = report["runtime_sha256"] == fingerprint()
    report["harness_unchanged_during_measurement"] = (
        report["harness_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    report["contracts_unchanged_during_measurement"] = (
        report["contracts_sha256"]
        == hashlib.sha256(json.dumps(contracts.schemas, sort_keys=True).encode()).hexdigest()
    )
    if args.merkle_hardening:
        report["fixture_helpers_unchanged_during_measurement"] = report[
            "fixture_helper_sha256"
        ] == {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in helper_paths
        }
        report["validation_summary"] = dict(
            completed_rows=sum(row["status"] == "complete" for row in rows),
            failed_rows=sum(row["status"] != "complete" for row in rows),
            completed_corpus_sizes=args.sizes,
            source_fingerprints_unchanged=all(
                report[key]
                for key in (
                    "runtime_unchanged_during_measurement",
                    "harness_unchanged_during_measurement",
                    "contracts_unchanged_during_measurement",
                    "fixture_helpers_unchanged_during_measurement",
                )
            ),
        )
        grouped = {}
        for row in rows:
            key = (row["commits_at_corpus_start"], row["operation"])
            grouped.setdefault(key, []).append(row)
        report["observed_work_ranges"] = []
        for (size, operation_name), observations in grouped.items():
            metrics = {}
            for metric in (
                "elapsed_seconds",
                "git_processes",
                "blob_reads",
                "duplicate_blob_requests",
                "commits_traversed",
                "receipts_validated",
                "sqlite_statements",
                "projection_rows_changed",
                "sha256_calls",
                "sha256_bytes",
                "file_metadata_rows_returned",
                "derived_bytes_written",
                "full_sqlite_serializations",
                "full_sqlite_hash_calls",
            ):
                values = [row[metric] for row in observations if row.get(metric) is not None]
                metrics[metric] = dict(minimum=min(values), maximum=max(values)) if values else None
            report["observed_work_ranges"].append(
                dict(
                    corpus_size=size,
                    operation=operation_name,
                    samples=len(observations),
                    metrics=metrics,
                )
            )
    save()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000])
    parser.add_argument("--git-budget", type=int, default=2500)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--optimized", action="store_true")
    parser.add_argument("--node-mutation", action="store_true")
    parser.add_argument("--mutation-hardening", action="store_true")
    parser.add_argument("--merkle-hardening", action="store_true")
    parser.add_argument("--hardening-samples", type=int, default=None)
    args = parser.parse_args()
    if args.mutation_hardening or args.merkle_hardening:
        mutation_hardening(args)
        return
    if args.node_mutation:
        node_mutation(args)
        return
    if args.optimized:
        optimized(args)
        return
    rows = []
    contracts = ContractValidator()
    for size in args.sizes:
        with tempfile.TemporaryDirectory(prefix="second-brain-benchmark-") as directory:
            app, cluster = core_fixture.__wrapped__(Path(directory), contracts)
            first = batch(app, cluster)
            first["operations"][0]["payload"]["content"]["body"] = "small\n" * 32
            first["operations"][1]["payload"]["content"]["body"] = "large\n" * 2048
            app.submit(first)
            # Several genuine supported transactions accumulate distinct immutable evidence.
            for _ in range(2):
                app.submit(batch(app, cluster))
            fixture_generation = extend(app, cluster, size - 4)
            node = first["operations"][0]["request_id"]
            relation = first["operations"][2]["payload"]["relation"]["id"]

            # Correct request generation without another uninstrumented baseline scan.
            create = copy.deepcopy(first)

            create.update(transaction_id=uid(), idempotency_key=uid())
            create["operations"] = [
                operation(app, "node.create", first["operations"][0]["payload"])
            ]
            create["expected_generation"] = fixture_generation
            actions = {
                "node_read": partial(app.read, operation(app, "node.read", {"node_id": node})),
                "relation_read": partial(
                    app.read, operation(app, "relation.read", {"relation_id": relation})
                ),
                "generation": app.generation,
                "exact_replay": partial(app.submit, first),
                "bounded_create": partial(app.submit, create),
                "full_history_audit": app.repository.snapshot,
                "migration_inspect": partial(inspect_history, app),
            }
            for name, callback in actions.items():
                result = dict(commits=size, **measure(app, name, callback, args.git_budget))
                rows.append(result)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
