import shutil
from pathlib import Path

import pytest

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
    return root
