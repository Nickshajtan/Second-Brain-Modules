"""Platform lock strategies for cooperating writers in one Git repository."""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


class WindowsFileLock:
    def acquire(self, stream: BinaryIO) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows lock requested on another platform")
        import msvcrt

        stream.seek(0)
        if not stream.read(1):
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)

    def release(self, stream: BinaryIO) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows lock requested on another platform")
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class PosixFileLock:
    def acquire(self, stream: BinaryIO) -> None:
        if sys.platform == "win32":
            raise RuntimeError("POSIX lock requested on Windows")
        import fcntl

        fcntl.flock(stream, fcntl.LOCK_EX)

    def release(self, stream: BinaryIO) -> None:
        if sys.platform == "win32":
            raise RuntimeError("POSIX lock requested on Windows")
        import fcntl

        fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def writer_lock(path: Path) -> Iterator[None]:
    """OS releases the lock on process death; never delete the shared lock file."""
    strategy = {"nt": WindowsFileLock, "posix": PosixFileLock}[os.name]()
    with path.open("a+b") as stream:
        strategy.acquire(stream)
        try:
            yield
        finally:
            strategy.release(stream)
