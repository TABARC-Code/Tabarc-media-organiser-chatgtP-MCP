# Development standards

## Source and documentation style

Use UK English throughout the source, interface and technical documentation. Keep the prose natural and technically literate; vary sentence and paragraph lengths according to what needs explaining. Dry observations are fine when they describe a genuine problem. Don't force jokes, grandiose claims or commentary which doesn't help somebody maintain the code.

Write as the person maintaining the software, with attention to the assumptions behind each decision. An obvious assignment does not need a comment. A constraint protecting existing media, an unusual API response or a decision about data integrity usually does.

Project-facing documentation should describe the product, the problems it solves and the state of its development. Avoid statements about authorship or the process by which text or code was produced. Optional AI and MCP integration may be discussed as application features.

## Engineering boundaries

- The deterministic organiser must operate without any optional model service.
- The first prototype is strictly read-only with respect to registered media directories.
- Filesystem operations require per-root permission boundaries, previews, journalling and error recovery before write support is introduced.
- Existing application databases, including Plex, Jellyfin and Calibre, must not be edited directly.
- Filenames, media tags, external metadata and remote model output are untrusted inputs.
- Provider keys, tokens and secrets must not appear in logs or committed configuration.
- Don't substitute filename similarity for verified identity when authorising a rename.
- Keep background work incremental, cancelable and low priority; measure load before claiming performance characteristics.
- A feature is complete only after tests pass and related documentation describes its actual behaviour.
- After four meaningful fixes, audit the accumulated changes and run relevant regression tests.

## Useful comments

```python
# A file on a network share might still be growing. Defer it until two
# observations agree on size and modification time.

# A short fingerprint narrows the search; it doesn't establish identity.
# Compare complete hashes before marking copies as exact duplicates.
```

Prefer specific contracts and failure cases in docstrings. If something is untested, record it plainly rather than describing the intended behaviour as fact.
