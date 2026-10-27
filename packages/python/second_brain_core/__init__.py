"""M1 private-cluster, committed Git knowledge foundation."""

from .application import Core
from .boundary import CoreError, InstanceContext, TrustedPrincipal
from .git_store import GitStore
from .maintenance import (
    adopt_generation_commitment,
    audit_history,
    collect_history_index,
    compact_history_index,
    maintain_history_index,
    rebuild_history_index,
    upgrade_history_index,
)
from .migration import apply_history_migration, inspect_history

__all__ = [
    "Core",
    "CoreError",
    "GitStore",
    "InstanceContext",
    "TrustedPrincipal",
    "adopt_generation_commitment",
    "apply_history_migration",
    "audit_history",
    "collect_history_index",
    "compact_history_index",
    "inspect_history",
    "maintain_history_index",
    "rebuild_history_index",
    "upgrade_history_index",
]
