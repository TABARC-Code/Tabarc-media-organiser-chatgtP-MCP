# Kaizen review — 9 October 2026

**Scope:** current read-only catalogue alpha, Python service, browser controls, SQLite schema, worker behaviour, GitHub Actions and the earlier product specification.

The aim of this pass was to reduce the chance of an incorrect inventory before introducing remote database matching or file-changing operations. A faster matcher built on an unreliable catalogue would only organise mistakes more efficiently.

## Observe: problems found

| Priority | Finding | Consequence | Disposition |
| --- | --- | --- | --- |
| P0 | A changed mount or replaced library root could cause an apparently complete scan of the wrong directory. | Existing records could be pruned from the catalogue even though the original media still exists elsewhere. | Guard root device/inode, recheck before reconciliation, don't prune if unverified. |
| P0 | Two server processes could initialise the same SQLite job state and scan the same collection. | Interrupted-job marking, job collision and contradictory reconciliation. | Exclusive POSIX catalogue lock on service startup. |
| P1 | Every observed file incremented the changed counter on every scan. | The dashboard couldn't distinguish real changes from routine rescans. | Compare batched records before refreshing observation timestamps. |
| P1 | Arbitrary HTTP Host values were accepted. | Possible DNS-rebinding route to an otherwise loopback-bound service. | Reject untrusted hosts; retain origin and local-action checks. |
| P1 | Catalogue browsing had no useful pagination. | Users inspecting a large library saw a limited sample in the notification area. | Add offset paging, path search and a persistent file browser panel. |
| P1 | Queued directories weren't rechecked immediately before traversal. | A changed symlink could lead the scanner towards an unapproved location. | Verify queued paths remain within the configured root. |
| P2 | Test coverage concentrated on happy-path scanning. | Root replacement, concurrent servers and incomplete directory reads weren't exercised. | Expand regression scenarios and cross-version CI. |
| P2 | There was no Python lint or browser syntax gate. | Preventable source errors reached test execution. | Add Ruff, JavaScript syntax check and Python compilation. |

## Changes implemented in this cycle

### Catalogue integrity

Library registration now records the filesystem identity of the approved root. The scanner compares that identity before working and again before reconciling missing records. A changed root causes the job to fail safely; the old catalogue remains for review. Existing pre-upgrade registrations have no recorded root identity, so their first clean scan establishes one **without pruning records**. This conservative migration avoids treating the current mount as proof of what an older version had indexed.

The file index now counts additions and modifications rather than every pass over an unchanged file. The batch query does add a small amount of database work; the trade-off is more accurate change reporting with no full-file hashing.

File-list endpoints now accept a bounded offset, and the browser has a paged search panel. The same relative-path sorting rule is applied throughout so normal paging produces consistent results while the catalogue is stable.

### Process and request boundaries

The application now takes a POSIX advisory lock in its local state directory **before** initialising SQLite. Starting a second server against the same catalogue fails. Shutdown asks the worker to stop and only releases that lock if the worker actually terminates. A network I/O stall must not permit a second process to begin writing to the catalogue while the first worker is still alive.

The HTTP server continues to bind to loopback. Trusted host validation rejects unexpected Host headers; origin checks and the local action header remain in place. These controls are not a substitute for account authentication and TLS, so LAN or internet hosting remains unsupported.

### Worker behaviour and validation

Traversal still skips directory links, but a queued directory is revalidated when it is actually visited. A failed traversal never authorises pruning entries that weren't seen. The regression suite now covers interrupted scans, unchanged-file counts, root replacement, legacy root registration, cross-origin and untrusted-host requests, catalogue persistence, pagination, process locking and partial directory failures.

CI adds Python lint, Python bytecode compilation, JavaScript syntax and pytest under two Python versions.

## Check: evidence and limits

GitHub Actions is the repeatable integration check for this branch. A green run means the recorded fixtures passed; it does **not** establish live Plex/Jellyfin interoperability or large NAS performance. Tests use synthetic file contents, which is appropriate for the read-only scanner but insufficient for metadata matching.

There is an important trade-off with root identity. On some network filesystems a legitimate remount may change the observed device or inode even when the share contains the same media. Failing closed is correct for data integrity, but an explicit, audited root reauthorisation flow is required before general release. Do not silently reset identity when that happens.

POSIX advisory locking covers this Linux alpha. Windows packaging needs its own locking implementation and tests. Scans may still block on a stuck network filesystem beyond the shutdown grace period; the service retains its lock rather than pretending recovery is complete.

## Act: next prioritised cycle

1. **Root reauthorisation and provenance.** Present old and new root identities, sample paths and a user-controlled review action; persist the decision and keep first scan after reauthorisation non-pruning. Test network remounts and malicious symlink substitutions.
2. **Catalogue lifecycle.** Explicit library edit/remove actions, backup/restore, versioned schema migrations and a history of removed catalogue records. Removal of an index entry must never imply deletion of media.
3. **Repeatable performance assessment.** Benchmark batches on local SSD, spinning disks and network shares. Record files/second, DB writes, process CPU, memory, latency and I/O impact with an idle media server and during playback. Set resource ceilings from measurements rather than guesses.
4. **Accurate identity records.** Separate work, edition, release and physical file. Add existing NFO/OPF identifier extraction before network lookups; don't allow a filename guess to become an authorised rename.
5. **One metadata provider at a time.** Introduce TMDB/TVmaze matching with rate limiting, response provenance and a manual review queue. Add anime episode-order rules and multi-episode fixture coverage before bulk automation.
6. **Scoped file transaction engine.** Only after matching accuracy is measured. Start with dry-run comparisons and an immutable journal; add one verified rename class at a time and test recovery from interrupted operations.

## Measurements for the next gate

| Measure | Acceptance direction |
| --- | --- |
| Media file modifications during observe-only scans | Exactly zero |
| Accidental catalogue pruning after incomplete or uncertain scans | Exactly zero in fault-injection tests |
| Repeat scan of unchanged files | Zero newly/modified records reported |
| Root replacement | Detected and blocked |
| Concurrent service processes | Second instance rejected |
| Match accuracy | Evaluated on a labelled corpus, not asserted from fuzzy scores |
| CPU/I/O budget | Quantified for Quiet/Balanced/Fast on actual hardware |
| Recovery | Documented, exercised, and independently checked |

### Boundary of the current release

This remains a read-only alpha. It does not yet implement file renaming, NFO writing, metadata provider calls, an MCP server, secret encryption, duplicate removal, background transcoding or real media-server refreshes. Those features should not be presented as working until code and tests establish that they are.

The underlying principle is uncomplicated: make each small improvement measurable, retain the protections earned by earlier work, and avoid mistaking a green unit test for a guarantee about a forty-terabyte network share.
