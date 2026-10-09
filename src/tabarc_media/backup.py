"""Create consistent, private SQLite catalogue snapshots while the service is offline."""

import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote

from .instance_lock import CatalogueLock


def backup_catalogue(data_dir: Path, destination: Path) -> Path:
    """Backup a catalogue without touching media or replacing existing files."""
    state = Path(data_dir).expanduser().resolve()
    database = state / "catalogue.sqlite3"
    if not database.is_file():
        raise ValueError("There is no existing catalogue in this state directory.")

    requested = Path(destination).expanduser()
    if not requested.is_absolute():
        raise ValueError("Choose an absolute path for the backup.")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("The backup parent is not a directory.")
    output = parent / requested.name
    if output.exists() or output.is_symlink():
        raise FileExistsError("A backup already exists at that path.")
    if output == database or output.parent == state and output.name == database.name:
        raise ValueError("The live catalogue cannot be overwritten by a backup.")

    lock = CatalogueLock(state)
    temporary = None
    try:
        # Open the catalogue read-only, and inspect its registered media roots.
        # Backups contain full paths and private collection information, so
        # they must never be saved inside a scanned library by accident.
        source_uri = "file:" + quote(str(database), safe="/") + "?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source:
            roots = [Path(row[0]) for row in source.execute("SELECT root FROM libraries")]
            for root in roots:
                if output.is_relative_to(root):
                    raise ValueError("A catalogue backup cannot be saved inside a media root.")

            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".tabarc-backup-", suffix=".sqlite3",
                dir=parent, delete=False
            ) as staging:
                temporary = Path(staging.name)
            os.chmod(temporary, 0o600)
            try:
                with sqlite3.connect(temporary) as snapshot:
                    source.backup(snapshot, pages=64, sleep=0.03)
                    integrity = snapshot.execute("PRAGMA integrity_check").fetchone()[0]
                    if integrity != "ok":
                        raise RuntimeError("Catalogue backup failed its integrity check.")
                # Hard-link publication is atomic and refuses to overwrite an
                # existing destination, including one created during the copy.
                os.link(temporary, output)
                with output.open("rb") as saved:
                    os.fsync(saved.fileno())
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return output
    finally:
        lock.close()
