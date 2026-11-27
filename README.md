# WorkspaceEasyPack

**Pack your AI workspace. Take it anywhere.**

WorkspaceEasyPack is a local Agent Skill that backs up an AI workspace into one
portable archive, then inspects, restores and verifies it. No cloud service, no
network access, no third-party Python packages.

`v0.1.0` · MIT-0 · Python 3.9+ · pre-release

## Why

An AI workspace usually lives inside a single product: memories, agent
instructions, projects, Skills, tool configuration. Moving it to another host,
or just keeping a long-term copy, tends to lose the structure — or carries
secrets along with it.

WorkspaceEasyPack writes one ZIP that preserves every included original file
byte-for-byte, records where each file came from, and leaves suspected
credentials out.

## What you get

| Command | What it does |
|---|---|
| `export` | Builds one archive from the files and folders you point at. Originals are kept as-is; recognised content also gets a categorised copy. |
| `inspect` | Shows what is inside before you share it: categories, duplicates, broken links, platform-specific config, sensitive findings. |
| `restore` | Unpacks into a **new** folder with a bootstrap guide and a restore report. Never writes into an existing folder. |
| `verify` | Recomputes every SHA-256 against the manifest, and can diff a restored folder against what the package says it should contain. |

Exit codes: `0` success, `1` integrity failure reported, `2` unsafe input,
invalid archive or unavailable path.

## Quick start

```bash
git clone https://github.com/Crystaria/workspace-easy-pack.git
cd workspace-easy-pack

python3 scripts/workspace_easy_pack.py export  --input ./my-workspace --output ./workspace.zip
python3 scripts/workspace_easy_pack.py inspect --package ./workspace.zip --report ./inspection.md
python3 scripts/workspace_easy_pack.py restore --package ./workspace.zip --target ./restored
python3 scripts/workspace_easy_pack.py verify  --package ./workspace.zip --restored ./restored --report ./verification.json
```

Repeat `--input` for extra files, folders or ZIP exports. Read the generated
`RESTORE_GUIDE.md` before adopting anything into a new host, and recreate
credentials there instead of copying them out of an archive.

There is nothing to install beyond Python 3.9+. See
[docs/INSTALL.md](docs/INSTALL.md) for first-run details, macOS path notes and
how to run the test suite.

## Safety

- **Opt-in scope.** Only the input paths you explicitly name are read; a named
  directory is traversed, but nothing outside your inputs and outputs is looked
  at. No external accounts, no network calls.
- **No silent overwrites.** Export and report outputs refuse to replace existing
  files unless you pass `--overwrite`; restore has no overwrite mode.
- **Credential screening.** Private keys and credential-bearing files are
  excluded whole-file and reported without the value. Detection is heuristic: it
  reduces risk but cannot guarantee that every credential or secret is found.
- **Path safety.** Output paths that contain symbolic links are rejected instead
  of followed. Archives with traversal paths, links, special files, encrypted
  entries or Unicode/case collisions are refused.
- **Imported content is data.** Scripts, prompts and configuration from an
  archive are never executed.
- **Hash-based integrity.** Every payload is recorded in `manifest.json` and
  `checksums.sha256`, and re-hashed on verify.

## Known limitations

- **Credential detection is best-effort.** Private keys and credential-shaped
  files are excluded whole-file, but no pattern list is complete — always review
  `excluded_files` and the archive contents before sharing.
- **On macOS, the default temp directory may not work.** The CLI refuses any path
  that goes through a symbolic link, and macOS reaches `/var` and `/tmp` that
  way. Use a real path under your home directory for `--output`, `--target`,
  `--report` and `TMPDIR`.
- **Concurrent writes are not protected.** Checking a path and writing to it are
  separate steps, so pointing the output at a shared or actively rewritten
  directory can race with another process. Write where you control the
  directory.
- **Hash-only integrity.** v0.1 has no signature: if payload, manifest and
  checksums are rewritten together, the archive stays self-consistent. Keep a
  trusted package hash outside the archive.
- **No platform integration.** No connector, sync, GUI or background service; no
  real ChatGPT / Claude / Gemini / Cursor / Coze / Dify / MCP export has been
  tested end to end.
- **Copies, not conversions.** Content is preserved byte-for-byte. The tool does
  not summarise memories, infer traits, or claim behaviour equivalence across
  models.
- **No bundle yet.** The installable `.skill` package is not shipped in this
  repository; run the CLI from source.

Audit details and release readiness are tracked in
[docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md) and [audit/](audit/).

## Documentation

| Document | Contents |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | Install, first run, macOS path notes |
| [docs/VERIFY.md](docs/VERIFY.md) | Verifying a package or a release |
| [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Full limitations list |
| [docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md) | Release readiness |
| [references/FORMAT.md](references/FORMAT.md) | Package format contract |
| [references/SECURITY.md](references/SECURITY.md) | Security rules and trust boundary |
| [references/test-report.md](references/test-report.md) | Test evidence |
| [audit/](audit/) | Audit status and evidence |

## License

MIT No Attribution (MIT-0). See [LICENSE](LICENSE) and
[assets/LICENSE](assets/LICENSE).
