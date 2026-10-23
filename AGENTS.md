# Engineering rules

- Before changing behavior, read the [domain baseline](docs/domain/domain-model.md),
  [current Core scope](docs/core/m1.md) and relevant [ADRs](docs/architecture/decisions/README.md).
- Canonical JSON Schema 2020-12 is the structural authority. Validate untrusted
  ingress and outgoing records canonically; generated types alone are insufficient.
- Never hand-edit generated Python/TS models or their manifests. Reuse generated
  types instead of handwritten domain DTOs; regenerate through the existing tools.
- Keep domain semantics independent of storage/transports. Preserve fail-closed
  authorization, instance isolation and conditional transaction publication.
- Do not invent Owner policy decisions or implement unsupported operations.
- Type new exported APIs and narrow infrastructure interfaces. Use Ruff alone for
  handwritten Python formatting. See [standards](docs/engineering/standards.md).
- Add focused regressions for confirmed defects; preserve existing fixtures and
  independent validators. Do not add dependencies/abstractions without a concrete need.
- Run relevant [quality commands](docs/engineering/standards.md) and report actual
  results, remaining risks and unverified platforms/durability claims.
- Preserve user changes. Do not remove uncertain/user-authored material, rewrite
  history, force-push or perform destructive cleanup. Historical evidence stays
  accessible; generated submodule-consumer artifacts remain tracked.
