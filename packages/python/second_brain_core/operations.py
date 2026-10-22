"""Concrete M1 operation strategies; no runtime plugin registration."""

from .boundary import VERSION, digest, timestamp, uid


class NodeCreateStrategy:
    def __init__(self, boundary, access, domain):
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
        identifier = operation["request_id"]
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
        node = records["node", operation["request_id"]]
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
            or member["cluster_id"] != operation["payload"]["target_cluster_id"]
            or member["admitted_by"] != receipt["actor"]
            or (revision["recorded_by"] != receipt["actor"])
            or (result["resources"] != expected)
            or (result["revisions"] != [node["revision_ref"]])
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def authorize_replay(self, result, records):
        action = result["operation"]
        resource = result["resources"][0]
        member = next(
            (
                r
                for (k, _), r in records.items()
                if k == "membership" and r["node_id"] == resource["id"]
            )
        )
        self.access.cluster(records, member["cluster_id"], action)
        self.access.cluster(records, member["cluster_id"], "membership.admit")


class RelationCreateStrategy:
    def __init__(self, boundary, access, domain):
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
        additions = [relation]
        revisions = [
            {
                "resource": self.boundary.resource("relation", relation["id"]),
                "revision_id": uid(),
                "revision": 1,
            }
        ]
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
    def __init__(self, boundary, access):
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
    def __init__(self, access):
        self.access = access

    def read(self, selection, records):
        return self.access.relation(
            records, selection["relation_id"], selection.get("selected_cluster_id")
        )
