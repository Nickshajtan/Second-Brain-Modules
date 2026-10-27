"""Concrete M1 operation strategies; no runtime plugin registration."""

from .access import AccessControl
from .boundary import VERSION, ContractBoundary, digest, timestamp, uid
from .domain import DomainRules


def _definition(index, kind, key, version):
    return [
        (kind, path.rsplit("/", 1)[1][:-5])
        for (path,) in index.query(
            "SELECT path FROM definitions WHERE kind=? AND key=? AND version=?",
            (kind, key, version),
        )
    ]


class NodeCreateStrategy:
    def __init__(
        self, boundary: ContractBoundary, access: AccessControl, domain: DomainRules
    ) -> None:
        self.boundary = boundary
        self.access = access
        self.domain = domain

    def screen(self, operation, index, pending):
        payload = operation["payload"]
        cluster = payload["target_cluster_id"]
        self.access.screen_cluster(index, cluster, "node.create")
        self.access.screen_cluster(index, cluster, "membership.admit")
        identifier = payload.get("node_id", operation["request_id"])
        existing = self.access.projected(index, "node", identifier, pending)
        if existing is not None:
            self.access.screen_node(index, identifier, pending=pending)
        self.access.screen_expectations(operation, index, pending)
        if existing is None:
            pending["node", identifier] = dict(lifecycle="active", membership_cluster=cluster)

    def dependencies(self, operation, index):
        payload = operation["payload"]
        dependencies = [
            ("cluster", payload["target_cluster_id"]),
            ("node", payload.get("node_id", operation["request_id"])),
        ]
        dependencies.extend(
            _definition(
                index,
                "node_type_definition",
                payload["content"]["node_type"],
                payload["content"]["node_type_version"],
            )
        )
        return dependencies

    def prepare(self, operation, records, metadata):
        action = operation["operation"]
        actor, now = {"principal_id": self.boundary.context.principal.principal_id}, timestamp()
        payload = operation["payload"]
        cluster_id = payload["target_cluster_id"]
        self.access.cluster(records, cluster_id, action)
        self.access.cluster(records, cluster_id, "membership.admit")
        self.domain.content(payload["content"], records, metadata)
        identifier = payload.get("node_id", operation["request_id"])
        revision = {
            "resource": self.boundary.resource("node", identifier),
            "revision_id": uid(),
            "revision": 1,
        }
        node = dict(
            kind="node",
            id=identifier,
            schema_version=VERSION,
            revision=1,
            content=payload["content"],
            revision_ref=revision,
            lifecycle="active",
            created_at=now,
            updated_at=now,
        )
        history = dict(
            kind="node_revision",
            id=revision["revision_id"],
            schema_version=VERSION,
            node_id=identifier,
            logical_revision=1,
            digest=digest(payload["content"]),
            recorded_by=actor,
            recorded_at=now,
            provenance=payload["content"]["provenance"],
            snapshot=payload["content"],
        )
        membership = dict(
            kind="membership",
            id=uid(),
            schema_version=VERSION,
            revision=1,
            cluster_id=cluster_id,
            node_id=identifier,
            admitted_by=actor,
            admitted_at=now,
            admission_provenance=[],
            lifecycle="active",
        )
        additions, revisions = ([node, history, membership], [revision])
        return additions, revisions

    def verify_result(self, operation, result, receipt, records):
        node = records["node", operation["payload"].get("node_id", operation["request_id"])]
        members = [
            r for (k, _), r in records.items() if k == "membership" and r["node_id"] == node["id"]
        ]
        member = members[0]
        revision = records["node_revision", node["revision_ref"]["revision_id"]]
        expected = [
            self.boundary.resource("node", node["id"]),
            self.boundary.resource("membership", member["id"]),
        ]
        if (
            node["content"] != operation["payload"]["content"]
            or node["revision"] != 1
            or revision["logical_revision"] != 1
            or revision["id"] != node["revision_ref"]["revision_id"]
            or revision["node_id"] != node["id"]
            or revision["digest"] != digest(operation["payload"]["content"])
            or revision["provenance"] != operation["payload"]["content"]["provenance"]
            or member["cluster_id"] != operation["payload"]["target_cluster_id"]
            or member["revision"] != 1
            or member["admitted_at"] != node["created_at"]
            or member["admitted_by"] != receipt["actor"]
            or (revision["recorded_by"] != receipt["actor"])
            or (result["resources"] != expected)
            or (result["revisions"] != [node["revision_ref"]])
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def authorize_replay(self, result, records):
        action = result["operation"]
        resource = result["resources"][0]
        members = [
            r
            for (k, _), r in records.items()
            if k == "membership" and r["node_id"] == resource["id"] and r["lifecycle"] == "active"
        ]
        if len(members) != 1 or ("node", resource["id"]) not in records:
            self.boundary.fail("NOT_FOUND")
        member = members[0]
        self.access.cluster(records, member["cluster_id"], action)
        self.access.cluster(records, member["cluster_id"], "membership.admit")


class RelationCreateStrategy:
    def __init__(
        self, boundary: ContractBoundary, access: AccessControl, domain: DomainRules
    ) -> None:
        self.boundary = boundary
        self.access = access
        self.domain = domain

    def screen(self, operation, index, pending):
        relation = operation["payload"]["relation"]
        self.access.screen_cluster(index, relation["owner_cluster_id"], "relation.create")
        for endpoint in (relation["source"], relation["target"]):
            if endpoint["instance_id"] != self.boundary.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            self.access.screen_node(index, endpoint["id"], pending=pending)
        existing = self.access.projected(index, "relation", relation["id"], pending)
        if existing is not None:
            self.access.screen_relation(index, relation["id"], pending=pending)
        self.access.screen_expectations(operation, index, pending)
        if existing is None:
            pending["relation", relation["id"]] = {
                key: relation[key] for key in ("owner_cluster_id", "source", "target", "lifecycle")
            }

    def dependencies(self, operation, index):
        relation = operation["payload"]["relation"]
        dependencies = [
            ("relation", relation["id"]),
            ("cluster", relation["owner_cluster_id"]),
            ("node", relation["source"]["id"]),
            ("node", relation["target"]["id"]),
        ]
        dependencies.extend(
            _definition(
                index,
                "relation_type_definition",
                relation["predicate"],
                relation["predicate_version"],
            )
        )
        return dependencies

    def prepare(self, operation, records, metadata):
        action = operation["operation"]
        payload = operation["payload"]
        relation = payload["relation"]
        self.access.cluster(records, relation["owner_cluster_id"], action)
        if any(
            relation[key]["instance_id"] != self.boundary.context.instance_id
            for key in ("source", "target")
        ):
            self.boundary.fail("NOT_FOUND")
        self.access.node(records, relation["source"]["id"])
        self.access.node(records, relation["target"]["id"])
        self.domain.relation(relation, records)
        if relation["revision"] != 1 or relation["lifecycle"] != "active":
            self.boundary.fail("VALIDATION_FAILED")
        revisions = [
            {
                "resource": self.boundary.resource("relation", relation["id"]),
                "revision_id": uid(),
                "revision": 1,
            }
        ]
        history = dict(
            kind="relation_revision",
            id=revisions[0]["revision_id"],
            schema_version=VERSION,
            relation_id=relation["id"],
            logical_revision=1,
            snapshot=relation,
            digest=digest(relation),
            recorded_by={"principal_id": self.boundary.context.principal.principal_id},
            recorded_at=timestamp(),
        )
        additions = [relation, history]
        return additions, revisions

    def verify_result(self, operation, result, receipt, records):
        relation = operation["payload"]["relation"]
        reference = self.boundary.resource("relation", relation["id"])
        if (
            records["relation", relation["id"]] != relation
            or result["resources"] != [reference]
            or len(result["revisions"]) != 1
            or (result["revisions"][0]["resource"] != reference)
            or (result["revisions"][0]["revision"] != relation["revision"])
            or relation["revision"] != 1
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        history = records.get(("relation_revision", result["revisions"][0]["revision_id"]))
        if history is not None and (
            history["snapshot"] != relation or history["recorded_by"] != receipt["actor"]
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def authorize_replay(self, result, records):
        action = result["operation"]
        resource = result["resources"][0]
        relation = records["relation", resource["id"]]
        self.access.cluster(records, relation["owner_cluster_id"], action)
        self.access.node(records, relation["source"]["id"])
        self.access.node(records, relation["target"]["id"])


class NodeReadStrategy:
    def __init__(self, boundary: ContractBoundary, access: AccessControl) -> None:
        self.boundary = boundary
        self.access = access

    def read(self, selection, records):
        record = self.access.node(
            records, selection["node_id"], selection.get("selected_cluster_id")
        )
        if "revision" in selection and selection["revision"] != record["revision_ref"]:
            self.boundary.fail("NOT_FOUND")
        return record


class RelationReadStrategy:
    def __init__(self, access: AccessControl) -> None:
        self.access = access

    def read(self, selection, records):
        return self.access.relation(
            records, selection["relation_id"], selection.get("selected_cluster_id")
        )


class NodeUpdateStrategy:
    def __init__(
        self, boundary: ContractBoundary, access: AccessControl, domain: DomainRules
    ) -> None:
        self.boundary = boundary
        self.access = access
        self.domain = domain

    def screen(self, operation, index, pending):
        self.access.screen_node(
            index, operation["payload"]["node_id"], actions=("node.update",), pending=pending
        )
        self.access.screen_expectations(operation, index, pending)

    def dependencies(self, operation, index):
        content = operation["payload"]["content"]
        targets = [("node", operation["payload"]["node_id"])]
        targets.extend(
            _definition(
                index, "node_type_definition", content["node_type"], content["node_type_version"]
            )
        )
        current = index.record("node", operation["payload"]["node_id"])
        if current and current["content"]["node_type"] != content["node_type"]:
            targets.extend(
                ("relation", identifier)
                for (identifier,) in index.query(
                    "SELECT relation FROM endpoints WHERE node=?", (current["id"],)
                )
            )
        return targets

    def prepare(self, operation, records, metadata):
        node = self.access.node(records, operation["payload"]["node_id"], actions=("node.update",))
        expectations = [
            e
            for e in operation["expectations"]
            if e["resource"] == self.boundary.resource("node", node["id"])
        ]
        if len(expectations) != 1 or len(
            {
                (e["resource"]["resource_kind"], e["resource"]["id"])
                for e in operation["expectations"]
            }
        ) != len(operation["expectations"]):
            self.boundary.fail("VALIDATION_FAILED")
        self.access.check_expectations(operation, records)
        self.domain.content(operation["payload"]["content"], records, metadata)
        previous = node["revision_ref"]
        reference = dict(
            resource=previous["resource"], revision_id=uid(), revision=node["revision"] + 1
        )
        now = timestamp()
        content = operation["payload"]["content"]
        revised = dict(
            node,
            content=content,
            revision=reference["revision"],
            revision_ref=reference,
            updated_at=now,
        )
        history = dict(
            kind="node_revision",
            id=reference["revision_id"],
            schema_version=VERSION,
            node_id=node["id"],
            logical_revision=reference["revision"],
            previous=previous,
            digest=digest(content),
            recorded_by={"principal_id": self.boundary.context.principal.principal_id},
            recorded_at=now,
            provenance=content["provenance"],
            snapshot=content,
        )
        return [revised, history], [reference]

    def verify_result(self, operation, result, receipt, records):
        identifier = operation["payload"]["node_id"]
        node = records["node", identifier]
        revision = records["node_revision", node["revision_ref"]["revision_id"]]
        expected = [
            e
            for e in operation["expectations"]
            if e["resource"] == self.boundary.resource("node", identifier)
        ]
        if (
            len(expected) != 1
            or len(
                {
                    (e["resource"]["resource_kind"], e["resource"]["id"])
                    for e in operation["expectations"]
                }
            )
            != len(operation["expectations"])
            or node["content"] != operation["payload"]["content"]
            or node["revision"] != expected[0]["expected_revision"] + 1
            or result["resources"] != [self.boundary.resource("node", identifier)]
            or result["revisions"] != [node["revision_ref"]]
            or revision["node_id"] != identifier
            or revision["logical_revision"] != node["revision"]
            or revision.get("snapshot") != node["content"]
            or revision["digest"] != digest(node["content"])
            or revision["recorded_by"] != receipt["actor"]
            or revision["recorded_at"] != node["updated_at"]
            or revision["provenance"] != node["content"]["provenance"]
            or revision.get("previous", {}).get("revision") != node["revision"] - 1
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def authorize_replay(self, result, records):
        self.access.node(records, result["resources"][0]["id"], actions=("node.update",))


class NodeRevisionReadStrategy:
    def __init__(self, boundary: ContractBoundary, access: AccessControl) -> None:
        self.boundary = boundary
        self.access = access

    def read(self, selection, records):
        reference = selection["revision"]
        identifier = reference["resource"]["id"]
        self.access.node(records, identifier, actions=("node.read", "node.history.read"))
        revision = records.get(("node_revision", reference["revision_id"]))
        if (
            not revision
            or revision["node_id"] != identifier
            or revision["logical_revision"] != reference["revision"]
        ):
            self.boundary.fail("NOT_FOUND")
        if "snapshot" not in revision:
            supplements = [
                r
                for (k, _), r in records.items()
                if k == "node_revision_snapshot" and r["revision_ref"] == reference
            ]
            if len(supplements) != 1:
                self.boundary.fail("REPAIR_REQUIRED")
            revision = dict(revision, snapshot=supplements[0]["snapshot"])
        if digest(revision["snapshot"]) != revision["digest"]:
            self.boundary.fail("REPAIR_REQUIRED")
        return revision
