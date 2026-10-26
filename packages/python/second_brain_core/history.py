"""Original committed effects, separate from live authorization and resource heads."""

from uuid import UUID

from .boundary import GENERATION, VERSION, CoreError, digest
from .codec import decode

HISTORY = "control/history.json"


class HistoricalEvidenceError(CoreError):
    def __init__(self, contracts, category: str) -> None:
        self.category = category
        super().__init__(contracts, "REPAIR_REQUIRED")


class HistoricalEffects:
    def __init__(self, repository) -> None:
        self.repository = repository
        self.boundary = repository.boundary

    def fail(self, category="inconsistent_history"):
        raise HistoricalEvidenceError(self.boundary.contracts, category)

    def trees(self, commit):
        """Read retained linear ancestry once per verification, never mutable files."""
        return [
            (oid, self.repository.store.read(oid)) for oid in self.repository.store.ancestry(commit)
        ]

    def origin(self, receipt_path, files, trees):
        receipt = decode(files[receipt_path])
        matches = [
            (oid, tree) for oid, tree in trees if decode(tree[GENERATION]) == receipt["generation"]
        ]
        if not matches:
            self.fail("unavailable_original_effects")
        if len(matches) != 1:
            self.fail("ambiguous_history")
        oid, original = matches[0]
        request_path = self.repository.receipts.request_path(receipt_path)
        position = next(i for i, (candidate, _) in enumerate(trees) if candidate == oid)
        if position + 1 == len(trees):
            self.fail("unavailable_original_effects")
        parent = trees[position + 1][1]
        if receipt_path in parent or request_path in parent:
            self.fail()
        if (
            original.get(receipt_path) != files[receipt_path]
            or original.get(request_path) != files[request_path]
        ):
            self.fail()
        request = decode(original[request_path])
        if request["expected_generation"] != decode(parent[GENERATION]):
            self.fail()
        for operation, result in zip(request["operations"], receipt["results"], strict=True):
            for resource in result["resources"]:
                effect_path = f"knowledge/{resource['resource_kind']}/{resource['id']}.yaml"
                if effect_path in parent:
                    self.fail()
            for revision in result["revisions"]:
                kind = (
                    "node_revision"
                    if revision["resource"]["resource_kind"] == "node"
                    else "relation_revision"
                )
                if f"knowledge/{kind}/{revision['revision_id']}.yaml" in parent:
                    self.fail()
            if operation["operation"] == "node.create":
                members = [
                    resource
                    for resource in result["resources"]
                    if resource["resource_kind"] == "membership"
                ]
                if len(members) != 1:
                    self.fail("insufficient_admission_evidence")
                path = f"knowledge/membership/{members[0]['id']}.yaml"
                if path not in original:
                    self.fail("insufficient_admission_evidence")
                member = decode(original[path])
                if member["admitted_by"] != receipt["actor"] or (
                    member["cluster_id"] != operation["payload"]["target_cluster_id"]
                ):
                    self.fail("insufficient_admission_evidence")
        generation, records, metadata = self.repository.parse_tree(original)
        self.repository.receipts.validate_pair(receipt_path, original)
        return oid, original, generation, records, metadata

    def recovered(self, receipt_path, files, trees):
        """Return deterministic missing evidence using only its original tree."""
        _, original, generation, records, _ = self.origin(receipt_path, files, trees)
        receipt = decode(files[receipt_path])
        request = decode(files[self.repository.receipts.request_path(receipt_path)])
        additions = []
        for operation, result in zip(request["operations"], receipt["results"], strict=True):
            strategy = self.repository.receipts.strategies.get(operation["operation"])
            if strategy is None:
                self.fail()
            if operation["operation"] == "node.create":
                members = [
                    records.get(("membership", resource["id"]))
                    for resource in result["resources"]
                    if resource["resource_kind"] == "membership"
                ]
                if (
                    len(members) != 1
                    or members[0] is None
                    or (
                        members[0]["cluster_id"] != operation["payload"]["target_cluster_id"]
                        or members[0]["admitted_by"] != receipt["actor"]
                    )
                ):
                    self.fail("insufficient_admission_evidence")
            strategy.verify_result(operation, result, receipt, records)
            ref = result["revisions"][0]
            identifier = ref["resource"]["id"]
            if operation["operation"] == "node.create":
                revision = records["node_revision", ref["revision_id"]]
                if "snapshot" not in revision:
                    if HISTORY in original:
                        self.fail()
                    # A supplement is evidence about the original revision, not another revision.
                    additions.append(
                        dict(
                            kind="node_revision_snapshot",
                            id=str(
                                UUID(
                                    hex=digest(
                                        [
                                            "node-revision-snapshot",
                                            self.boundary.context.instance_id,
                                            ref["revision_id"],
                                        ]
                                    )["value"][:32],
                                    version=4,
                                )
                            ),
                            schema_version=VERSION,
                            revision_ref=ref,
                            snapshot=records["node", identifier]["content"],
                            digest=revision["digest"],
                            source_generation=generation,
                        )
                    )
            else:
                history = records.get(("relation_revision", ref["revision_id"]))
                if history is None:
                    if HISTORY in original:
                        self.fail()
                    history = dict(
                        kind="relation_revision",
                        id=ref["revision_id"],
                        schema_version=VERSION,
                        relation_id=identifier,
                        logical_revision=1,
                        snapshot=records["relation", identifier],
                        digest=digest(records["relation", identifier]),
                        recorded_by=receipt["actor"],
                        recorded_at=receipt["committed_at"],
                    )
                    additions.append(history)
        return additions

    def baseline(self, files, trees):
        markers = [(oid, tree) for oid, tree in trees if HISTORY in tree]
        if not markers:
            return False
        if HISTORY not in files or any(tree[HISTORY] != files[HISTORY] for _, tree in markers):
            self.fail()
        origin_oid, origin = markers[-1]
        self.repository.parse_tree(origin)
        marker = decode(files[HISTORY])
        self.boundary.contracts.parse("transaction", marker)
        if marker["instance_id"] != self.boundary.context.instance_id:
            self.fail()
        if marker["generation"] != decode(origin[GENERATION]):
            self.fail()
        paths = marker["additions"]
        if marker["effects_digest"] != digest({path: decode(origin[path]) for path in paths}):
            self.fail()
        if marker["mode"] == "fresh":
            if paths or origin_oid != trees[-1][0]:
                self.fail()
        else:
            index = next(i for i, (oid, _) in enumerate(trees) if oid == origin_oid)
            if index + 1 == len(trees) or trees[index + 1][0] != marker["source_commit"]:
                self.fail()
            source = trees[index + 1][1]
            if decode(source[GENERATION]) != marker["source_generation"]:
                self.fail()
            additions = {}
            for path in source:
                if path != GENERATION and origin.get(path) != source[path]:
                    self.fail()
            for path in origin.keys() - source.keys() - {HISTORY}:
                additions[path] = decode(origin[path])
            if sorted(additions) != paths or marker["plan_digest"] != digest(
                {
                    "source_commit": marker["source_commit"],
                    "source_generation": marker["source_generation"],
                    "additions": additions,
                }
            ):
                self.fail()
            # A migration marker must explain additions using the original receipts.
            expected = {}
            for path in source:
                if path.startswith("control/receipts/"):
                    for record in self.recovered(path, source, trees[index + 1 :]):
                        target = f"knowledge/{record['kind']}/{record['id']}.yaml"
                        if target not in source:
                            expected[target] = record
            if additions != expected:
                self.fail()
        return True

    def validate(self, files, records, commit):
        trees = self.trees(commit)
        # Current-only iteration cannot detect deleting an entire transaction.
        # Derive the retained evidence obligation from every committed ancestor;
        # heads and live Memberships deliberately remain outside this byte lock.
        immutable = (
            "control/receipts/",
            "control/requests/",
            "knowledge/node_revision/",
            "knowledge/relation_revision/",
            "knowledge/node_revision_snapshot/",
        )
        for _, tree in trees:
            for path, raw in tree.items():
                if path.startswith(immutable) and files.get(path) != raw:
                    self.fail()
        marked = self.baseline(files, trees)
        if not marked and any(kind == "node_revision_snapshot" for kind, _ in records):
            self.fail()
        explained = set()
        for path in files:
            if not path.startswith("control/receipts/"):
                continue
            _, original, _, effects, _ = self.origin(path, files, trees)
            receipt = decode(files[path])
            request = decode(files[self.repository.receipts.request_path(path)])
            for operation, result in zip(request["operations"], receipt["results"], strict=True):
                self.repository.receipts.strategies[operation["operation"]].verify_result(
                    operation, result, receipt, effects
                )
                ref = result["revisions"][0]
                kind = (
                    "node_revision"
                    if operation["operation"] == "node.create"
                    else "relation_revision"
                )
                key = kind, ref["revision_id"]
                if key in effects:
                    if records.get(key) != effects[key]:
                        self.fail()
                    explained.add(key)
                elif HISTORY in original:
                    self.fail()
            for recovered in self.recovered(path, files, trees):
                key = recovered["kind"], recovered["id"]
                if marked and records.get(key) != recovered:
                    self.fail()
                if key in records:
                    if records[key] != recovered:
                        self.fail()
                    explained.add(key)
        for key in records:
            if (
                key[0] in {"node_revision", "relation_revision", "node_revision_snapshot"}
                and key not in explained
            ):
                self.fail()
