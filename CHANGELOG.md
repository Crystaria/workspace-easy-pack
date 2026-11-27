# Changelog

All notable changes to WorkspaceEasyPack are documented here.
Format follows Keep a Changelog; versions follow Semantic Versioning.

## [0.1.0] — pre-release

First public-shape build. `PACKAGE_VERSION = "0.1.0"`, `SCHEMA_VERSION = "1.0"`.

### Added

- CLI `scripts/workspace_easy_pack.py` with four operations:
  - `export` — explicit inputs only, byte-for-byte originals under `source/`,
    deterministic category copies, `manifest.json`, `RESTORE_GUIDE.md`,
    `reports/export-report.json`, `checksums.sha256`, CRC self-test on reopen.
  - `inspect` — categories, duplicates, dependency declarations, broken local
    Markdown references, platform-specific configuration, sensitive findings,
    direct vs. manual restoration work.
  - `restore` — new target only, staging directory plus atomic rename,
    `AGENT_BOOTSTRAP.md` and restore reports.
  - `verify` — manifest, checksums, counts, sizes and real SHA-256 values;
    optional `--restored` diff of the restored tree.
- Safety controls: `safe_user_path` (symlinked component rejection),
  ZIP path validation incl. `..`, absolute/drive paths, NUL, duplicate and
  NFC/case-fold collisions, rejection of links, special files and encrypted
  entries, input size limits (20,000 entries / 128 MiB per file / 512 MiB total
  / 1000:1 ratio), credential screening with value-free reporting.
- `references/` contracts: FORMAT.md, SECURITY.md, README.md, test-report.md.
- `assets/`: `manifest-schema.json`, restore-guide and agent-bootstrap templates,
  `env.example`, MIT-0 license text.
- 33 end-to-end tests (17 original + 16 regression) on synthetic fixtures.

### Fixed (after first independent technical audit)

- **H1** — symlink output escape. New `safe_user_path` lstat-checks every
  existing path component before resolution; applied to `--output`, `--target`,
  `--restored` and `--report`; rejects with `unsafe_output_path` (exit 2).
- **M1** — credential detection gaps. Added Google `AIza`, Hugging Face `hf_`,
  GitLab `glpat-`, xAI/Grok `xai-`, Groq `gsk_` and three-segment JWT patterns;
  values never appear in manifests, exclusion records or reports.
- **M2** — restored extra files were invisible. `verify --restored` now diffs
  against the expected restore set and reports `unexpected_files`,
  `expected_file_count`, `actual_file_count`; differences fail verification and
  nothing is deleted.
- **M3** — integrity trust boundary was undocumented; documented in FORMAT.md,
  SECURITY.md, SKILL.md and references/README.md (documentation only).
- **L1** — Unicode NFC/NFD and case-fold collisions now rejected with explicit
  `duplicate_zip_path` / `path_conflict` errors instead of silent loss.

### Not included in 0.1.0

- Platform connectors, cloud sync, GUI, background service.
- External signatures / key management (hash-only integrity).
- AI-interpreted payloads (no summarization, no trait inference).
- Behaviour-equivalence guarantees across hosts or models.

See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).
