"""Deny-by-default access to supported private Cluster selections."""

from functools import partial

from .boundary import ContractBoundary, digest


class AccessControl:
    def __init__(self, boundary: ContractBoundary) -> None:
        self.boundary = boundary

    def allowed(self, cluster_id, action):
        return (cluster_id, action) in self.boundary.context.principal.grants

    def cluster(self, records, identifier, action):
        if not self.allowed(identifier, action):
            self.boundary.fail("NOT_FOUND")
        cluster = records.get(("cluster", identifier))
        if not cluster or cluster["lifecycle"] != "active":
            self.boundary.fail("NOT_FOUND")
        if cluster["publication_mode"] != "private":
            self.boundary.fail("APPROVAL_REQUIRED")
        return cluster

    def node(self, records, identifier, selected=None):
        memberships = [
            r
            for (k, _), r in records.items()
            if k == "membership" and r["node_id"] == identifier and r["lifecycle"] == "active"
        ]
        # O4 composition is deliberately unsupported, never unioned implicitly.
        if len(memberships) != 1:
            self.boundary.fail("NOT_FOUND")
        cluster = memberships[0]["cluster_id"]
        if selected is not None and selected != cluster:
            self.boundary.fail("NOT_FOUND")
        self.cluster(records, cluster, "node.read")
        node = records.get(("node", identifier))
        if not node or node["lifecycle"] != "active":
            self.boundary.fail("NOT_FOUND")
        return node

    def relation(self, records, identifier, selected=None):
        relation = records.get(("relation", identifier))
        if not relation or (selected is not None and selected != relation["owner_cluster_id"]):
            self.boundary.fail("NOT_FOUND")
        self.cluster(records, relation["owner_cluster_id"], "relation.read")
        self.node(records, relation["source"]["id"])
        self.node(records, relation["target"]["id"])
        return relation

    def check_expectations(self, operation, records):
        for expectation in operation["expectations"]:
            resource = expectation["resource"]
            if resource["instance_id"] != self.boundary.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            kind, identifier = resource["resource_kind"], resource["id"]
            selectors = {
                "cluster": partial(self.cluster, records, identifier, operation["operation"]),
                "node": partial(self.node, records, identifier),
                "relation": partial(self.relation, records, identifier),
            }
            selector = selectors.get(kind)
            if selector is None:
                self.boundary.fail("VALIDATION_FAILED")
            record = selector()
            if record["revision"] != expectation["expected_revision"]:
                self.boundary.fail("REVISION_CONFLICT")
            if (
                "expected_digest" in expectation
                and digest(record) != expectation["expected_digest"]
            ):
                self.boundary.fail("REVISION_CONFLICT")
