"""Deny-by-default access to supported private Cluster selections."""

from functools import partial

from .boundary import ContractBoundary, digest


class AccessControl:
    def __init__(self, boundary: ContractBoundary) -> None:
        self.boundary = boundary

    def allowed(self, cluster_id, action):
        return (cluster_id, action) in self.boundary.context.principal.grants

    def projected(self, index, kind, identifier, pending=None):
        """Authenticated metadata can reject access; it never grants delivery."""
        if pending is not None and (kind, identifier) in pending:
            return pending[kind, identifier]
        return index.resource_metadata(kind, identifier)

    def screen_cluster(self, index, identifier, action):
        if not self.allowed(identifier, action):
            self.boundary.fail("NOT_FOUND")
        cluster = self.projected(index, "cluster", identifier)
        if not cluster or cluster.get("lifecycle") != "active":
            self.boundary.fail("NOT_FOUND")
        if cluster.get("publication_mode") != "private":
            self.boundary.fail("APPROVAL_REQUIRED")

    def screen_node(
        self, index, identifier, selected=None, *, actions=("node.read",), active=True, pending=None
    ):
        node = self.projected(index, "node", identifier, pending)
        if not node or (active and node.get("lifecycle") != "active"):
            self.boundary.fail("NOT_FOUND")
        if pending is not None and ("node", identifier) in pending:
            memberships = [dict(cluster_id=node["membership_cluster"], lifecycle="active")]
        else:
            memberships = index.membership_metadata(identifier)
        if len(memberships) != 1 or memberships[0].get("lifecycle") != "active":
            self.boundary.fail("NOT_FOUND")
        cluster = memberships[0]["cluster_id"]
        if selected is not None and selected != cluster:
            self.boundary.fail("NOT_FOUND")
        for action in actions:
            self.screen_cluster(index, cluster, action)

    def screen_relation(
        self, index, identifier, selected=None, *, action="relation.read", pending=None
    ):
        relation = self.projected(index, "relation", identifier, pending)
        if not relation or (selected is not None and selected != relation["owner_cluster_id"]):
            self.boundary.fail("NOT_FOUND")
        self.screen_cluster(index, relation["owner_cluster_id"], action)
        for endpoint in (relation["source"], relation["target"]):
            if endpoint["instance_id"] != self.boundary.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            self.screen_node(index, endpoint["id"], pending=pending)

    def screen_expectations(self, operation, index, pending):
        for expectation in operation["expectations"]:
            resource = expectation["resource"]
            if resource["instance_id"] != self.boundary.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            kind, identifier = resource["resource_kind"], resource["id"]
            selectors = {
                "cluster": partial(self.screen_cluster, index, identifier, operation["operation"]),
                "node": partial(
                    self.screen_node,
                    index,
                    identifier,
                    actions=(
                        ("node.update",)
                        if operation["operation"] == "node.update"
                        and identifier == operation["payload"]["node_id"]
                        else ("node.read",)
                    ),
                    pending=pending,
                ),
                "relation": partial(self.screen_relation, index, identifier, pending=pending),
            }
            selector = selectors.get(kind)
            if selector is None:
                self.boundary.fail("VALIDATION_FAILED")
            selector()

    def cluster(self, records, identifier, action):
        if not self.allowed(identifier, action):
            self.boundary.fail("NOT_FOUND")
        cluster = records.get(("cluster", identifier))
        if not cluster or cluster["lifecycle"] != "active":
            self.boundary.fail("NOT_FOUND")
        if cluster["publication_mode"] != "private":
            self.boundary.fail("APPROVAL_REQUIRED")
        return cluster

    def node(self, records, identifier, selected=None, *, actions=("node.read",)):
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
        for action in actions:
            self.cluster(records, cluster, action)
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
                "node": partial(
                    self.node,
                    records,
                    identifier,
                    actions=(
                        ("node.update",)
                        if operation["operation"] == "node.update"
                        and identifier == operation["payload"]["node_id"]
                        else ("node.read",)
                    ),
                ),
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
