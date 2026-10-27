"""Narrow committed-storage interface; application code has no Git command port."""

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

type Files = dict[str, bytes]


class CommitStore(Protocol):
    repository: Path
    ref: str

    def writer(self) -> AbstractContextManager[None]: ...

    def resolve(self) -> str | None: ...

    def read(self, commit: str) -> Files: ...

    def ancestry(self, commit: str) -> list[str]: ...

    def prepare(self, files: Files, parent: str | None) -> str: ...

    def publish(self, candidate: str, expected: str | None) -> None: ...

    common: Path

    def blobs(self, oids: list[str]) -> dict[str, bytes]: ...

    def entries(self, commit: str) -> dict[str, str]: ...

    def locate(self, commit: str, path: str) -> str: ...

    def require_complete(self) -> None: ...

    def changes(
        self, start: str | None, end: str
    ) -> list[tuple[str, str | None, dict[str, str | None]]]: ...

    def prepare_delta(self, files: Files, parent: str) -> str: ...
