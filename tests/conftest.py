import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from second_brain_contracts import ContractValidator
from second_brain_core import Core, GitStore, InstanceContext, TrustedPrincipal

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "repository with spaces"
    shutil.copytree(ROOT / "docs", root / "docs")
    shutil.copytree(ROOT / "contracts", root / "contracts")
    shutil.copytree(
        ROOT / "packages", root / "packages", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(ROOT / "tests/fixtures", root / "tests/fixtures")
    shutil.copyfile(ROOT / "README.md", root / "README.md")
    shutil.copyfile(ROOT / "LICENSE", root / "LICENSE")
    shutil.copyfile(ROOT / "AGENTS.md", root / "AGENTS.md")
    return root


@pytest.fixture(scope="module")
def contracts():
    return ContractValidator()


@pytest.fixture
def core(tmp_path, contracts):
    def uid():
        return str(uuid4())

    path = tmp_path / "managed repo with spaces"
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)
    instance, principal, cluster = uid(), uid(), uid()
    grants = frozenset(
        (cluster, a)
        for a in (
            "node.create",
            "membership.admit",
            "node.read",
            "relation.create",
            "relation.read",
        )
    )
    context = InstanceContext(
        instance, path, "refs/heads/brain", TrustedPrincipal(principal, grants, True)
    )
    app = Core(context, GitStore(path, context.managed_ref), contracts)
    records = [
        dict(
            kind="cluster",
            id=cluster,
            schema_version="1.0.0",
            revision=1,
            name="Приватний",
            owner={"principal_id": principal},
            policy={"policy_id": uid(), "version": 1},
            publication_mode="private",
            lifecycle="active",
        ),
        dict(
            kind="node_type_definition",
            id=uid(),
            schema_version="1.0.0",
            revision=1,
            type_key="note",
            type_version="1.0.0",
            metadata_schema_id="local:note:1",
            description="Fabricated note",
            flat_properties_required=True,
        ),
        dict(
            kind="relation_type_definition",
            id=uid(),
            schema_version="1.0.0",
            revision=1,
            predicate="supports",
            type_version="1.0.0",
            symmetric=False,
            source_node_types=["note"],
            target_node_types=["note"],
            self_links_allowed=False,
            description="Fabricated predicate",
        ),
    ]
    app.bootstrap(
        records,
        {
            "local:note:1": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
                "additionalProperties": False,
            }
        },
    )
    return app, cluster
