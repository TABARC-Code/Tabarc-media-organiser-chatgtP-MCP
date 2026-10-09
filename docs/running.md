# Running the read-only prototype

**Status:** v0.1 alpha. This is a local inventory prototype, not a production organiser. It doesn't fetch media database matches, generate NFOs, rename files or apply proposed changes.

## Requirements

Python 3.11 or later. The initial supported environment is Linux; other platforms may work but have not been validated. A browser is needed for the local dashboard.

## Install

```bash
git clone https://github.com/TABARC-Code/Tabarc-media-organiser-chatgtP-MCP.git
cd Tabarc-media-organiser-chatgtP-MCP
git switch development/read-only-foundation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m tabarc_media
```

Visit **http://127.0.0.1:8787** on the same machine. The service deliberately binds to localhost, not every network interface.

Run the automated checks with `python -m pytest -q`.

### Other options

```bash
tabarc-media --port 8788 --data-dir /path/to/empty/local/state-folder
```

The default catalogue path is `~/.local/share/tabarc-media-organiser/catalogue.sqlite3`. Set `TABARC_DATA_DIR` to change this without passing `--data-dir`. Keep it on reliable **local storage**, outside all media roots. SQLite files, job history and write-ahead logs will be created there.

## Current operating safeguards

The service accepts localhost hostnames only, and the Linux alpha takes an exclusive catalogue lock so a second server cannot start against the same state directory. Library roots have recorded device/inode identities. A replaced directory or changed mount causes an error rather than silently reconciling an unrelated tree. The dashboard now offers an explicit root-review step, with recorded and current directory identities, a small sample of historical filenames, and a typed confirmation to approve a replacement.

File browsing now has search and numbered pages, and scan history distinguishes files seen from genuinely new or updated records. These improvements don't change the read-only nature of the prototype.

## First scan

1. Enter a library name, the **absolute path on the machine running the service**, and one or more media types. Select any applications that use the files; they are labels only at this stage, not active server connections.
2. Select Quiet, Balanced or Fast. These profiles change the delay between indexing batches. Resource metrics and operating-system-level scheduling controls are not implemented yet.
3. Add the library and click **Scan library**. The background worker reads names, sizes, file types and modification timestamps. It does not read entire video streams or calculate full hashes.
4. The dashboard shows the number of indexed files, job history and sample filename suggestions. Suggestions use filename patterns only: they are not authoritative matches. There is **no Apply button**.

Paused scans recheck the folder from the beginning when resumed. Already catalogued files are updated in place. Incomplete or faulty scans never prune unseen files from the catalogue, which matters when a network share briefly disappears.

## Recovering a changed mount

If a mount is replaced or remounted with a different recorded device/inode, the scan stops and keeps the existing catalogue intact. The path can be inspected through **Check root** beside the relevant library. Review the old and current identities, sample file status and actual contents of the mounted share before accepting a change.

Only use **Approve changed root** when the displayed folder really belongs to the intended library. Type `REAUTHORISE` in the confirmation field. The application records an audit event and retains the existing catalogue through the first complete scan after approval. A later complete scan may reconcile entries no longer present. An incomplete scan does not clear this safeguard.

Reauthorisation is blocked while a scan is active. If a mount is unavailable or redirected through a symbolic link, restore the path first; approval is not offered.

This is a cautious recovery mechanism, not cryptographic proof of media identity. On network storage, the recorded device/inode may change after an ordinary remount, so verifying the actual share is essential.

## Backing up the local catalogue

Stop the web service before running a backup. The snapshot operation uses SQLite's backup API, checks the result for corruption, writes a private file and refuses to overwrite an existing destination.

```bash
python -m tabarc_media --backup /home/user/backups/media-catalogue-2026-10-09.sqlite3
```

For a non-default catalogue location, also specify `--data-dir /path/to/state`. The destination directory must already exist and **must be outside all registered media roots**. The backup contains your library paths, indexed filenames and job information, so treat it as private data. It is not encrypted.

Backups cannot run while the server holds the catalogue lock. Restoring a snapshot is not yet supported through the interface; keep the original and the exported copy until a tested restore and migration procedure exists.

## Limitations

- A server-side directory picker, media database lookups, metadata sidecars, duplicate detection, watcher service, API keys, AI/MCP connections and Plex/Jellyfin refreshes are not available yet.
- The interface doesn't presently allow removing a library or editing its settings. The SQLite catalogue persists across restarts.
- Filename suggestions are simple, unverified previews and may omit multi-episode, anime and edition details; do not use them as a source of truth.
- File records are updated in batches; scans might take a while on large network shares. No performance claims have been established on large datasets.
- This is a localhost application without account authentication. **Do not expose it to the LAN or internet** using a reverse proxy without adding proper authentication and transport security.
- A read-only *application* does not make a writable filesystem mount read-only. Where possible, test against genuinely read-only media mounts or disposable fixtures.

Please report failing media scans with platform, Python version, filesystem type and an anonymised example path. Never post personal folder listings or API credentials in an issue.
