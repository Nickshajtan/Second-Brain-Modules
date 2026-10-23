"""Build boundary checks and isolated consumers; no manual testing required."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import build_contracts as builder
from tools.generate_contracts import OUTPUTS, files

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundles(tmp_path_factory):
    parent = tmp_path_factory.mktemp("distribution")
    first, second = parent / "first", parent / "second"
    builder.build(first)
    builder.build(second, from_source=True)
    return first, second


def test_reproducible_bundle_inventory(bundles):
    first, second = bundles
    assert builder.payload_files(first) == builder.payload_files(second)
    assert (first / "distribution.json").read_bytes() == (second / "distribution.json").read_bytes()
    manifest = builder.verify_distribution(first)
    assert len(list((first / "contracts/schemas/v1").glob("*.schema.json"))) == 8
    assert all((first / name).is_file() for name in builder.RUNTIME_FILES)
    assert not (first / "tools").exists()
    assert not (first / "packages/python/generated/source-hashes.json").exists()
    assert set(manifest["runtime_dependencies"]["node"]) == {"ajv", "ajv-formats"}


@pytest.mark.parametrize("mutation", ["missing", "stale", "unexpected"])
def test_build_rejects_tracked_output_drift(tmp_path, monkeypatch, mutation):
    source = tmp_path / "source"
    for directory in OUTPUTS:
        shutil.copytree(
            ROOT / directory, source / directory, ignore=shutil.ignore_patterns("__pycache__")
        )
    expected = files(ROOT)

    def generate(destination, **kwargs):
        for name, content in expected.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    monkeypatch.setattr(builder, "generate", generate)
    target = source / next(iter(expected))
    if mutation == "missing":
        target.unlink()
    elif mutation == "stale":
        target.write_bytes(b"stale")
    else:
        (source / OUTPUTS[0] / "unexpected.py").write_text("unexpected")
    with pytest.raises(ValueError, match="Generated artifact drift"):
        builder.build(tmp_path / "output", source_root=source)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "mutation", ["missing", "stale", "unexpected", "nested_manifest", "nested_dependencies"]
)
def test_distribution_integrity(bundles, tmp_path, mutation):
    root = tmp_path / "bundle"
    shutil.copytree(bundles[0], root)
    target = root / "LICENSE"
    if mutation == "missing":
        target.unlink()
    elif mutation == "stale":
        target.write_bytes(b"stale")
    else:
        name = {
            "nested_manifest": "contracts/distribution.json",
            "nested_dependencies": "contracts/node_modules/extra",
        }.get(mutation, "extra")
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("unexpected")
    with pytest.raises(ValueError, match="Distribution"):
        builder.verify_distribution(root)


def test_existing_destination_is_preserved(tmp_path):
    marker = tmp_path / "keep"
    marker.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        builder.build(tmp_path)
    assert marker.read_text() == "keep"


def test_consumers_outside_checkout(bundles, tmp_path):
    bundle = bundles[0]
    cases = json.loads((ROOT / "tests/fixtures/contracts/v1.json").read_text(encoding="utf-8"))
    data = tmp_path / "cases.json"
    data.write_text(json.dumps(cases), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "NODE_PATH"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    python = """
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / 'packages/python'))
from second_brain_contracts import ContractValidator, decode_json, encode_json
validator = ContractValidator()
validator.verify_generated()
assert decode_json(encode_json({'unicode': 'Знання', 'omitted': None})) == {'unicode': 'Знання', 'omitted': None}
try:
    decode_json('{"duplicate": 1, "duplicate": 2}')
except ValueError:
    pass
else:
    raise AssertionError('Public strict decoder accepted duplicate keys')
for case in json.loads(pathlib.Path(sys.argv[2]).read_text()):
    valid = validator.validators[case['schema']].is_valid(case['instance'])
    assert valid == case['valid'], case['name']
    if valid:
        model = validator.parse(case['schema'], case['instance'])
        assert validator.dump(case['schema'], model) == case['instance']
        if case['schema'] == 'knowledge':
            assert validator.parse_as('knowledge', case['instance'], type(model.root)) == model.root
assert not any(n.startswith(('tools', 'datamodel_code_generator')) for n in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-I", "-c", python, str(bundle), str(data)],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    # Provision only the declared Node runtime dependency closure from the installed lock.
    installed = set()

    def provision(name):
        if name in installed:
            return
        installed.add(name)
        source = ROOT / "node_modules" / name
        shutil.copytree(source, bundle / "node_modules" / name, dirs_exist_ok=True)
        for dependency in json.loads((source / "package.json").read_text()).get("dependencies", {}):
            provision(dependency)

    for name in builder.verify_distribution(bundle)["runtime_dependencies"]["node"]:
        provision(name)
    assert "json-schema-to-typescript" not in installed
    script = tmp_path / "consumer.mjs"
    script.write_text(
        f"import {{loadContracts}} from {json.dumps((bundle / 'packages/typescript/validation.mjs').as_uri())};\n"
        "import {readFile} from 'node:fs/promises';\n"
        "const contracts = await loadContracts(process.argv[2]);\n"
        "for (const c of JSON.parse(await readFile(process.argv[3], 'utf8'))) {\n"
        "let valid = true; try {contracts.validate(c.schema, c.instance);} catch {valid = false;}\n"
        "if (valid !== c.valid) throw Error(c.name); }\n",
        encoding="utf-8",
    )
    subprocess.run(
        [shutil.which("node"), str(script), str(bundle), str(data)],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    builder.verify_distribution(bundle)


def test_generator_cli_from_unrelated_directory(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/generate_contracts.py"),
            "--check",
            "--output-root",
            str(ROOT),
        ],
        cwd=tmp_path,
        check=True,
    )


def test_source_only_checkout_build(tmp_path):
    source = tmp_path / "checkout"
    for directory in ("contracts", "tools", "docs/architecture/examples", "node_modules"):
        shutil.copytree(
            ROOT / directory, source / directory, ignore=shutil.ignore_patterns("__pycache__")
        )
    for name in (
        *builder.RUNTIME_FILES,
        "requirements-dev.lock",
        "package-lock.json",
        "package.json",
        "pyproject.toml",
        "LICENSE",
    ):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    output = tmp_path / "distribution"
    subprocess.run(
        [
            sys.executable,
            str(source / "tools/build_contracts.py"),
            "--from-source",
            "--output",
            str(output),
        ],
        cwd=tmp_path,
        check=True,
    )
    builder.verify_distribution(output)
    assert not any((source / directory).exists() for directory in OUTPUTS)
