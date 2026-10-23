"""Shared local/CI checks: quality (default), contracts, core, or full."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def commands(mode: str) -> list[list[str]]:
    """Use existing tool CLIs directly; no shell, downloads or implicit fixes."""
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Install Node and locked npm dependencies first")
    python = sys.executable
    quality = [
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [node, "node_modules/pyright/index.js", "--pythonpath", python],
        [node, "node_modules/eslint/bin/eslint.js", "."],
        [node, "node_modules/typescript/bin/tsc", "-p", "packages/typescript/tsconfig.json"],
        [
            python,
            "-m",
            "compileall",
            "-q",
            "tools",
            "tests",
            "packages/python/second_brain_core",
            "packages/python/second_brain_contracts",
            "packages/python/generated",
        ],
    ]
    contracts = [
        [python, "-m", "tools.validate_examples"],
        [python, "-m", "tools.validate_contracts"],
        [python, "-m", "tools.generate_contracts", "--check"],
        [node, "tools/validate_typescript.mjs"],
    ]
    core = [
        [python, "-m", "pytest", "-q", "tests/test_core_m1.py", "tests/test_quality_boundaries.py"]
    ]
    return {
        "quality": quality,
        "contracts": contracts,
        "core": core,
        "full": quality + contracts + [[python, "-m", "pytest", "-q"]],
    }[mode]


def run(command: list[str]) -> None:
    print("CHECK:", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("quality", "contracts", "core", "full"), nargs="?", default="quality"
    )
    args = parser.parse_args()
    try:
        for command in commands(args.mode):
            run(command)
        if args.mode == "full":
            # Each verification owns a fresh destination; never remove/overwrite
            # a developer's existing dist bundle to make repeat checks pass.
            cache = ROOT / ".cache"
            cache.mkdir(exist_ok=True)
            with TemporaryDirectory(prefix="quality-bundle-", dir=cache) as temp:
                bundle = str(Path(temp) / "contracts")
                run([sys.executable, "-m", "tools.build_contracts", "--output", bundle])
                run([sys.executable, "-m", "tools.build_contracts", "--check", bundle])
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
