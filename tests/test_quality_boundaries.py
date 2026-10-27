"""Focused regressions for M1.1 runtime boundaries; no private user repositories."""

import pytest
from generated.v1.common_schema import DomainError
from generated.v1.transaction_schema import CommittedReceipt
from jsonschema.exceptions import ValidationError
from second_brain_contracts import ContractValidator, decode_json, encode_json
from second_brain_core import CoreError
from second_brain_core.codec import decode, encode
from second_brain_core.git_store import StorageError
from test_core_m1 import batch, read_node


def test_symbolic_managed_ref_cannot_publish_into_another_branch(core):
    app, _ = core
    parent = app.store.resolve()
    other_ref = "refs/heads/human-owned"
    app.store.run("update-ref", other_ref, parent)
    app.store.run("symbolic-ref", app.store.ref, other_ref)
    candidate = app.store.prepare(app.store.read(parent), parent)
    with pytest.raises(StorageError):
        app.store.publish(candidate, parent)
    assert app.store.run("rev-parse", other_ref).strip() == parent


@pytest.mark.parametrize("operation", ["read", "submit", "generation"])
def test_programmer_failure_is_not_misreported_as_corrupt_state(core, monkeypatch, operation):
    app, cluster = core
    request = batch(app, cluster)
    app.submit(request)

    def broken_validator(*_):
        raise RuntimeError("private diagnostic must not enter the envelope")

    if operation == "generation":
        monkeypatch.setattr(app, "_generation", broken_validator)
        invoke = app.generation
    elif operation == "submit":
        next_request = batch(app, cluster)
        monkeypatch.setattr(app.domain, "validate", broken_validator)

        def invoke():
            return app.submit(next_request)
    else:
        monkeypatch.setattr(app.domain, "validate", broken_validator)

        def invoke():
            return read_node(app, request["operations"][0]["request_id"])

    parent = app.store.resolve()
    with pytest.raises(CoreError) as caught:
        invoke()
    assert caught.value.code == "INTERNAL"
    assert caught.value.error.message == "INTERNAL"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert app.store.resolve() == parent


def test_invalid_committed_metadata_schema_is_corruption_not_programmer_failure(core):
    app, _ = core
    parent = app.store.resolve()
    files = app.store.read(parent)
    files["control/metadata.json"] = encode({"local:note:1": {"type": "invalid-type"}})
    files["control/generation.json"] = encode(app.repository.generation(files))
    app.store.publish(app.store.prepare(files, parent), parent)
    with pytest.raises(CoreError) as caught:
        app.generation()
    assert caught.value.code == "REPAIR_REQUIRED"


def test_writer_lock_filesystem_failure_has_a_sanitized_envelope(core):
    app, cluster = core
    request = batch(app, cluster)
    parent = app.store.resolve()
    lock = app.store.common / "second-brain-writer.lock"
    lock.unlink()  # Only the disposable fixture repository's closed lock file.
    lock.mkdir()
    with pytest.raises(CoreError) as caught:
        app.submit(request)
    assert caught.value.code == "REPAIR_REQUIRED"
    assert caught.value.error.message == "REPAIR_REQUIRED"
    assert isinstance(caught.value.__cause__, OSError)
    assert app.store.resolve() == parent


@pytest.mark.parametrize(
    "raw",
    [
        '{"nested":{"duplicate":1,"duplicate":2}}',
        '{"n":NaN}',
        '{"n":Infinity}',
        '{"n":-Infinity}',
        '{"n":1e999}',
        '{"n":-1e999}',
        b'"\xff"',
    ],
)
def test_public_json_decoder_rejects_ambiguous_or_nonfinite_input(raw):
    with pytest.raises(ValueError):
        decode_json(raw)


def test_public_json_api_roundtrips_unicode_omission_null_and_arrays():
    value = {
        "title": "Знання 🧠 e\u0301",
        "body": "text\r\n",
        "nullable": None,
        "list": [True, 1.25, 9007199254740991],
    }
    encoded = encode_json(value)
    assert decode_json(encoded) == value
    assert encode_json(dict(reversed(list(value.items())))) == encoded
    assert "omitted" not in decode_json(encoded)
    assert decode_json('[1,null,"test"]') == [1, None, "test"]
    with pytest.raises(ValueError, match="Managed record"):
        decode(b'[1,null,"test"]')


@pytest.mark.parametrize("number", [float("inf"), float("-inf"), float("nan")])
def test_public_json_encoder_rejects_nonfinite_numbers(number):
    with pytest.raises(ValueError):
        encode_json({"nested": [number]})


def test_typed_parse_still_requires_canonical_validation():
    validator = ContractValidator()
    with pytest.raises(ValidationError):
        validator.parse_as("transaction", {"kind": "committed_receipt"}, CommittedReceipt)
    error = CoreError(validator, "NOT_FOUND").error
    wire = validator.dump("common", error)
    assert validator.parse_as("common", wire, DomainError) == error
    with pytest.raises(ValueError, match="Unexpected contract alternative"):
        validator.parse_as("common", wire, CommittedReceipt)
