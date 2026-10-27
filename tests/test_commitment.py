"""Independent full-tree vectors and incremental SHA256 commitment properties."""

import hashlib
import random
import sqlite3
from uuid import UUID

import pytest
from second_brain_core.commitment import SCHEMA, ContentCommitment, content_digest

INSTANCE = "00000001-1111-4111-8111-000000000001"


def reference(files, instance=INSTANCE):
    """Full 65,536-leaf specification implementation, independent of production helpers."""
    identity = UUID(instance).bytes

    def encode(tag, parts):
        result = bytearray(b"second-brain.content\0sha256-bucket16-v1\0")
        result.extend(len(tag).to_bytes(2, "big"))
        result.extend(tag)
        result.extend(len(parts).to_bytes(4, "big"))
        for item in parts:
            result.extend(len(item).to_bytes(8, "big"))
            result.extend(item)
        return bytes(result)

    def hashed(tag, parts):
        return hashlib.sha256(encode(tag, parts)).digest()

    buckets = {}
    for path, raw in files.items():
        key = path.encode("utf-8")
        bucket = int.from_bytes(hashed(b"key", [identity, key])[:2], "big")
        buckets.setdefault(bucket, []).append((key, hashlib.sha256(raw).digest()))
    level = [hashed(b"empty", [identity])] * 65536
    for bucket, entries in buckets.items():
        level[bucket] = hashed(
            b"bucket",
            [
                identity,
                bucket.to_bytes(2, "big"),
                len(entries).to_bytes(4, "big"),
                b"".join(encode(b"entry", [key, value]) for key, value in sorted(entries)),
            ],
        )
    for height in range(1, 17):
        level = [
            hashed(b"branch", [identity, height.to_bytes(2, "big"), level[i], level[i + 1]])
            for i in range(0, len(level), 2)
        ]
    return dict(algorithm="sha256", value=hashed(b"root", [identity, level[0]]).hex())


def connection():
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    return db


def test_full_reference_and_incremental_branch_reuse():
    files = {f"knowledge/node/{number}.md": f"body {number}".encode() for number in range(200)}
    files["control/metadata.json"] = b"{}"
    expected = reference(files)
    assert content_digest(INSTANCE, files) == expected
    with connection() as db:
        tree = ContentCommitment(db, INSTANCE)
        changes = {path: hashlib.sha256(raw).hexdigest() for path, raw in files.items()}
        items = list(changes.items())
        random.Random(42).shuffle(items)
        for path, sha in items:
            tree.update({path: sha}, apply=True)
        assert tree.update({}) == expected
        before = dict(
            ((h, p), value) for h, p, value in db.execute("SELECT * FROM commitment_nodes")
        )
        target = "knowledge/node/3.md"
        files[target] = b"replacement"
        preview = tree.update({target: hashlib.sha256(files[target]).hexdigest()})
        assert tree.update({}) == expected  # Preview must not mutate accepted state.
        assert (
            tree.update({target: hashlib.sha256(files[target]).hexdigest()}, apply=True) == preview
        )
        assert preview == reference(files)
        after = dict(
            ((h, p), value) for h, p, value in db.execute("SELECT * FROM commitment_nodes")
        )
        bucket = tree.bucket(target)
        touched = {(height, bucket >> height) for height in range(17)}
        assert all(after[key] == value for key, value in before.items() if key not in touched)


def test_empty_absent_delete_instance_and_determinism():
    empty = reference({})
    assert empty["value"] == "2ce5b19fba2f6a9e704881a6d742c210ac02ac56b10cc14a1c1716c907b62707"
    vector = {"knowledge/node/a.md": b"", "control/metadata.json": b"{}"}
    assert (
        reference(vector)["value"]
        == "2b9c717159484a29f6e299e2b0eaf1d09e77a93314639e714087fc03204fd885"
    )
    assert content_digest(INSTANCE, vector) == reference(vector)
    assert content_digest(INSTANCE, {}) == empty
    with connection() as db:
        tree = ContentCommitment(db, INSTANCE)
        path = "knowledge/node/empty.md"
        assert tree.update({path: hashlib.sha256(b"").hexdigest()}, apply=True) != empty
        assert tree.update({path: None}, apply=True) == empty
        assert list(db.execute("SELECT * FROM commitment_nodes")) == []
        assert tree.update({}) != ContentCommitment(db, str(UUID(int=2, version=4))).update({})
        with pytest.raises(ValueError):
            tree.update({path: "not-a-hash"})


def test_complete_collision_bucket_and_omitted_absence_witness():
    with connection() as db:
        tree = ContentCommitment(db, INSTANCE)
        # Deliberately find a collision in the public 16-bit routing prefix.
        seen = {}
        for number in range(10000):
            path = f"knowledge/node/{number}.md"
            bucket = tree.bucket(path)
            if bucket in seen:
                paths = [seen[bucket], path]
                break
            seen[bucket] = path
        else:
            pytest.fail("deterministic collision corpus unexpectedly has no collision")
        values = {path: b"" for path in paths}
        accepted = reference(values)
        assert (
            tree.update({path: hashlib.sha256(b"").hexdigest() for path in paths}, apply=True)
            == accepted
        )
        # A purported complete-set/absence witness omitting a colliding path fails.
        assert reference({paths[0]: b""}) != accepted
        assert reference({paths[0]: b"", paths[1]: b"tampered"}) != accepted
        row = db.execute("SELECT hash FROM commitment_nodes WHERE height=1 LIMIT 1").fetchone()
        assert row
        # A modified sibling branch cannot reproduce the trusted root.
        target = tree.bucket(paths[0]) >> 1
        sibling = target ^ 1
        db.execute("INSERT OR REPLACE INTO commitment_nodes VALUES(1,?,?)", (sibling, "00" * 32))
        assert tree.update({paths[0]: hashlib.sha256(b"").hexdigest()}) != accepted


def test_duplicate_key_input_rejected():
    class Duplicate(dict):
        def items(self):
            return [("knowledge/node/a.md", "00" * 32)] * 2

    with connection() as db, pytest.raises(ValueError, match="Duplicate"):
        ContentCommitment(db, INSTANCE).update(Duplicate())
