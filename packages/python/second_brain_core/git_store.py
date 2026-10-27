"""Git plumbing boundary: isolated index, unpublished objects, one CAS publication."""

import hashlib
import os
import subprocess
from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from tempfile import TemporaryDirectory

from .locking import writer_lock
from .ports import CommitStore, Files


class StorageError(RuntimeError):
    pass


class PublicationConflict(StorageError):
    pass


class GitStore(CommitStore):
    def __init__(self, repository: str | Path, ref: str) -> None:
        self.repository = Path(repository).resolve()
        if not ref.startswith("refs/heads/"):
            raise ValueError("Managed ref must be a fully qualified branch ref")
        self.ref = ref
        self.run("check-ref-format", ref)
        self.common = Path(
            self.run("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        )
        self.object_format = self.run("rev-parse", "--show-object-format").strip()

    def run(
        self, *args: str, data: bytes | None = None, env: Mapping[str, str] | None = None
    ) -> str:
        """Run a textual plumbing command; blob reads use the binary boundary."""
        return self._run_bytes(*args, data=data, env=env).decode("utf-8")

    @staticmethod
    def _environment(overrides: Mapping[str, str] | None) -> dict[str, str]:
        # Ignore inherited Git overrides, including a caller's index/worktree.
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_GRAFT_FILE": os.devnull,
            }
        )
        clean.update(overrides or {})
        return clean

    def _run_bytes(
        self, *args: str, data: bytes | None = None, env: Mapping[str, str] | None = None
    ) -> bytes:
        try:
            result = subprocess.run(
                ["git", "--no-replace-objects", "-C", str(self.repository), *args],
                input=data,
                capture_output=True,
                env=self._environment(env),
            )
        except OSError as exc:
            raise StorageError("Git process unavailable") from exc
        if result.returncode:
            if args[0] in {"rev-list", "diff-tree", "cat-file", "ls-tree"} or (
                args[0] == "rev-parse" and "--verify" in args
            ):
                raise StorageError("MISSING_ANCESTOR")
            raise StorageError("Git operation failed: " + args[0])
        return result.stdout

    def writer(self) -> AbstractContextManager[None]:
        return writer_lock(self.common / "second-brain-writer.lock")

    def resolve(self) -> str | None:
        # Only absent refs are initialization, never a broken existing ref.
        for entry in self.run(
            "for-each-ref", "--format=%(refname) %(symref)", self.ref
        ).splitlines():
            name, target = entry.split(" ", 1)
            if name != self.ref:
                continue
            if target:
                raise StorageError("Managed ref must not be symbolic")
            return self.run("rev-parse", "--verify", self.ref + "^{commit}").strip()
        return None

    def read(self, commit: str) -> Files:
        entries = self.entries(commit)
        blobs = self.blobs(list(set(entries.values())))
        return {path: blobs[oid] for path, oid in entries.items()}

    def entries(self, commit: str) -> dict[str, str]:
        files = {}
        for row in self.run("ls-tree", "-rz", "--full-tree", commit).split("\0"):
            if not row:
                continue
            header, name = row.split("\t", 1)
            mode, kind, oid = header.split()
            if mode != "100644" or kind != "blob":
                raise StorageError("Unsupported canonical tree entry")
            files[name] = oid
        return files

    def locate(self, commit: str, path: str) -> str:
        if (
            not commit
            or any(c not in "0123456789abcdef" for c in commit)
            or path.startswith("/")
            or ".." in path.split("/")
        ):
            raise StorageError("Invalid canonical locator")
        return self.run("rev-parse", "--verify", f"{commit}:{path}").strip()

    def blobs(self, oids: list[str]) -> dict[str, bytes]:
        if not oids:
            return {}
        if any(not oid or any(c not in "0123456789abcdef" for c in oid) for oid in oids):
            raise StorageError("Invalid object locator")
        raw = self._run_bytes("cat-file", "--batch", data=("\n".join(oids) + "\n").encode())
        position, result = 0, {}
        for oid in oids:
            end = raw.find(b"\n", position)
            header = raw[position:end].split()
            if len(header) != 3 or header[0].decode() != oid or header[1] != b"blob":
                raise StorageError("Missing canonical blob")
            size = int(header[2])
            body = raw[end + 1 : end + 1 + size]
            if len(body) != size or raw[end + 1 + size : end + 2 + size] != b"\n":
                raise StorageError("Invalid canonical blob")
            actual = hashlib.new(self.object_format, f"blob {size}\0".encode() + body).hexdigest()
            if actual != oid:
                raise StorageError("Canonical blob identity mismatch")
            result[oid] = body
            position = end + size + 2
        if position != len(raw):
            raise StorageError("Invalid batch blob response")
        return result

    def changes(
        self, start: str | None, end: str
    ) -> list[tuple[str, str | None, dict[str, str | None]]]:
        self.require_complete()
        rows = self.run(
            "rev-list", "--parents", "--reverse", f"{start}..{end}" if start else end
        ).splitlines()
        commits, previous = [], start
        for row in rows:
            parts = row.split()
            if len(parts) > 2:
                raise StorageError("NONLINEAR_HISTORY")
            parent = parts[1] if len(parts) == 2 else None
            if parent != previous:
                raise StorageError("MISSING_ANCESTOR")
            commits.append((parts[0], parent, {}))
            previous = parts[0]
        if previous != end:
            raise StorageError("MISSING_ANCESTOR")
        raw = (
            self.run(
                "diff-tree",
                "--stdin",
                "--root",
                "-r",
                "-z",
                "--no-renames",
                data=("\n".join(c[0] for c in commits) + "\n").encode(),
            )
            if commits
            else ""
        )
        changes = {oid: delta for oid, _, delta in commits}
        tokens, position, current = raw.split("\0"), 0, None
        while position < len(tokens):
            token = tokens[position].strip("\n")
            position += 1
            if not token:
                continue
            if token in changes:
                current = token
                continue
            if not token.startswith(":") or current is None or position >= len(tokens):
                raise StorageError("Invalid transition response")
            modes = token[1:].split()
            path = tokens[position]
            position += 1
            if (
                len(modes) != 5
                or modes[4] not in {"A", "M", "D"}
                or modes[1] not in {"100644", "000000"}
            ):
                raise StorageError("Unsupported canonical transition")
            changes[current][path] = None if modes[4] == "D" else modes[3]
        return commits

    def prepare_delta(self, files: Files, parent: str) -> str:
        with TemporaryDirectory(prefix="second-brain-index-") as temp:
            env = {"GIT_INDEX_FILE": str(Path(temp) / "index")}
            self.run("read-tree", parent, env=env)
            entries = []
            for name, raw in sorted(files.items()):
                if name.startswith("/") or ".." in name.split("/") or "\0" in name:
                    raise StorageError("Unsafe tree path")
                oid = self.run("hash-object", "-w", "--stdin", data=raw).strip()
                entries.append(f"100644 {oid}\t{name}\0")
            self.run("update-index", "-z", "--index-info", data="".join(entries).encode(), env=env)
            tree = self.run("write-tree", env=env).strip()
        return self._write_commit(tree, parent)

    def ancestry(self, commit: str) -> list[str]:
        """Require a complete linear managed history, ignoring replacement objects."""
        self.require_complete()
        rows = self.run("rev-list", "--parents", commit).splitlines()
        if any(len(row.split()) > 2 for row in rows):
            raise StorageError("Nonlinear managed history")
        return [row.split()[0] for row in rows]

    def require_complete(self) -> None:
        grafts = self.common / "info" / "grafts"
        if grafts.exists() and grafts.read_bytes().strip():
            raise StorageError("NONLINEAR_HISTORY")
        if self.run("rev-parse", "--is-shallow-repository").strip() != "false":
            raise StorageError("MISSING_ANCESTOR")

    def prepare(self, files: Files, parent: str | None) -> str:
        tree = self._write_tree(files)
        return self._write_commit(tree, parent)

    def _write_tree(self, files: Files) -> str:
        with TemporaryDirectory(prefix="second-brain-index-") as temp:
            env = {"GIT_INDEX_FILE": str(Path(temp) / "index")}
            self.run("read-tree", "--empty", env=env)
            entries = []
            for name, raw in sorted(files.items()):
                if name.startswith("/") or ".." in name.split("/") or "\0" in name:
                    raise StorageError("Unsafe tree path")
                oid = self.run("hash-object", "-w", "--stdin", data=raw).strip()
                entries.append(f"100644 {oid}\t{name}\0")
            self.run("update-index", "-z", "--index-info", data="".join(entries).encode(), env=env)
            return self.run("write-tree", env=env).strip()

    def _write_commit(self, tree: str, parent: str | None) -> str:
        identity = {
            "GIT_AUTHOR_NAME": "Second Brain Core",
            "GIT_AUTHOR_EMAIL": "core@localhost",
            "GIT_COMMITTER_NAME": "Second Brain Core",
            "GIT_COMMITTER_EMAIL": "core@localhost",
        }
        args = ["commit-tree", tree]
        if parent:
            args += ["-p", parent]
        return self.run(*args, data=b"Second Brain committed generation\n", env=identity).strip()

    def publish(self, candidate: str, expected: str | None) -> None:
        # Empty expected value means the ref must not exist (works with SHA-256 repos).
        self.resolve()  # Reject existing aliases before attempting publication.
        try:
            # Do not follow an alias introduced after the direct-ref check.
            self.run("update-ref", "--no-deref", self.ref, candidate, expected or "")
        except StorageError as exc:
            if self.resolve() != expected:
                raise PublicationConflict("Managed generation changed") from exc
            raise
