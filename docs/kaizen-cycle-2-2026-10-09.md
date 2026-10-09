# Kaizen cycle 2 — mount recovery and catalogue protection

**Date:** 9 October 2026
**Scope:** read-only Linux alpha; no media-file writes or external metadata integrations.

## What changed

An explicit storage-root recovery path now handles the situation where an approved NAS mount or directory appears under a different filesystem identity. Rather than silently treating the replacement as the original folder, the catalogue shows the recorded device/inode, the currently observed pair and a small sample of previously indexed paths.

The operator must inspect the storage independently and type `REAUTHORISE` to accept a changed identity. The confirmation request includes both the original and replacement identities. If either changed between review and confirmation, the operation is rejected. The decision is recorded in `root_events`, and an active scan prevents reauthorisation.

The first **complete** scan after an approved change deliberately retains missing catalogue records. A later successful scan can reconcile them. A paused or failed scan leaves the hold in place; there is no silent pruning just because a directory was temporarily unavailable.

The second change is a SQLite backup command. It obtains the same exclusive process lock as the server, makes a consistent SQLite snapshot and checks its integrity before atomically publishing a private backup file. Existing destinations are not overwritten, and backups inside registered media roots are refused. The command needs the service stopped. It creates a copy of the **catalogue**, not the films, books, audio files or photos themselves.

Finally, a synthetic benchmark exercises initial and repeat scans. It reports elapsed time, process CPU time, observed files, changed files and throughput. The harness creates disposable one-byte files; it cannot be used to claim real-world NAS performance.

## Why these changes matter

The original root-integrity guard had a deliberate weakness: it could prevent a bad reconciliation, but legitimate network remounts had no supported recovery route. A user might reasonably try editing the database to get a blocked library running again. Explicit review and audit history offer a safer alternative, without allowing a scan to silently authorise its own target.

A catalogue without an independent backup is another problem waiting to happen. SQLite's WAL mode is reliable when used correctly, but copying the live database file alone is not a sound backup procedure. The snapshot command avoids that particular mistake and verifies the result before publication.

The benchmark addresses a different sort of risk. Delaying every 64 files may reduce peak activity, but it is not the same as a measured CPU or disk-I/O ceiling. The initial tool gives repeatable local baselines without pretending that temporary one-byte files behave like a NAS holding large films.

## Verification

New regression cases cover root-review status, wrong and stale confirmation, event history, deferred pruning, unchanged original media, API confirmation restrictions, backup consistency, backup location restrictions, existing backup protection and the exclusive server lock. The benchmark also has a small automated smoke test checking that a repeat scan finds no changed records.

Continuous integration runs the test suite on Python 3.11 and 3.12, with Ruff, Python compilation and JavaScript syntax checking. A passing build verifies the scripted fixtures; it does not demonstrate compatibility with live Plex or Jellyfin servers.

## Remaining limitations

- Root device/inode is a useful local guard, not a cryptographic identity. Some legitimate remounts require review, and a matching identifier does not prove every nested file remains the same.
- A directory can still be swapped between separate filesystem checks. A future scanner should favour descriptor-relative operations on supported platforms and test TOCTOU resistance explicitly.
- The dashboard displays a small sample of prior files, not a complete comparison of the old and new trees. Approval must remain a conscious decision.
- SQLite backups are not encrypted. They contain sensitive paths and filenames, and no automated restore workflow has been validated.
- The benchmark tests inventory only. NAS performance, disk bandwidth, large metadata probes and simultaneous playback remain unmeasured.
- There is still no automatic naming, provider-backed identification, NFO/OPF export, external media-server control or MCP service. These features should continue to be introduced behind independent validation gates.

## Next small improvements

The next useful increments are a verified restore procedure, versioned catalogue migrations, additional network-share fault fixtures, and a measured local-versus-NAS performance run. Once the catalogue itself has reliable recovery, metadata import should start with existing local identifiers and sidecars before remote TMDB, TVmaze and book-provider requests.

These improvements are intentionally narrower than the full media-organiser roadmap. They reduce the amount of damage a mistake could cause without making the project harder to operate.
