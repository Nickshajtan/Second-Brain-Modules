"""Canonical record encoding and validated, pinned committed snapshots."""

import hashlib

from .boundary import GENERATION, CoreError, digest, uid
from .codec import decode, encode


class KnowledgeRepository:
    def __init__(self, boundary, store, domain, receipts):
        self.boundary = boundary
        self.store = store
        self.domain = domain
        self.receipts = receipts

    def pack(self, record, files):
        record = decode(encode(record))
        kind, identifier = record["kind"], record["id"]
        self.boundary.contracts.parse("knowledge", record)
        if kind == "node":
            files[f"knowledge/node/{identifier}.md"] = record["content"].pop("body").encode("utf-8")
        files[f"knowledge/{kind}/{identifier}.yaml"] = encode(record)

    def generation(self, files):
        # Generation digest binds canonical knowledge/config bytes, excluding
        # receipts and this descriptor to avoid a self-referential hash.
        content = {
            p: hashlib.sha256(raw).hexdigest()
            for p, raw in files.items()
            if p.startswith("knowledge/") or p == "control/metadata.json"
        }
        return {
            "instance_id": self.boundary.context.instance_id,
            "generation_id": uid(),
            "digest": digest(content),
        }

    def snapshot(self):
        try:
            commit = self.store.resolve()
            if commit is None:
                self.boundary.fail("REPAIR_REQUIRED")
            files = self.store.read(commit)
            generation = decode(files[GENERATION])
            schema = self.boundary.contracts.schemas["common"]["$defs"]["GenerationRef"]
            self.boundary.contracts.validators["common"].evolve(schema=schema).validate(generation)
            if generation["instance_id"] != self.boundary.context.instance_id:
                self.boundary.fail("REPAIR_REQUIRED")
            if generation["digest"] != self.generation(files)["digest"]:
                self.boundary.fail("REPAIR_REQUIRED")
            records = {}
            expected = {GENERATION, "control/metadata.json"}
            for path, raw in files.items():
                if path.startswith("knowledge/") and path.endswith(".yaml"):
                    record = decode(raw)
                    kind, identifier = record["kind"], record["id"]
                    if path != f"knowledge/{kind}/{identifier}.yaml":
                        self.boundary.fail("REPAIR_REQUIRED")
                    if kind == "node":
                        body = f"knowledge/node/{identifier}.md"
                        record["content"]["body"] = files[body].decode("utf-8")
                        expected.add(body)
                    self.boundary.contracts.parse("knowledge", record)
                    records[kind, identifier] = record
                    expected.add(path)
                elif path.startswith("control/receipts/") and path.endswith(".json"):
                    request_path = self.receipts.validate_pair(path, files)
                    expected.update((path, request_path))
            if set(files) != expected:
                self.boundary.fail("REPAIR_REQUIRED")
            metadata = decode(files["control/metadata.json"])
            self.domain.metadata(metadata)
            self.domain.validate(records, metadata)
            self.receipts.validate_results(files, records)
            return commit, files, generation, records, metadata
        except Exception as exc:
            raise CoreError(self.boundary.contracts, "REPAIR_REQUIRED") from exc
