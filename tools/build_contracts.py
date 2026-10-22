"""Build/verify a relocatable contract bundle; no installer or publishing infrastructure."""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages/python"))

from second_brain_contracts import ContractValidator  # noqa: E402
from second_brain_contracts.validation import load_json  # noqa: E402

from tools.generate_contracts import OUTPUTS, files, generate  # noqa: E402

RUNTIME_FILES = (
    "packages/python/second_brain_contracts/__init__.py",
    "packages/python/second_brain_contracts/validation.py",
    "packages/typescript/validation.mjs",
    "packages/typescript/validation.d.mts",
)
PRODUCTION_OUTPUTS = tuple(path + "/v1" for path in OUTPUTS)


def payload_files(root):
    """First-party payload only; installed dependencies/bytecode are environment state."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.relative_to(root).parts
        and p.relative_to(root).parts[0] != "node_modules"
        and p.relative_to(root).as_posix() != "distribution.json"
    }


def verify_distribution(root):
    """Verify a built bundle without generators, tools, fixtures or source checkout."""
    root = Path(root).resolve()
    manifest = load_json(root / "distribution.json")
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported distribution manifest format")
    actual = payload_files(root)
    expected = manifest["file_hashes"]
    if actual.keys() != expected.keys():
        raise ValueError("Distribution file set mismatch (missing or unexpected file)")
    for name, content in actual.items():
        if hashlib.sha256(content).hexdigest() != expected[name]:
            raise ValueError(f"Distribution content drift: {name}")
    validator = ContractValidator(root, version=manifest["contract_version"])
    validator.verify_generated()
    return manifest


def build(destination, *, source_root=ROOT, from_source=False):
    """Reuse the generator once, then assemble and verify only production runtime files.

    Default mode requires checked-in generated artifacts to match fresh output.
    Explicit from_source mode ignores them, preparing for source-only Git later.
    Neither mode mutates or removes checked-in generated files.
    """
    source = Path(source_root).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Build destination already exists; choose a fresh directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="contract-build-", dir=destination.parent) as temp:
        staging = Path(temp)
        generated = staging / "generated"
        generate(generated, source_root=source)
        if not from_source:
            expected, current = files(generated), files(source)
            changed = sorted(
                k for k in expected.keys() | current.keys() if expected.get(k) != current.get(k)
            )
            if changed:
                raise ValueError("Generated artifact drift: " + ", ".join(changed))
        bundle = staging / "bundle"
        bundle.mkdir()
        registry = load_json(source / "contracts/registry/v1.json")
        for entry in registry["schemas"]:
            path = entry["path"]
            target = bundle / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / path, target)
        for path in ("contracts/registry/v1.json", "LICENSE", *RUNTIME_FILES):
            target = bundle / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / path, target)
        for path in PRODUCTION_OUTPUTS:
            shutil.copytree(generated / path, bundle / path)
        # Keep exact installed-toolchain lock provenance, not an undeclared developer path.
        (bundle / "build-locks").mkdir()
        for name in ("requirements-dev.lock", "package-lock.json"):
            shutil.copyfile(source / name, bundle / "build-locks" / name)
        pins = dict(
            re.findall(
                r"^([a-z0-9_-]+)==([^\s\\]+)", (source / "requirements-dev.lock").read_text(), re.M
            )
        )
        python_dependencies = {
            "jsonschema[format]": pins["jsonschema"],
            "referencing": pins["referencing"],
            "pydantic": pins["pydantic"],
        }
        (bundle / "requirements-runtime.txt").write_text(
            "".join(f"{name}=={version}\n" for name, version in python_dependencies.items()),
            encoding="utf-8",
            newline="\n",
        )
        package = load_json(source / "package.json")
        node_dependencies = {
            name: package["devDependencies"][name] for name in ("ajv", "ajv-formats")
        }
        runtime_package = {
            "name": "second-brain-contracts-bundle",
            "private": True,
            "version": registry["contract_version"],
            "type": "module",
            "engines": package["engines"],
            "dependencies": node_dependencies,
        }
        (bundle / "package.json").write_text(
            json.dumps(runtime_package, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest = {
            "format_version": 1,
            "contract_version": registry["contract_version"],
            "runtime_dependencies": {"python": python_dependencies, "node": node_dependencies},
            "file_hashes": {
                name: hashlib.sha256(content).hexdigest()
                for name, content in sorted(payload_files(bundle).items())
            },
        }
        (bundle / "distribution.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        verify_distribution(bundle)
        bundle.rename(destination)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/contracts-1.0.0")
    parser.add_argument(
        "--from-source",
        action="store_true",
        help="Build fresh without comparing tracked generated artifacts",
    )
    parser.add_argument(
        "--check",
        type=Path,
        metavar="BUNDLE",
        help="Verify existing distribution without generating or modifying it",
    )
    args = parser.parse_args()
    if args.check:
        manifest = verify_distribution(args.check)
    else:
        manifest = build(args.output, from_source=args.from_source)
    print(
        f"PASS: contract distribution {manifest['contract_version']}, "
        f"{len(manifest['file_hashes'])} payload files"
    )


if __name__ == "__main__":
    main()
