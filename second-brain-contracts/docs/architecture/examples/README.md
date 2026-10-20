# Illustrative contracts

These schemas intentionally cover a small subset of the [proposed families](../contracts-spec.md), not all future fields/kinds/predicates. They have unpublished `example.invalid` IDs and version 0.1.0. Do not import them as a production v1 package. Shared primitive definitions are temporarily in Node to demonstrate local and cross-file `$ref`; M1 will extract reviewed common primitives before production use.

`openapi-example.yaml` uses JSON syntax, a valid YAML 1.2 representation, to permit syntax checking without adding a YAML dependency. Its external Node ref illustrates the HTTP binding boundary; error payloads are intentionally unmodeled until the common Error contract is approved. No server, token provider, or HTTP generator has been selected.

Fixtures are fabricated. `fixtures/valid` means structurally valid only: no actual principal/provenance/target registry is supplied. The invalid node must fail the `type` check at `/title`; invalid cluster must fail `format` at `/created_at`. The offline check also probes extra properties, null versus omission, enums, safe-integer bounds, nested references and timestamp spelling. Semantic cases such as “updated before created” remain the application's responsibility; schema success is not permission to persist.

Run `python tools/validate_examples.py` from the portable module root. See the [validation record](../validation.md) for executed scope and limitations.
