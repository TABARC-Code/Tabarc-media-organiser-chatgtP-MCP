# Development notes

## 8 October 2026 — Read-only inventory foundation

The first runnable application now has a FastAPI backend, SQLite catalogue and localhost browser dashboard. Libraries have names, approved roots, selected media types, intended consumer applications and one of three scan profiles. The initial forms are functional; they're not yet the more polished first-run wizard described in the specification.

The scanner walks directories without following symbolic links. It keeps a persistent record of relative paths, file sizes, modification times and broad file types, updating records in batches with a short pause between batches. When a scan completes without errors, files missing from that completed inventory are removed from **the catalogue only**. Media files aren't touched.

A failed or interrupted scan doesn't delete records merely because it hasn't seen them this time. Network mounts have a habit of vanishing at thoroughly inconvenient moments, and a temporary disconnection isn't evidence that somebody deliberately removed an entire television collection.

### First implementation checks

The regression suite covers SQLite persistence, input validation, overlapping media roots, filename previews, write-header and origin checks, symbolic-link handling, ignored folders, scan resumption, basic media-type filtering and the absence of media writes in a fixture library. GitHub Actions runs Python 3.11 and 3.12.

An early test used the catalogue's default 100-file page and then complained that only 100 records had appeared. The scanner had indexed all 280 correctly. The test now requests the complete sample rather than quietly pretending pagination is a data-loss bug.

### Limits that still matter

- No film or television identity database has been connected. Suggestions are filename guesses requiring review.
- Selecting an application records the intended consumer; Plex and Jellyfin APIs aren't called yet.
- Media-type selection is extension-based. A video extension cannot establish whether the file is a film, episode, anime or home recording.
- Sidecars are indexed when encountered, but aren't yet linked to a particular media item.
- No ExifTool or FFprobe adapter is hooked up yet; the initial scan uses filesystem metadata only.
- Pause/resume restarts the directory walk and updates existing records in place. A persisted directory cursor can come later if real-world measurements justify it.
- Current throttling is deliberate batching plus sleep, not a measured disk-I/O ceiling or proof of safe behaviour under every shared NAS workload.
- The local browser interface needs more work on folder selection, error presentation and accessibility before a general release.
- Neither the test suite nor the repository contains real user media. A large-library pilot is still required.
- Database migrations, backup/restore, API keys, encrypted credentials, MCP integration and approval-based rename transactions are future work.

## Next engineering pass

First, test the scanner on an SMB/NFS-mounted fixture and measure actual CPU, disk and database load. Add a file-stability check before metadata operations, and a proper media record that separates work identity from physical file location. Then add one provider adapter and a matching review queue. Renaming comes after those pieces can be verified together, not before.

The first useful definition of success is still quite plain: point the application at a collection, get a coherent inventory, and be certain the originals stayed exactly where they were.


## 9 October 2026 — Kaizen integrity pass

The first audit focused on what could go wrong before any media files are modified. The scanner now checks that the registered root still has the same filesystem identity before it reconciles stale catalogue entries. An interrupted, incomplete or unexpectedly redirected scan leaves existing records intact. Previously registered roots without an identity are adopted conservatively on the first clean scan, with pruning deferred until the next successful run.

Change counts now reflect new or modified file records, not every ordinary observation. A separate file-browser panel handles path search and pages of results without filling the notification banner. The local API rejects unexpected Host headers, while a POSIX catalogue lock prevents two service processes from running against the same state directory. The worker retains that lock if a blocked scan survives the shutdown grace period.

The new regression tests exercise root replacement, legacy catalogue records, partial directory failure, concurrent server starts, paging and actual change counts. CI now includes source linting, Python compilation and browser JavaScript syntax checking. The initial lint pass exposed a handful of routine import-order issues, corrected in the same cycle.

The root identity policy intentionally fails closed when a network share changes identity. This may produce false alarms after legitimate NAS remounts, so the next pass needs a reviewed reauthorisation flow. The current implementation isn't an excuse to bypass that safeguard manually in the database. The full decisions and remaining priorities are in [the Kaizen review](kaizen-review-2026-10-09.md).
