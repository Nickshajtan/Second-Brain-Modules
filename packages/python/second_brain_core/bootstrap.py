"""Trusted fixture/bootstrap initialization, separate from public operations."""

from .boundary import GENERATION
from .codec import decode, encode


class BootstrapInitializer:
    def __init__(self, boundary, store, repository, domain):
        self.boundary = boundary
        self.store = store
        self.repository = repository
        self.domain = domain

    def initialize(self, records, metadata_schemas):
        """Explicit trusted fixture initializer; never an operation payload handler."""
        if not self.boundary.context.principal.bootstrap:
            self.boundary.fail("FORBIDDEN")
        files, accepted = {}, {}
        for value in records:
            record = self.boundary.dump("knowledge", self.boundary.ingest("knowledge", value))
            if record["kind"] not in {
                "cluster",
                "node_type_definition",
                "relation_type_definition",
            }:
                self.boundary.fail("VALIDATION_FAILED")
            if (
                record["kind"] == "cluster"
                and record["owner"]["principal_id"] != self.boundary.context.principal.principal_id
            ):
                self.boundary.fail("FORBIDDEN")
            key = record["kind"], record["id"]
            if key in accepted:
                self.boundary.fail("VALIDATION_FAILED")
            accepted[key] = record
            self.repository.pack(record, files)
        metadata = decode(encode(metadata_schemas))
        self.domain.metadata(metadata)
        self.domain.validate(accepted, metadata)
        for record in accepted.values():
            if (
                record["kind"] == "node_type_definition"
                and record["metadata_schema_id"] not in metadata
            ):
                self.boundary.fail("VALIDATION_FAILED")
        files["control/metadata.json"] = encode(metadata)
        generation = self.repository.generation(files)
        files[GENERATION] = encode(generation)
        with self.store.writer():
            if self.store.resolve() is not None:
                self.boundary.fail("REVISION_CONFLICT")
            candidate = self.store.prepare(files, None)
            self.store.publish(candidate, None)
        return generation
