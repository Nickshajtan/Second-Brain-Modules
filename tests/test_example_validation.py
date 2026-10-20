import hashlib
import json
import socket
import subprocess
import sys
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError, ValidationError

from tools.example_validation import ExampleValidator, load

ROOT = Path(__file__).resolve().parents[1]


def example(root, name):
    return root / "docs/architecture/examples" / name


def change(root, filename, mutate):
    path = example(root, filename)
    obj = load(path)
    mutate(obj)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_report_deterministic_immutable_and_no_mutation(repository, capsys):
    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in repository.rglob("*") if p.is_file()
    }
    validator = ExampleValidator(repository)
    report = validator.run()
    assert report == validator.run()
    assert asdict(report) == dict(
        schemas=2,
        schema_refs=20,
        fixtures=4,
        rejection_probes=11,
        valid_probes=3,
        openapi_refs=2,
        document_links=validator.check_document_links(),
    )
    assert report.summary().startswith("PASS: 2 schemas")
    with pytest.raises(FrozenInstanceError):
        report.schemas = 10
    assert not capsys.readouterr().out
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}


def test_valid_schemas_and_offline_resolution(repository, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Network access attempted")

    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    validator = ExampleValidator(repository)
    assert validator.check_schemas() == 20
    assert validator.check_openapi() == 2


def test_invalid_schema(repository):
    change(repository, "node.schema.json", lambda x: x.update(type="invalid-type"))
    with pytest.raises(SchemaError):
        ExampleValidator(repository)


def test_missing_schema(repository):
    example(repository, "node.schema.json").unlink()
    with pytest.raises(AssertionError, match="expected node and cluster"):
        ExampleValidator(repository)


@pytest.mark.parametrize(
    "ref",
    [
        "missing.schema.json",
        "https://untrusted.invalid/schema.json",
        "file:///etc/passwd",
        "../../../../secret.json",
        "%2e%2e/%2e%2e/%2e%2e/%2e%2e/secret.json",
        "..\\..\\secret.json",
        "/secret.json",
        "//untrusted.invalid/schema.json",
        "node.schema.json#/missing",
        "node.schema.json?query=1",
    ],
)
def test_rejects_unresolved_or_unsafe_reference(repository, ref, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Network retrieval attempted")

    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    change(repository, "cluster.schema.json", lambda x: x["properties"]["id"].update({"$ref": ref}))
    with pytest.raises(Exception) as error:
        ExampleValidator(repository).check_schemas()
    assert "Network" not in str(error.value)


def test_unknown_format(repository):
    change(
        repository,
        "node.schema.json",
        lambda x: x["properties"]["title"].update(format="executable-python"),
    )
    with pytest.raises(AssertionError, match="Missing format checker"):
        ExampleValidator(repository).check_schemas()


def test_valid_fixture_acceptance(repository):
    assert ExampleValidator(repository).check_fixtures() == 4


def test_invalid_valid_fixture_rejected(repository):
    change(repository, "fixtures/valid/node.json", lambda x: x.update(title=None))
    with pytest.raises(ValidationError, match="None"):
        ExampleValidator(repository).check_fixtures()


def test_invalid_fixture_expected_reason(repository):
    change(repository, "fixtures/invalid/node.json", lambda x: x.update(title="valid", revision=0))
    with pytest.raises(AssertionError, match="wrong reason"):
        ExampleValidator(repository).check_fixtures()


def test_invalid_fixture_unexpected_acceptance(repository):
    change(repository, "fixtures/invalid/node.json", lambda x: x.update(title="valid"))
    with pytest.raises(AssertionError, match="wrong reason"):
        ExampleValidator(repository).check_fixtures()


@pytest.mark.parametrize(
    "text,diagnostic",
    [
        ("{", "Expecting property name"),
        ('{"a":1,"a":2}', "Duplicate JSON key"),
        ('{"a":NaN}', "Non-JSON numeric constant"),
    ],
)
def test_bad_json_reports_filename(repository, text, diagnostic):
    path = example(repository, "fixtures/valid/node.json")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=diagnostic) as error:
        ExampleValidator(repository).check_fixtures()
    assert str(path) in str(error.value)


def test_semantically_invalid_openapi(repository):
    change(repository, "openapi-example.yaml", lambda x: x["info"].pop("title"))
    with pytest.raises(Exception, match="title"):
        ExampleValidator(repository).check_openapi()


@pytest.mark.parametrize("ref", ["https://untrusted.invalid/schema", "../../../../outside"])
def test_openapi_references_restricted(repository, ref):
    def mutate(api):
        api["paths"]["/v1/nodes/{node_id}"]["get"]["parameters"][0]["schema"]["$ref"] = ref

    change(repository, "openapi-example.yaml", mutate)
    with pytest.raises((ValueError, AssertionError)):
        ExampleValidator(repository).check_openapi()


@pytest.mark.parametrize("link", ["../../outside.md", "missing.md"])
def test_document_links_restricted(repository, link):
    (repository / "README.md").write_text(f"[bad]({link})", encoding="utf-8")
    with pytest.raises(AssertionError):
        ExampleValidator(repository).check_document_links()


def test_local_links_resolve_relative_to_document(repository):
    (repository / "README.md").write_text(
        "[docs](docs/architecture/contracts-spec.md)", encoding="utf-8"
    )
    assert ExampleValidator(repository).check_document_links() > 0


def test_cli_from_other_cwd_and_root_with_spaces(repository, tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_examples.py"), "--root", str(repository)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: 2 schemas" in result.stdout


def test_cli_failure_diagnostic_and_exit_code(repository, tmp_path):
    example(repository, "fixtures/valid/node.json").write_text("{", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_examples.py"), "--root", str(repository)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1
    assert "FAIL" in result.stderr and "node.json" in result.stderr
    assert "PASS" not in result.stdout


def test_instances_do_not_share_roots(repository):
    first = ExampleValidator(ROOT)
    second = ExampleValidator(repository)
    assert first.root != second.root
    assert first.check_fixtures() == second.check_fixtures() == 4


@pytest.mark.parametrize(
    "link",
    ["file:///private/file.md", "C:\\private\\file.md", "docs/architecture/CONTRACTS-SPEC.md"],
)
def test_nonportable_link_scheme_or_case(repository, link):
    (repository / "README.md").write_text(f"[bad]({link})", encoding="utf-8")
    with pytest.raises(AssertionError):
        ExampleValidator(repository).check_document_links()
