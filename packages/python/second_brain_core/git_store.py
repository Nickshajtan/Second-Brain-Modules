"""Git plumbing boundary: isolated index, unpublished objects, one CAS publication."""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from .locking import writer_lock


class StorageError(RuntimeError):
    pass


class PublicationConflict(StorageError):
    pass


class GitStore:
    def __init__(self, repository, ref):
        self.repository = Path(repository).resolve()
        if not ref.startswith("refs/heads/"):
            raise ValueError("Managed ref must be a fully qualified branch ref")
        self.ref = ref
        self.run("check-ref-format", ref)
        self.common = Path(
            self.run("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        )

    def run(self, *args, data=None, env=None):
        """Run a textual plumbing command; blob reads use the binary boundary."""
        return self._run_bytes(*args, data=data, env=env).decode("utf-8")

    @staticmethod
    def _environment(overrides):
        # Ignore inherited Git overrides, including a caller's index/worktree.
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        clean.update(overrides or {})
        return clean

    def _run_bytes(self, *args, data=None, env=None):
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(self.repository), *args],
            input=data,
            capture_output=True,
            env=self._environment(env),
        )
        if result.returncode:
            raise StorageError("Git operation failed: " + args[0])
        return result.stdout

    def writer(self):
        return writer_lock(self.common / "second-brain-writer.lock")

    def resolve(self):
        # Only absent refs are initialization, never a broken existing ref.
        refs = self.run("for-each-ref", "--format=%(refname)", self.ref).splitlines()
        if self.ref not in refs:
            return None
        return self.run("rev-parse", "--verify", self.ref + "^{commit}").strip()

    def read(self, commit):
        files = {}
        for row in self.run("ls-tree", "-rz", "--full-tree", commit).split("\0"):
            if not row:
                continue
            header, name = row.split("\t", 1)
            mode, kind, oid = header.split()
            if mode != "100644" or kind != "blob":
                raise StorageError("Unsupported canonical tree entry")
            files[name] = self._run_bytes("cat-file", "blob", oid)
        return files

    def prepare(self, files, parent):
        tree = self._write_tree(files)
        return self._write_commit(tree, parent)

    def _write_tree(self, files):
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

    def _write_commit(self, tree, parent):
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

    def publish(self, candidate, expected):
        # Empty expected value means the ref must not exist (works with SHA-256 repos).
        try:
            self.run("update-ref", self.ref, candidate, expected or "")
        except StorageError as exc:
            if self.resolve() != expected:
                raise PublicationConflict("Managed generation changed") from exc
            raise
