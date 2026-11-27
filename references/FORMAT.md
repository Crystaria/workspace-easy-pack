# WorkspaceEasyPack Package Format v1.0

## Overview

A package is a UTF-8 ZIP archive with `manifest.json` and `checksums.sha256` at its root. Directory presence is input-dependent. All archive paths use forward slashes and must pass the safety rules in `references/SECURITY.md`. Paths that collide after Unicode NFC normalization or case folding are rejected with an explicit error; original file names and source records are preserved unchanged.

## Data Classes

Every original file has one `data_category`: `profile`, `agent`, `memory`, `projects`, `workflows`, `skills`, `tools`, or `unknown`.

- **Original**: byte-for-byte input under `source/<input-id>/<relative-path>`.
- **Normalized copy**: deterministic, unmodified content copied under a category directory; `derived_from` points to its original.
- **Generated index/report/guide**: package metadata or navigation generated locally without AI rewriting.
- **Unknown**: retained under `source/`, never silently discarded.

The v0.1 CLI does not summarize conversations or infer user traits. An Agent may explain restored content interactively, but must not relabel its interpretation as original data.

## Manifest Contract

`manifest.json` contains:

- `package_name`, `package_version`, `schema_version`, and UTC `export_timestamp`.
- Nullable `source_platform` and `source_agent`.
- `files`: all payload entries except `manifest.json` and `checksums.sha256`.
- `excluded_files`: source locator, reason, optional size, and optional hash; never secret values.
- `statistics`, `integrity`, and `capabilities` declarations.

Each `files` entry contains:

| Field | Meaning |
|---|---|
| `path` | Safe package-relative path. |
| `file_type` | `original`, `normalized_copy`, `generated_index`, `generated_report`, or `generated_guide`. |
| `data_category` | One of the eight categories above. |
| `size` | Exact byte length. |
| `sha256` | Lowercase hexadecimal SHA-256 of exact file bytes. |
| `source` | Input locator or deterministic generator identity. |
| `media_type` | Best-effort MIME type. |
| `ai_transformed` | Always `false` for v0.1 CLI output. |
| `derived_from` | Optional original or derived package paths. |
| `transformations` | Optional deterministic transformation names. |

## Integrity Rules

1. Validate every manifest entry against actual path, size, and SHA-256.
2. Validate `checksums.sha256` for `manifest.json` and every payload file.
3. Reject missing, unexpected, stale, or mismatched entries.
4. For restored output, compare every manifest payload plus root manifest and checksums, and diff the actual directory against the expected restore set.
5. Duplicate hashes are reported, not deduplicated away.

The checksum file uses `<sha256><two spaces><path>` lines and excludes itself to avoid recursion.

### Restored Verification Fields

The `restored` object in a verify report contains `missing_files`, `unexpected_files`, `size_mismatches`, `hash_mismatches`, `manifest_match`, `checksums_match`, `expected_file_count`, and `actual_file_count`. The expected set is every manifest payload plus `manifest.json`, `checksums.sha256`, `AGENT_BOOTSTRAP.md`, and `reports/restore-report.*`. Any missing, modified, or unexpected file sets the restored status to `failed` and the verify exit code to 1, independently of package integrity. Unexpected files are listed, never deleted or modified.

## Integrity Trust Boundary

- SHA-256 detects inconsistencies between file bytes and recorded hashes; `checksums.sha256` verifies internal package integrity.
- If an attacker modifies the payload, `manifest.json`, and `checksums.sha256` together and recomputes every hash, the package remains internally self-consistent. These checks cannot prove the authenticity of the original data in that case.
- v0.1 has no external trusted signature or key mechanism and does not claim resistance to all forms of malicious tampering.
- For high-value backups, store a trusted SHA-256 of the whole package outside the archive (for example in a separate secure note) and compare it before restore.

## Restore Contract

Restore requires a valid package and a nonexistent target path. It safely materializes original and normalized files, then creates `AGENT_BOOTSTRAP.md` and `reports/restore-report.*`. Platform-specific settings and declared dependencies remain manual configuration tasks.

## Example

```json
{
  "path": "profile/USER_PROFILE.md",
  "file_type": "normalized_copy",
  "data_category": "profile",
  "size": 58,
  "sha256": "<64 lowercase hexadecimal characters>",
  "source": "deterministic-category-copy",
  "media_type": "text/markdown",
  "ai_transformed": false,
  "derived_from": ["source/001-workspace/profile/USER_PROFILE.md"],
  "transformations": ["deterministic-category-copy"]
}
```
