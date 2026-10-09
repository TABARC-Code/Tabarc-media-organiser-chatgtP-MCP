"""Prevent two local servers from reconciling the same catalogue at once."""

import os
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows packaging needs a separate locking adapter.
    fcntl = None


class CatalogueLock:
    def __init__(self, directory: Path):
        if fcntl is None:
            raise RuntimeError("This alpha currently requires POSIX file locking (Linux).")
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / ".catalogue.lock"
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self.fd = os.open(path, flags, 0o600)
        try:
            os.fchmod(self.fd, 0o600)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            self.fd = -1
            raise RuntimeError(
                "Another TABARC server is already using this catalogue directory."
            ) from exc
        except BaseException:
            os.close(self.fd)
            self.fd = -1
            raise

    def close(self):
        if self.fd >= 0:
            fd, self.fd = self.fd, -1
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
