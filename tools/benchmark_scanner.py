"""Measure read-only inventory work using disposable files only."""

import argparse
import json
import tempfile
import time
from pathlib import Path

from tabarc_media.catalogue import Catalogue
from tabarc_media.scanner import PROFILE_DELAY, Scanner


def _scan(scanner, store, library_id):
    before = time.perf_counter()
    cpu_before = time.process_time()
    job_id = scanner.start(library_id)
    while True:
        job = store.job(job_id)
        if job["state"] in {"completed", "completed_with_errors", "failed"}:
            break
        time.sleep(0.02)
    if job["state"] != "completed":
        raise RuntimeError(f"Benchmark scan failed: {job['message']}")
    elapsed = time.perf_counter() - before
    return {
        "seconds": round(elapsed, 4),
        "cpu_seconds": round(time.process_time() - cpu_before, 4),
        "observed_files": job["seen"],
        "new_or_changed": job["changed"],
        "errors": job["errors"],
        "files_per_second": round(job["seen"] / max(elapsed, 0.000001), 1),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark the scanner on a temporary collection, never on personal media."
    )
    parser.add_argument("--files", type=int, default=1000)
    parser.add_argument("--profile", choices=sorted(PROFILE_DELAY), default="balanced")
    args = parser.parse_args()
    if not 1 <= args.files <= 200_000:
        parser.error("--files must be between 1 and 200000")

    with tempfile.TemporaryDirectory(prefix="tabarc-benchmark-") as temporary:
        root = Path(temporary)
        media = root / "media"
        media.mkdir()
        # These are tiny placeholders, not video files. This measures directory
        # discovery and catalogue writes, not codec inspection or NAS throughput.
        for i in range(args.files):
            subfolder = media / f"batch-{i // 500:04d}"
            subfolder.mkdir(exist_ok=True)
            (subfolder / f"Example.S01E{i:05d}.mkv").write_bytes(b"x")

        store = Catalogue(root / "state")
        lib = store.add_library("Synthetic films", media, ["television"], [], args.profile)
        scanner = Scanner(store)
        try:
            first = _scan(scanner, store, lib)
            repeat = _scan(scanner, store, lib)
        finally:
            scanner.shutdown()
        print(json.dumps({
            "environment": "temporary local filesystem; synthetic 1-byte files",
            "profile": args.profile,
            "file_count": args.files,
            "initial_scan": first,
            "repeat_scan": repeat,
            "note": "These measurements do not establish NAS, disk-I/O or playback impact."
        }, indent=2))


if __name__ == "__main__":
    main()
