# Hardening impact assessment

The inspected Git root is Second-Brain-Modules, with an existing MIT license and a
tracked `second-brain-contracts/` delivery. There were no unit tests, package/lock
configuration, workflows or production runtime modules. The local raw export,
inventory and task prompt were untracked. They are not inputs to the new tests.

Minimal change: promote the existing `docs`, `tools`, README and text settings to
the Git root, retain schemas/fixtures at their existing documentation-relative
paths, and make that root the sole submodule boundary. This avoids duplicate
contract repositories and minimizes link changes. Add development tooling, tests,
generated illustrative models and CI; do not scaffold empty runtime domains.

The validator's class and CLI survive. Harden local reference allowlisting,
offline semantic OpenAPI validation, scoped document traversal and diagnostics.
Keep the first-delivery report as historical evidence, with explicit superseding
records. Update ADRs for whole-repository reuse and Stable revision pointers;
leave unrelated production questions open.
