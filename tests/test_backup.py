import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tabarc_media.app import create_app
from tabarc_media.backup import backup_catalogue
from tabarc_media.catalogue import Catalogue


def test_backup_is_consistent_without_touching_media(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    film = root / "Film.mkv"
    film.write_bytes(b"existing media")
    state = tmp_path / "state"
    store = Catalogue(state)
    lib = store.add_library("Films", root, ["films"], [])
    store.upsert_batch(lib, [("Film.mkv", "film", 14, 123, 10.0)])
    target = tmp_path / "catalogue-backup.sqlite3"

    backup_catalogue(state, target)
    assert target.is_file()
    assert os.stat(target).st_mode & 0o077 == 0
    with sqlite3.connect(target) as snapshot:
        assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert snapshot.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 1
        assert snapshot.execute("SELECT root FROM libraries").fetchone()[0] == str(root)
    assert film.read_bytes() == b"existing media"
    assert sorted(p.name for p in root.iterdir()) == ["Film.mkv"]
    with pytest.raises(FileExistsError):
        backup_catalogue(state, target)


def test_backup_rejects_media_folders_and_active_server(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    state = tmp_path / "state"
    store = Catalogue(state)
    store.add_library("Films", root, ["films"], [])
    with pytest.raises(ValueError, match="inside a media root"):
        backup_catalogue(state, root / "backup.sqlite3")
    with pytest.raises(ValueError, match="absolute"):
        backup_catalogue(state, Path("relative.sqlite3"))

    with (
        TestClient(create_app(state), base_url="http://localhost"),
        pytest.raises(RuntimeError, match="already using"),
    ):
        backup_catalogue(state, tmp_path / "busy.sqlite3")
    assert not (tmp_path / "busy.sqlite3").exists()
    backup_catalogue(state, tmp_path / "after-close.sqlite3")
    assert (tmp_path / "after-close.sqlite3").is_file()


def test_backup_rejects_absent_catalogue(tmp_path):
    with pytest.raises(ValueError, match="no existing catalogue"):
        backup_catalogue(tmp_path / "missing", tmp_path / "new.sqlite3")
