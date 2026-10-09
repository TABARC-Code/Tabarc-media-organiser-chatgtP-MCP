import pytest

from tabarc_media.catalogue import Catalogue, classify


def test_classification():
    assert classify("example.MKV") == "film"
    assert classify("manual.EPUB") == "ebook"
    assert classify("photo.NEF") == "photo"
    assert classify("notes.unknown") == "other"


def test_catalogue_persists_and_filters(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    store = Catalogue(tmp_path / "state")
    number = store.add_library("Collection", root, ["films", "ebooks"],
                               ["plex", "jellyfin"], "quiet")
    assert store.library(number)["scan_profile"] == "quiet"
    store.upsert_batch(number, [
        ("Film_100%.mkv", "film", 125, 500, 10.0),
        ("Books/manual.epub", "ebook", 25, 600, 10.0),
    ])
    assert len(store.files(number)) == 2
    assert [x["relative_path"] for x in store.files(number, search="100%")] == ["Film_100%.mkv"]
    assert [x["relative_path"] for x in store.files(number, search="Film_")] == ["Film_100%.mkv"]
    assert store.status()["files"] == 2

    reloaded = Catalogue(tmp_path / "state")
    assert reloaded.status()["files"] == 2
    assert reloaded.library(number)["applications"] == ["jellyfin", "plex"]


def test_invalid_and_overlapping_roots(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    subdir = root / "shows"
    subdir.mkdir()
    store = Catalogue(tmp_path / "db")
    store.add_library("A", root, ["films"], [])
    with pytest.raises(ValueError, match="Overlapping"):
        store.add_library("B", subdir, ["films"], [])
    with pytest.raises(ValueError, match="profile"):
        store.add_library("C", subdir, ["films"], [], "ultra")
    with pytest.raises(ValueError, match="catalogue directory"):
        store.add_library("D", tmp_path, ["films"], [])
    with pytest.raises(ValueError, match="media type"):
        store.add_library("E", subdir, ["pretend"], [])


def test_interrupted_job_becomes_paused(tmp_path):
    root = tmp_path / "movies"
    root.mkdir()
    data = tmp_path / "state"
    store = Catalogue(data)
    lib = store.add_library("Films", root, ["films"], [])
    job = store.new_job(lib)
    restarted = Catalogue(data)
    assert restarted.job(job)["state"] == "paused"


def test_real_changes_and_offset_paging(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Films", root, ["films"], [], "quiet")
    batch = [
        ("a.mkv", "film", 20, 100, 10.0),
        ("b.mkv", "film", 25, 100, 10.0),
    ]
    assert store.upsert_batch(lib, batch) == 2
    assert store.upsert_batch(lib, [(p, k, sz, mt, 20.0) for p,k,sz,mt,_ in batch]) == 0
    assert store.upsert_batch(lib, [("b.mkv", "film", 26, 101, 30.0)]) == 1
    assert [x["relative_path"] for x in store.files(lib, limit=1, offset=1)] == ["b.mkv"]


def test_legacy_root_identity_does_not_prune_first_scan(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Films", root, ["films"], [])
    store.upsert_batch(lib, [("old.mkv", "film", 5, 20, 1.0)])
    # Existing installations won't have a root fingerprint. Establish one
    # without assuming the first observed directory is the old one.
    with store.connect() as db:
        db.execute("UPDATE libraries SET root_device=NULL, root_inode=NULL WHERE id=?", (lib,))
    stat = root.stat()
    store.finalise_scan(lib, 30.0, stat.st_dev, stat.st_ino)
    assert len(store.files(lib)) == 1
    store.finalise_scan(lib, 40.0, stat.st_dev, stat.st_ino)
    assert store.files(lib) == []


def test_changed_root_requires_explicit_confirmation_and_defers_pruning(tmp_path):
    root = tmp_path / "films"
    root.mkdir()
    (root / "old.mkv").write_bytes(b"original")
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Films", root, ["films"], [])
    old_stat = root.stat()
    store.upsert_batch(lib, [("old.mkv", "film", 8, 100, 1.0)])

    old_root = tmp_path / "old-mount"
    root.rename(old_root)
    root.mkdir()
    (root / "new.mkv").write_bytes(b"replacement")
    report = store.root_review(lib)
    assert report["status"] == "changed"
    assert report["indexed_files"] == 1
    assert report["recorded"]["inode"] == old_stat.st_ino
    current = report["current"]

    with pytest.raises(ValueError, match="REAUTHORISE"):
        store.reauthorise_root(lib, old_stat.st_dev, old_stat.st_ino,
                               current["device"], current["inode"], "yes")
    with pytest.raises(ValueError, match="changed during review"):
        store.reauthorise_root(lib, old_stat.st_dev, -1,
                               current["device"], current["inode"], "REAUTHORISE")
    assert store.root_review(lib)["status"] == "changed"

    store.reauthorise_root(lib, old_stat.st_dev, old_stat.st_ino,
                           current["device"], current["inode"], "REAUTHORISE")
    assert store.root_review(lib)["hold_prune"] is True
    assert len(store.root_review(lib)["history"]) == 1

    store.upsert_batch(lib, [("new.mkv", "film", 11, 101, 50.0)])
    store.finalise_scan(lib, 40.0, current["device"], current["inode"])
    assert {f["relative_path"] for f in store.files(lib)} == {"old.mkv", "new.mkv"}
    assert store.root_review(lib)["hold_prune"] is False

    store.upsert_batch(lib, [("new.mkv", "film", 11, 101, 90.0)])
    store.finalise_scan(lib, 80.0, current["device"], current["inode"])
    assert {f["relative_path"] for f in store.files(lib)} == {"new.mkv"}
    # The index was reconciled; no media file on either root was touched.
    assert (old_root / "old.mkv").read_bytes() == b"original"
    assert (root / "new.mkv").read_bytes() == b"replacement"


def test_root_review_reports_unavailable_directory(tmp_path):
    root = tmp_path / "films"
    root.mkdir()
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Films", root, ["films"], [])
    root.rename(tmp_path / "temporarily-gone")
    assert store.root_review(lib)["status"] == "unavailable"
