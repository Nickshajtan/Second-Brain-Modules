"""Concrete M1 operation strategies; no runtime plugin registration."""

from .access import AccessControl
from .boundary import VERSION, ContractBoundary, digest, timestamp, uid
from .domain import DomainRules


class NodeCreateStrategy:
    def __init__(
        self, boundary: ContractBoundary, access: AccessControl, domain: DomainRules
    ) -> None:
        self.boundary = boundary
        self.access = access
        self.domain = domain

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
