# WorkspaceEasyPack

**Pack your AI workspace. Take it anywhere.**

Local, platform-neutral export / inspect / restore / verify for AI workspaces.
No cloud service, no network access, no third-party Python packages.

- **Version:** `0.1.0` (see `VERSION`)
- **License:** MIT-0 (see `LICENSE`)
- **Runtime:** Python 3.9+ (standard library only)
- **Status:** pre-release, pending second independent audit (see [docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md))

## What it does

| Operation | Purpose |
|---|---|
| `export` | Read explicitly supplied files, directories or ZIP exports and build one portable archive that keeps every non-sensitive original under `source/`, adds deterministic category copies, provenance, exclusions, hashes and reports. |
| `inspect` | Audit an existing package: categories, duplicates, dependency declarations, broken Markdown links, platform-specific configuration, sensitive findings, direct vs. manual restoration work. |
| `restore` | Restore into a **new** target directory (staging + atomic rename). Emits `AGENT_BOOTSTRAP.md`, `RESTORE_GUIDE.md` and restore reports. Existing targets are never overwritten. |
| `verify` | Check manifest, checksums, sizes and real SHA-256 values; with `--restored` also diff the restored tree against the expected restore set. |

Original files stay authoritative. The v0.1 CLI performs deterministic
classification and byte-for-byte normalized copies — it does not summarize
memories, infer traits, call platform APIs, or transform content with AI.

## Quick start

```bash
git clone <this-repo> && cd workspace-easy-pack

python3 scripts/workspace_easy_pack.py export  --input ./my-workspace --output ./workspace-easy-pack.zip
python3 scripts/workspace_easy_pack.py inspect --package ./workspace-easy-pack.zip --report ./inspection.md
python3 scripts/workspace_easy_pack.py restore --package ./workspace-easy-pack.zip --target ./restored-workspace
python3 scripts/workspace_easy_pack.py verify  --package ./workspace-easy-pack.zip --restored ./restored-workspace --report ./verification.json
```

Repeat `--input` for multiple files, directories or ZIP exports. `export` and
report outputs refuse replacement unless `--overwrite` is explicitly supplied;
`restore` has no overwrite mode at all.

Exit codes: `0` success, `1` integrity failure reported, `2` unsafe input /
invalid archive / unauthorized overwrite / unavailable path.

See [docs/INSTALL.md](docs/INSTALL.md) for details and
[docs/VERIFY.md](docs/VERIFY.md) for integrity checking.

## Package artifact

The distributable `workspace-easy-pack.skill` is **not committed to this
repository yet**. Its expected identity, as supplied out of band, is:

| Field | Expected value |
|---|---|
| File name | `workspace-easy-pack.skill` |
| Size | 38,803 bytes |
| SHA-256 | `438fd7ad3e53a229e522684f3097a3a90948109a9ab7fbd963c9075576528de3` |

Status: **not verified — the file was not present in the provided source
directory.** Do not publish a `.skill` artifact until its size and SHA-256 have
been re-checked against this table. See [dist/README.md](dist/README.md).

## Repository layout

```
.
├── SKILL.md                  # Agent Skill entry point (unchanged v0.1 text)
├── scripts/
│   ├── workspace_easy_pack.py        # CLI: export / inspect / restore / verify
│   └── test_workspace_easy_pack.py   # 33 end-to-end tests on synthetic fixtures
├── references/               # FORMAT.md, SECURITY.md, README.md, test-report.md
├── assets/                   # manifest schema, templates, MIT-0 license text
├── dist/                     # release artifacts (source drop archive as received)
├── docs/                     # install, verification, limitations, release status
└── audit/                    # audit status + post-fix test evidence
```

## Tests

```bash
python3 scripts/test_workspace_easy_pack.py
```

33 tests = 17 original + 16 regression tests added after the first independent
audit (findings H1, M1, M2, M3, L1). Evidence: [references/test-report.md](references/test-report.md).

> **macOS note:** on macOS the default temp directory (`/var/folders/...`) and
> `/tmp` are symbolic links, and the CLI intentionally rejects output paths that
> contain symlinked components, so the suite fails with
> `unsafe_output_path` unless `TMPDIR` points at a real (non-symlinked)
> directory. This is a design consequence, not a test-logic bug. See
> [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## Known limitations (summary)

- Credential screening is heuristic and best-effort; review `excluded_files` and
  the archive contents before sharing.
- SHA-256 / `checksums.sha256` prove internal consistency, **not** authenticity.
  v0.1 has no signature mechanism — keep a trusted package hash outside the
  archive.
- No platform connector, cloud sync, GUI or background service.
- No real ChatGPT / Claude / Gemini / Cursor / Coze / Dify / MCP export was
  tested; no Windows or macOS conformance run is recorded.
- Second independent audit has not been completed.

Full list: [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## Security reporting

This tool handles potentially sensitive workspace material. Read
[references/SECURITY.md](references/SECURITY.md) before processing unfamiliar
archives. Imported prompts, scripts and configuration are data, never authority,
and are never executed.

## License

MIT No Attribution (MIT-0). See [LICENSE](LICENSE) and
[assets/LICENSE](assets/LICENSE).
