"""Explicit trusted-host immutable-history backfill; never called by normal reads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from generated.v1.transaction_schema import HistoryBaseline
from jsonschema.exceptions import SchemaError, ValidationError

from .boundary import GENERATION, VERSION, CoreError, digest
from .codec import decode, encode
from .git_store import PublicationConflict, StorageError
from .history import HISTORY, HistoricalEvidenceError

if TYPE_CHECKING:
    from .application import Core


def _require_host(core):
    if not core.context.principal.bootstrap:
        core.boundary.fail("FORBIDDEN")


def _plan(core, commit=None):
    commit = commit or core.store.resolve()
    if commit is None:
        core.boundary.fail("REPAIR_REQUIRED")
    anchor = core.history_index.anchor()
    if anchor is not None:
        # Explicit inspection of the historical pre-migration source is allowed;
        # the current managed publication still has to retain the accepted anchor.
        current = core.store.resolve()
        core.store.changes(anchor["commit"], current)
    files = core.store.read(commit)
    trees = core.receipts.history.trees(commit)
    # Classify absent/invalid original admission before aggregate validation
    # collapses missing membership into a generic corrupt-state error.
    for path in files:
        if path.startswith("control/receipts/"):
            core.receipts.history.origin(path, files, trees)
    generation, records, _ = core.repository.parse_tree(files)
    core.receipts.history.validate(files, records, commit)
    additions, inventory = {}, []
    for path in sorted(files):
        if not path.startswith("control/receipts/"):
            continue
        recovered = core.receipts.history.recovered(path, files, trees)
        for record in recovered:
            target = f"knowledge/{record['kind']}/{record['id']}.yaml"
            if target not in files:
                additions[target] = record
        receipt = decode(files[path])
        for result in receipt["results"]:
            revision = result["revisions"][0]
            node = revision["resource"]["resource_kind"] == "node"
            kind = "node_revision" if node else "relation_revision"
            target = f"knowledge/{kind}/{revision['revision_id']}.yaml"
            status = "complete"
            for record in recovered:
                recovered_ref = record.get("revision_ref", {})
                identifier = recovered_ref.get("revision_id", record["id"])
                if identifier == revision["revision_id"]:
                    target = f"knowledge/{record['kind']}/{record['id']}.yaml"
                    if target not in files:
                        status = "missing_node_snapshot" if node else "missing_relation_revision"
            inventory.append({"receipt": path, "status": status, "record": target})
    # Validate the complete prospective record set during dry-run too, so a
    # conflicting recovered revision ID never becomes an apparently eligible plan.
    prospective = dict(records)
    for record in additions.values():
        core.contracts.parse("knowledge", record)
        key = record["kind"], record["id"]
        if key in prospective:
            core.boundary.fail("REPAIR_REQUIRED")
        prospective[key] = record
    core.domain.validate(prospective, decode(files["control/metadata.json"]))
    # Even an empty legacy tree needs an explicit profile transition.
    binding = dict(source_commit=commit, source_generation=generation, additions=additions)
    return {
        **binding,
        "plan_digest": digest(binding),
        "inventory": inventory,
        "status": "complete" if HISTORY in files else "eligible",
        "blocking": [],
    }


def inspect_history(core: Core) -> dict[str, object]:
    """Return a deterministic dry-run inventory without allocating or writing objects."""
    _require_host(core)
    try:
        plan = _plan(core)
        # Preserve forensic classifications and dry-run non-mutation. Full private
        # transition verification also works when the disposable index is absent.
        from .verification import TransitionVerifier

        projection = core.history_index.empty()
        try:
            TransitionVerifier(core.repository, projection).verify(
                core.store.changes(None, plan["source_commit"])
            )
        finally:
            projection.close()
        return plan
    except HistoricalEvidenceError as exc:
        return {
            "status": "repair_required",
            "blocking": [exc.category],
            "inventory": [{"status": exc.category}],
            "additions": {},
        }
    except (StorageError, OSError):
        return {
            "status": "repair_required",
            "blocking": ["unavailable_original_effects"],
            "inventory": [{"status": "unavailable_original_effects"}],
            "additions": {},
        }
    except (CoreError, KeyError, ValueError, TypeError, ValidationError, SchemaError):
        return {
            "status": "repair_required",
            "blocking": ["corrupt_original_effects"],
            "inventory": [{"status": "corrupt_original_effects"}],
            "additions": {},
        }
    except Exception as exc:
        raise CoreError(core.contracts, "INTERNAL") from exc


def apply_history_migration(core: Core, plan: dict[str, object]) -> HistoryBaseline:
    """Apply exactly a reviewed dry-run plan once under the existing writer/CAS fence."""
    _require_host(core)
    if not isinstance(plan, dict):
        core.boundary.fail("VALIDATION_FAILED")
    try:
        with core.store.writer():
            commit, files, _, _, _ = core.repository.snapshot(locked=True)
            if HISTORY in files:
                marker = decode(files[HISTORY])
                if marker["mode"] == "migrated" and marker["plan_digest"] == plan.get(
                    "plan_digest"
                ):
                    if _plan(core, marker["source_commit"]) != plan:
                        core.boundary.fail("REPAIR_REQUIRED")
                    return core.contracts.parse_as("transaction", marker, HistoryBaseline)
                core.boundary.fail("REVISION_CONFLICT")
            if commit != plan.get("source_commit"):
                core.boundary.fail("REVISION_CONFLICT")
            actual = _plan(core)
            if plan != actual or actual["blocking"]:
                core.boundary.fail("REPAIR_REQUIRED")
            additions = actual["additions"]
            for path, record in additions.items():
                core.repository.pack(record, files)
                if decode(files[path]) != record:
                    core.boundary.fail("REPAIR_REQUIRED")
            generation = core.repository.generation(files)
            marker = dict(
                kind="history_baseline",
                schema_version=VERSION,
                instance_id=core.context.instance_id,
                mode="migrated",
                actor={"principal_id": core.context.principal.principal_id},
                generation=generation,
                source_commit=commit,
                source_generation=actual["source_generation"],
                plan_digest=actual["plan_digest"],
                additions=sorted(additions),
                effects_digest=digest(additions),
            )
            result = core.contracts.parse_as("transaction", marker, HistoryBaseline)
            files[HISTORY] = encode(core.contracts.dump("transaction", result))
            files[GENERATION] = encode(generation)
            candidate = core.store.prepare(files, commit)
            _, records, _ = core.repository.parse_tree(files)
            core.receipts.history.validate(files, records, candidate)
            core.store.publish(candidate, commit)
            return result
    except PublicationConflict as exc:
        raise CoreError(core.contracts, "REVISION_CONFLICT") from exc
    except (
        StorageError,
        OSError,
        KeyError,
        ValueError,
        TypeError,
        ValidationError,
        SchemaError,
    ) as exc:
        raise CoreError(core.contracts, "REPAIR_REQUIRED") from exc
    except CoreError:
        raise
    except Exception as exc:
        raise CoreError(core.contracts, "INTERNAL") from exc
