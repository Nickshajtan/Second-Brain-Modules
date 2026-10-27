# ADR-014: Versioned SHA256 content commitments

Status: adopted M2.2.2 design after independent Stage A review. Runtime validation
and final acceptance remain separate in [the validation report](../../core/m2-2-2-validation.md).
Baseline: `80a24eedb0379b15e4fd9a9d5975486d04cc0558`.

## Decision

Preserve the historical sorted path/SHA256-map generation digest whenever
GenerationRef omits `commitment_scheme`. Add the optional exact value
`sha256-bucket16-v1` for the new canonical content commitment. Digest.algorithm
still names SHA256, not a tree algorithm. This is an explicit unreleased 1.0.0
amendment: old closed readers reject new producers emitting the field.

The [precise binary specification](../../core/m2-2-2-merkle-hardening.md#proposed-canonical-commitment)
binds purpose/version, instance, paths, content SHA256 values, bucket identity,
entry count and ordered branches. The 16-level directory commits complete
path/value buckets. It updates only affected buckets and ancestors. Routing-prefix
collisions do not alias paths; worst-case work is O(affected bucket occupancy + 16)
per changed path, not a worst-case logarithmic guarantee.

Git-native trees remain the storage commitment and retained-history authority.
They do not replace the stronger SHA256 content commitment in SHA1 repositories.
No second Merkle structure covers authorization/index tables: ADR-013's complete
authenticated private-memory projection still protects negative lookups and
Membership completeness. No external cryptographic dependency is added.

Fresh trusted bootstrap emits the new scheme. Existing canonical history remains
unchanged. An explicit trusted-host `adopt_generation_commitment` publishes exactly
one generation-only transition; valid external adoption is also verifiable during
ordered catch-up. No historical host-identity authentication is inferred from that
unsigned Git transition. Once adopted, downgrade or ambiguous first adoption in a
content mutation fails closed. Existing receipt/generation/revision IDs and bytes
remain exact; historical verification dispatches by each descriptor's own scheme.

Derived format 4 adds leaf/branch tables; explicit upgrade authenticates the known
predecessor binding, exact base/tail/key/enrollment and accepted rollback frontier,
then fully verifies Git before adopting new derived state. It does not implicitly
adopt the new canonical scheme. Unknown predecessor fingerprints fail closed.

## Costs and limits

Stage A's real 100/1,000/10,000-generation updates each computed the complete flat
commitment twice. At 10,000 this visited 5,515 paths and hashed two 720,947-byte
maps. Generation construction took 0.030482 seconds versus 0.369614 seconds in Git
preparation; hashing was not the dominant measured latency. The decision removes
growing structural work, without promising an overall speedup.

Initial build, cold base authentication, compaction, audit/rebuild and GC inventory
remain proportional to their inputs. Git uses its existing isolated native index;
its metadata/fanout work remains. Concentrated buckets are explicitly tested and
reported. No cloud indexing, embeddings, search, Relation mutation, scheduler,
storage framework or Owner policy decision is introduced.
