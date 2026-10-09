import os
import time

from tabarc_media.catalogue import Catalogue
from tabarc_media.scanner import Scanner


def wait_for(store, job, states, timeout=8):
    finish = time.monotonic() + timeout
    while time.monotonic() < finish:
        state = store.job(job)["state"]
        if state in states:
            return state
        time.sleep(0.015)
    raise AssertionError(f"Job remained {store.job(job)['state']!r}")


def test_read_only_scan_rescan_and_symlink(tmp_path):
    root = tmp_path / "media"
    (root / "Season 01").mkdir(parents=True)
    video = root / "Season 01" / "Example.S01E01.mkv"
    video.write_bytes(b"untouched media file")
    subtitle = video.with_suffix(".srt")
    subtitle.write_text("Subtitles stay where they are")
    ignored = root / ".git"
    ignored.mkdir()
    (ignored / "private.json").write_text("ignored")
    external = tmp_path / "outside.mkv"
    external.write_text("not a library file")
    (root / "outside-link.mkv").symlink_to(external)

    original_bytes = video.read_bytes()
    original_stat = video.stat().st_mtime_ns
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("TV", root, ["television"], ["jellyfin"])
    scanner = Scanner(store)

    job = scanner.start(lib)
    assert wait_for(store, job, {"completed", "failed"}) == "completed"
    assert store.job(job)["changed"] == 2
    names = {f["relative_path"] for f in store.files(lib)}
    assert names == {"Season 01/Example.S01E01.mkv", "Season 01/Example.S01E01.srt"}
    assert video.read_bytes() == original_bytes
    assert video.stat().st_mtime_ns == original_stat

    subtitle.unlink()
    job2 = scanner.start(lib)
    assert wait_for(store, job2, {"completed", "failed"}) == "completed"
    assert len(store.files(lib)) == 1
    assert store.job(job2)["changed"] == 0
    assert video.read_bytes() == original_bytes
    scanner.shutdown()


def test_pause_resume_and_no_pruning_mid_scan(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    for i in range(280):
        (root / f"show.S01E{i:03d}.mkv").write_bytes(b"x")
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Slow scan", root, ["television"], [], "quiet")
    scanner = Scanner(store)
    job = scanner.start(lib)
    scanner.pause(job)
    assert wait_for(store, job, {"paused", "completed"}) == "paused"
    assert len(store.files(lib)) <= 280
    resumed = scanner.start(lib, resume_id=job)
    assert resumed == job
    assert wait_for(store, job, {"completed", "failed"}) == "completed"
    assert len(store.files(lib, limit=500)) == 280
    scanner.shutdown()


def test_selected_media_types_filter_unrelated_files(tmp_path):
    root = tmp_path / "books"
    root.mkdir()
    (root / "novel.epub").write_bytes(b"book")
    (root / "movie.mkv").write_bytes(b"video")
    (root / "book.opf").write_text("local metadata")
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Ebooks", root, ["ebooks"], ["calibre"])
    scanner = Scanner(store)
    job = scanner.start(lib)
    assert wait_for(store, job, {"completed", "failed"}) == "completed"
    assert {f["relative_path"] for f in store.files(lib)} == {"novel.epub", "book.opf"}
    scanner.shutdown()


def test_changed_root_fails_without_pruning_index(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    film = root / "film.mkv"
    film.write_bytes(b"original")
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("Films", root, ["films"], [])
    scanner = Scanner(store)
    first = scanner.start(lib)
    assert wait_for(store, first, {"completed", "failed"}) == "completed"
    assert len(store.files(lib)) == 1
    original = tmp_path / "old-root"
    root.rename(original)
    root.mkdir()
    (root / "impostor.mkv").write_bytes(b"different")
    second = scanner.start(lib)
    assert wait_for(store, second, {"completed", "failed"}) == "failed"
    assert {f["relative_path"] for f in store.files(lib)} == {"film.mkv"}
    assert "identity changed" in store.job(second)["message"]
    assert (original / "film.mkv").read_bytes() == b"original"
    scanner.shutdown()


def test_scan_error_does_not_prune_other_catalogue_rows(tmp_path, monkeypatch):
    root = tmp_path / "library"
    nested = root / "Season 01"
    nested.mkdir(parents=True)
    (nested / "old.mkv").write_bytes(b"previous")
    store = Catalogue(tmp_path / "state")
    lib = store.add_library("TV", root, ["television"], [])
    scanner = Scanner(store)
    first = scanner.start(lib)
    assert wait_for(store, first, {"completed", "failed"}) == "completed"

    real_scandir = os.scandir
    def blocked_scandir(path):
        if str(path) == str(nested):
            raise PermissionError("Simulated unavailable share")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", blocked_scandir)
    second = scanner.start(lib)
    assert wait_for(store, second, {"completed_with_errors", "failed"}) == "completed_with_errors"
    assert {f["relative_path"] for f in store.files(lib)} == {"Season 01/old.mkv"}
    assert (nested / "old.mkv").read_bytes() == b"previous"
    scanner.shutdown()
