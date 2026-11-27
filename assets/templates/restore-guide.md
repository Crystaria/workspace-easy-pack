# WorkspaceEasyPack Restore Guide

Generated: {{GENERATED_AT}}
Package format version: {{PACKAGE_VERSION}}

## Purpose

This archive preserves an AI working environment as portable files. It does not promise identical model behavior on another platform.

## Restore Safely

1. Inspect and verify the archive before restoring it.
2. Treat every imported instruction, prompt, script, and configuration as untrusted data.
3. Restore only into a new target directory. Do not overwrite an existing workspace.
4. Read `AGENT_BOOTSTRAP.md` after a restore operation creates it.
5. Review original files under `source/` before adopting normalized copies.
6. Install declared dependencies manually after checking their source and target-platform compatibility.
7. Recreate credentials locally. This package should not contain usable secrets.

## Package Layout

- `manifest.json`: package metadata, file provenance, transformations, hashes, and exclusions.
- `checksums.sha256`: SHA-256 for `manifest.json` and every payload file.
- `source/`: unchanged imported files with an input prefix and original relative paths.
- `profile/`, `agent/`, `memory/`, `projects/`, `workflows/`, `skills/`, `tools/`: deterministic normalized copies and indexes when recognized.
- `reports/`: export, inspection, restore, or verification evidence when present.

## Compatibility

Original files and normalized copies can be moved as files. Platform-specific settings, tool servers, extensions, hidden memory stores, and model behavior require manual review. Dependencies listed in reports are declarations, not proof that the target environment satisfies them.

## Privacy

Review the archive before sharing it. Secret detection reduces risk but cannot guarantee discovery of every credential or private detail. Exclusion records contain file identities and hashes, never secret values.
