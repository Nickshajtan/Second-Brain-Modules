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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages/python"))
from second_brain_contracts import ContractValidator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("packages/python/generated", "packages/typescript/generated")


def generate(destination: Path) -> None:
    ExampleValidator(ROOT).check_schemas()
    ContractValidator(ROOT)
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
    subprocess.run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            "contracts/schemas/v1",
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.12",
            "--use-union-operator",
            "--strict-nullable",
            "--disable-timestamp",
            "--use-title-as-name",
            "--strict-refs",
            "--type-mappings",
            "string+date-time=string",
            "--formatters",
            "black",
            "isort",
            "--output",
            str(python_out / "v1"),
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
        for output in directory.rglob("*"):
            if output.is_file():
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
    inputs += sorted((ROOT / "contracts/schemas/v1").glob("*.schema.json"))
    inputs += [ROOT / "contracts/registry/v1.json"]
    manifest = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
    }
    (python_out / "source-hashes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    artifacts = {
        p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in (python_out / "v1", typescript_out / "v1")
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }
    production_manifest = {
        "contract_version": "1.0.0",
        "source_hashes": {k: v for k, v in manifest.items() if k.startswith("contracts/")},
        "artifact_hashes": artifacts,
    }
    (python_out / "v1/manifest.json").write_text(
        json.dumps(production_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
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
        print(f"Generated {len(expected)} illustrative and production artifacts")


if __name__ == "__main__":
    main()
