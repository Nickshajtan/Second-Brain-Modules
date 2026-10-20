"""Orchestrate mature generators; --check compares the exact generated file set."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.example_validation import ExampleValidator

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("packages/python/generated", "packages/typescript/generated")


def generate(destination: Path) -> None:
    ExampleValidator(ROOT).check_schemas()
    python_out, typescript_out = (destination / p for p in OUTPUTS)
    python_out.mkdir(parents=True)
    for name in ("node", "cluster"):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                f"docs/architecture/examples/{name}.schema.json",
                "--input-file-type",
                "jsonschema",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.12",
                "--use-union-operator",
                "--strict-nullable",
                "--disable-timestamp",
                "--formatters",
                "black",
                "isort",
                "--output",
                str(python_out / f"{name}.py"),
            ],
            cwd=ROOT,
            check=True,
        )
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node is required; install the locked npm development dependencies")
    subprocess.run(
        [node, str(ROOT / "tools/generate_typescript.mjs"), str(typescript_out)],
        cwd=ROOT,
        check=True,
    )
    for directory in (python_out, typescript_out):
        for output in directory.iterdir():
            output.write_bytes(output.read_bytes().replace(b"\r\n", b"\n"))
    inputs = [
        ROOT / "requirements-dev.lock",
        ROOT / "package-lock.json",
        ROOT / "package.json",
        ROOT / "pyproject.toml",
        ROOT / "tools/generate_contracts.py",
        ROOT / "tools/generate_typescript.mjs",
    ]
    inputs += sorted((ROOT / "docs/architecture/examples").glob("*.schema.json"))
    manifest = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
    }
    (python_out / "source-hashes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for directory in OUTPUTS
        for p in (root / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="second-brain-generation-") as temp:
        staging = Path(temp)
        generate(staging)
        expected = files(staging)
        current = files(ROOT)
        changed = sorted(
            k for k in expected.keys() | current.keys() if expected.get(k) != current.get(k)
        )
        if args.check:
            if changed:
                raise SystemExit("Generated artifact drift: " + ", ".join(changed))
            print(f"PASS: {len(expected)} generated artifacts match, no extra files")
            return
        extras = current.keys() - expected.keys()
        if extras:
            raise SystemExit("Remove obsolete generated files explicitly: " + ", ".join(extras))
        for relative, content in expected.items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        print(f"Generated {len(expected)} illustrative artifacts")


if __name__ == "__main__":
    main()
