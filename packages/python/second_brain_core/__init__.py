"""M1 private-cluster, committed Git knowledge foundation."""

from .application import Core
from .boundary import CoreError, InstanceContext, TrustedPrincipal
from .git_store import GitStore
from .maintenance import audit_history, compact_history_index, rebuild_history_index
from .migration import apply_history_migration, inspect_history

__all__ = [
    "Core",
    "CoreError",
    "GitStore",
    "InstanceContext",
    "TrustedPrincipal",
    "apply_history_migration",
    "audit_history",
    "compact_history_index",
    "inspect_history",
    "rebuild_history_index",
]
