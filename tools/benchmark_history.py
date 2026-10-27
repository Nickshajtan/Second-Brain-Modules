"""Disposable history benchmark; counters are observations, never time guarantees."""

from __future__ import annotations

# Callbacks below execute synchronously before their enclosing loop advances.
# ruff: noqa: B023
import argparse
import copy
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000])
    parser.add_argument("--git-budget", type=int, default=2500)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--optimized", action="store_true")
    parser.add_argument("--node-mutation", action="store_true")
    args = parser.parse_args()
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
