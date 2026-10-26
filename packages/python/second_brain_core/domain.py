"""Registered meaning, admission and committed record invariants."""

from datetime import datetime

from jsonschema import Draft202012Validator, FormatChecker

from .boundary import ContractBoundary, digest


class DomainRules:
    def __init__(self, boundary: ContractBoundary) -> None:
        self.boundary = boundary

    def interval(self, value):
        if "valid_from" in value and "valid_until" in value:
            start = datetime.fromisoformat(value["valid_from"])
            end = datetime.fromisoformat(value["valid_until"])
            if start > end:
                self.boundary.fail("VALIDATION_FAILED")

    def content(self, content, records, metadata):
        definition = next(
            (
                r
                for (k, _), r in records.items()
                if k == "node_type_definition"
                and r["type_key"] == content["node_type"]
                and r["type_version"] == content["node_type_version"]
            ),
            None,
        )
        if not definition:
            self.boundary.fail("VALIDATION_FAILED")
        schema_id = definition["metadata_schema_id"]
        if content.get("metadata_schema_id", schema_id) != schema_id or schema_id not in metadata:
            self.boundary.fail("VALIDATION_FAILED")
        Draft202012Validator(metadata[schema_id], format_checker=FormatChecker()).validate(
            content["properties"]
        )
        self.interval(content)

    def relation(self, relation, records):
        self.interval(relation)
        source, target = relation["source"], relation["target"]
        if any(ref["instance_id"] != self.boundary.context.instance_id for ref in (source, target)):
            self.boundary.fail("NOT_FOUND")
        definition = next(
            (
                r
                for (k, _), r in records.items()
                if k == "relation_type_definition"
                and r["predicate"] == relation["predicate"]
                and r["type_version"] == relation["predicate_version"]
            ),
            None,
        )
        if not definition:
            self.boundary.fail("VALIDATION_FAILED")
        for endpoint, allowed in ((source, "source_node_types"), (target, "target_node_types")):
            node = records.get(("node", endpoint["id"]))
            if not node:
                self.boundary.fail("NOT_FOUND")
            if node["content"]["node_type"] not in definition[allowed]:
                self.boundary.fail("VALIDATION_FAILED")
        if source["id"] == target["id"] and not definition["self_links_allowed"]:
            self.boundary.fail("VALIDATION_FAILED")

    def validate(self, records, metadata):
        self._unique_definitions(records)
        validators = {
            "cluster": self._cluster,
            "membership": self._membership,
            "node": self._node,
            "node_revision": self._node_revision,
            "relation": self._relation,
            "relation_revision": self._relation_revision,
            "node_revision_snapshot": self._node_snapshot,
        }
        definitions = {"node_type_definition", "relation_type_definition"}
        identities, sequences, supplements = set(), set(), set()
        for (kind, _), record in records.items():
            if kind in {"node_revision", "relation_revision"}:
                resource = record["node_id"] if kind == "node_revision" else record["relation_id"]
                sequence = (kind, resource, record["logical_revision"])
                if record["id"] in identities or sequence in sequences:
                    self.boundary.fail("REPAIR_REQUIRED")
                identities.add(record["id"])
                sequences.add(sequence)
                previous = record.get("previous")
                if record["logical_revision"] == 1:
                    if previous is not None:
                        self.boundary.fail("REPAIR_REQUIRED")
                else:
                    prior = records.get((kind, previous["revision_id"])) if previous else None
                    resource_kind = "node" if kind == "node_revision" else "relation"
                    if (
                        not prior
                        or previous["resource"] != self.boundary.resource(resource_kind, resource)
                        or previous["revision"] != record["logical_revision"] - 1
                        or prior["logical_revision"] != previous["revision"]
                        or prior.get("node_id", prior.get("relation_id")) != resource
                    ):
                        self.boundary.fail("REPAIR_REQUIRED")
            if kind == "node_revision_snapshot":
                revision_id = record["revision_ref"]["revision_id"]
                if revision_id in supplements:
                    self.boundary.fail("REPAIR_REQUIRED")
                supplements.add(revision_id)
            validator = validators.get(kind)
            if validator is not None:
                validator(record, records, metadata)
            elif kind not in definitions:
                self.boundary.fail("REPAIR_REQUIRED")

    def _unique_definitions(self, records):
        fields = {"node_type_definition": "type_key", "relation_type_definition": "predicate"}
        seen = set()
        for (kind, _), record in records.items():
            field = fields.get(kind)
            if field is None:
                continue
            key = (kind, record[field], record["type_version"])
            if key in seen:
                self.boundary.fail("REPAIR_REQUIRED")
            seen.add(key)

    def _cluster(self, record, records, metadata):
        if record["publication_mode"] != "private" or record["lifecycle"] != "active":
            self.boundary.fail("REPAIR_REQUIRED")

    def _membership(self, record, records, metadata):
        if ("cluster", record["cluster_id"]) not in records or (
            "node",
            record["node_id"],
        ) not in records:
            self.boundary.fail("REPAIR_REQUIRED")
        if (
            record["lifecycle"] != "active"
            or "approved_revision" in record
            or "approval_id" in record
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def _node(self, record, records, metadata):
        identifier = record["id"]
        self.content(record["content"], records, metadata)
        members = [
            r for (k, _), r in records.items() if k == "membership" and r["node_id"] == identifier
        ]
        ref = record["revision_ref"]
        revision = records.get(("node_revision", ref["revision_id"]))
        if len(members) != 1 or ref["resource"] != self.boundary.resource("node", identifier):
            self.boundary.fail("REPAIR_REQUIRED")
        if (
            not revision
            or revision["node_id"] != identifier
            or revision["logical_revision"] != record["revision"]
            or (ref["revision"] != record["revision"])
            or (revision["digest"] != digest(record["content"]))
        ):
            self.boundary.fail("REPAIR_REQUIRED")

    def _node_revision(self, record, records, metadata):
        if "snapshot" in record:
            self.content(record["snapshot"], records, metadata)
            if record["digest"] != digest(record["snapshot"]):
                self.boundary.fail("REPAIR_REQUIRED")
        if ("node", record["node_id"]) not in records:
            self.boundary.fail("REPAIR_REQUIRED")

    def _relation(self, record, records, metadata):
        if ("cluster", record["owner_cluster_id"]) not in records:
            self.boundary.fail("REPAIR_REQUIRED")
        # Public M2.1 remains create-only. Isolated future-head tests exercise the
        # historical verifier directly, not a relaxed public snapshot profile.
        histories = [
            r
            for (kind, _), r in records.items()
            if kind == "relation_revision" and r["relation_id"] == record["id"]
        ]
        if (
            record["revision"] != 1
            or record["lifecycle"] != "active"
            or (histories and (len(histories) != 1 or histories[0]["snapshot"] != record))
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        self.relation(record, records)

    def _relation_revision(self, record, records, metadata):
        snapshot = record["snapshot"]
        if (
            snapshot["id"] != record["relation_id"]
            or snapshot["revision"] != record["logical_revision"]
            or record["digest"] != digest(snapshot)
            or ("relation", record["relation_id"]) not in records
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        self.interval(snapshot)

    def _node_snapshot(self, record, records, metadata):
        ref = record["revision_ref"]
        revision = records.get(("node_revision", ref["revision_id"]))
        if (
            not revision
            or "snapshot" in revision
            or ref["resource"] != self.boundary.resource("node", revision["node_id"])
            or ref["revision"] != revision["logical_revision"]
            or record["source_generation"]["instance_id"] != self.boundary.context.instance_id
            or record["digest"] != revision["digest"]
            or record["digest"] != digest(record["snapshot"])
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        self.content(record["snapshot"], records, metadata)

    def metadata(self, metadata):
        if not isinstance(metadata, dict):
            self.boundary.fail("VALIDATION_FAILED")

        def check(part):
            if isinstance(part, dict):
                if any(k in part for k in ("$ref", "$dynamicRef", "$id", "$schema")):
                    self.boundary.fail("VALIDATION_FAILED")
                if "format" in part and part["format"] not in FormatChecker.checkers:
                    self.boundary.fail("VALIDATION_FAILED")
                for child in part.values():
                    check(child)
            elif isinstance(part, list):
                for child in part:
                    check(child)

        for schema in metadata.values():
            Draft202012Validator.check_schema(schema)
            check(schema)
