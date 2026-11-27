# WorkspaceEasyPack v0.1 Test Report — Post-Audit Fix Build

Status: **pending independent re-audit**. This build addresses findings H1, M1, M2, M3, and L1 from the independent technical audit. Passing these tests is not a substitute for a new independent security review.

> Note added later: a second independent review has been completed. Its outcome is recorded in `audit/README.md`; the text above remains the original post-fix test record.

## Contents

- Result
- Fix Mapping
- A. Original Tests (17)
- B. New Regression Tests (16)
- C. Adversarial Retests After Fixes
- D. Synthetic or Simulated Scenarios
- E. NOT VERIFIED
- Reproduction

## Result

- Final local regression: **PASS**
- Tests run: **33** = original **17** + new **16**
- Failures: **0**; Errors: **0**
- Final observed run: **Ran 33 tests in 4.698s — OK**
- Environment: **Python 3.13.13, Linux, local filesystem**
- Execution command: `python3 scripts/test_workspace_easy_pack.py` from the Skill directory
- Arithmetic check: 33 run − 0 failures − 0 errors = 33 passed; 17 + 16 = 33. Consistent.

## Fix Mapping

| Finding | Code location | Change | Test evidence |
|---|---|---|---|
| H1 symlink output escape | `safe_user_path` (new) in `scripts/workspace_easy_pack.py`; applied in `command_export` (`--output`), `command_restore` (`--target`), `command_verify` (`--restored`), `write_report` (`--report`) | Every existing component of the original path, including parents, is lstat-checked before resolution; absolute/relative/broken/intermediate symlinks are rejected with `unsafe_output_path`, exit 2; nothing is created at link destinations | Tests 18–24 + adversarial retests H1a/H1b |
| M1 credential detection gaps | `TOKEN_RES` in `scripts/workspace_easy_pack.py` | Added Google `AIza`, Hugging Face `hf_`, GitLab `glpat-`, xAI/Grok `xai-`, Groq `gsk_`, and three-segment JWT (`eyJ...`) patterns; values never appear in manifest, exclusion records, or reports; templates and value-less docs stay included | Tests 25–26 + adversarial retest C1 |
| M2 restored extra files invisible | `command_verify` and `markdown_report` in `scripts/workspace_easy_pack.py` | Expected restore set (manifest payloads + `manifest.json`, `checksums.sha256`, `AGENT_BOOTSTRAP.md`, `reports/restore-report.*`) is diffed against the actual directory; new `unexpected_files`, `expected_file_count`, `actual_file_count`; any difference fails restoration verification; files are never deleted; JSON and Markdown reports both list paths | Tests 27–30 |
| M3 integrity trust boundary undocumented | `references/FORMAT.md` (Integrity Trust Boundary), `references/SECURITY.md`, `SKILL.md`, `references/README.md` | Documentation only, no code change: SHA-256/checksums detect file-record inconsistency; jointly recomputed payload+manifest+checksums remain self-consistent and cannot prove authenticity; no external signature in v0.1; store a trusted package hash outside the archive for high-value backups | Documentation review; adversarial retest B2 confirms inconsistent tampering is still detected |
| L1 Unicode NFC/NFD collisions | `safe_zip_members` (NFC + casefold keys) and new `check_archive_path_collisions` called by `command_export` before manifest creation in `scripts/workspace_easy_pack.py` | Colliding paths are rejected with explicit `duplicate_zip_path` / `path_conflict` errors; original names and source records are preserved; normal Unicode names are accepted | Tests 31–33 |

## A. Original Tests (Unchanged Assertions, 17/17 PASS)

| Test | Verified behavior | Result |
|---|---|---|
| 01 | Multiple categories exported; byte-for-byte originals | PASS |
| 02 | ZIP creation, reopening, root metadata, CRC self-test | PASS |
| 03 | Inspect categories and dependency declarations | PASS |
| 04 | Restore outputs; imported script is not executed | PASS |
| 05 | Every manifest and checksum SHA-256 matches actual bytes | PASS |
| 06 | Payload removed from a copied archive is detected | PASS |
| 07 | Synthetic API credential and private key excluded; placeholder template kept | PASS |
| 08 | Equal-content files preserved; duplicate groups reported | PASS |
| 09 | Invalid ZIP input rejected with structured error | PASS |
| 10 | `../` ZIP path traversal rejected; no escape file written | PASS |
| 11 | Synthetic ChatGPT/MCP configuration marked for manual configuration | PASS |
| 12 | Restored files verify; later deletion detected | PASS |
| 13 | Existing restore target refused; sentinel unchanged | PASS |
| 14 | Unclassified text and binary files preserved as unknown originals | PASS |
| 15 | Inspect writes Markdown report; Verify writes JSON report | PASS |
| 16 | Safe existing ZIP imported, traced with `!/`, reinspected | PASS |
| 17 | Modified payload bytes produce manifest-hash and checksum mismatches | PASS |

## B. New Regression Tests (16/16 PASS)

| Test | Finding | Verified behavior | Result |
|---|---|---|---|
| 18 | H1 | Restore target = absolute broken symlink: refused, link destination not created, link itself untouched | PASS |
| 19 | H1 | Restore target = relative broken symlink via `cwd`: refused, no destination created | PASS |
| 20 | H1 | Restore target under a symlinked parent directory: refused, real parent stays empty | PASS |
| 21 | H1 | Export output = broken symlink and output under symlinked parent: both refused, no escape writes | PASS |
| 22 | H1 | `inspect --report` and `verify --report` = broken symlinks: refused, no report created at destination | PASS |
| 23 | H1 | `verify --restored` = symlink to real directory and broken symlink: both refused, nothing created | PASS |
| 24 | H1 | Normal export/restore/report/verify paths still succeed; clean restore verifies with zero unexpected files | PASS |
| 25 | M1 | Five synthetic token types (Google, Hugging Face, JWT, GitLab, Grok) excluded with `credential_shaped_value`; no token value appears in any package member | PASS |
| 26 | M1 | Credential-hygiene documentation without values and `.env.example` placeholders remain included | PASS |
| 27 | M2 | Clean restored directory: `passed`, empty `unexpected_files`/`missing_files`, expected count equals actual count | PASS |
| 28 | M2 | Deleted expected file: `failed`, path listed in `missing_files`, no false unexpected entries | PASS |
| 29 | M2 | Modified restored file: `failed`, path listed in `hash_mismatches` | PASS |
| 30 | M2 | Extra file: `failed`, `unexpected_files` lists it, package integrity stays `valid`, extra file not deleted, JSON and Markdown reports both show the difference | PASS |
| 31 | L1 | NFC-only, NFD-only, and CJK file names export successfully with original names preserved | PASS |
| 32 | L1 | NFC+NFD collision in one ZIP: `duplicate_zip_path`, explicit Unicode error, no output archive | PASS |
| 33 | L1 | NFC+NFD collision in a directory input: `path_conflict`, explicit Unicode error, no output archive | PASS |

## C. Adversarial Retests After Fixes (Synthetic Data, Isolated `/tmp`)

Independent subprocess retests against the audit's original attack shapes:

| Retest | Result |
|---|---|
| H1a: restore with broken symlink target (original exploit shape) | Refused: `unsafe_output_path`, exit 2, escape location not created |
| H1b: export with broken symlink output | Refused: `unsafe_output_path`, exit 2, escape location not created |
| Traversal variants `/etc/x`, `C:/x`, `a/../b` | All refused: `unsafe_zip_path`, no output archive |
| ZIP symlink entry | Refused: `unsafe_zip_link` |
| Encrypted-flag ZIP entry | Refused: `encrypted_zip` |
| B1 hidden payload absent from manifest | `invalid`; listed in `unexpected_payload` |
| B2 forged manifest hash | `invalid`; exact path in `hash_mismatches` |
| C1 Google/Hugging Face/JWT variants | Excluded; no token value present in the package |

All retests passed their expected secure outcome. No residual filesystem escape was observed.

## D. Synthetic or Simulated Scenarios

All workspaces, platform names, credentials, tokens, JWTs, symlinks, Unicode names, malicious archives, and imported scripts were synthetic and created only inside temporary test directories. Credential strings are unusable. ChatGPT/MCP examples verify recognition and reporting logic, not real platform compatibility.

## E. NOT VERIFIED

- Real ChatGPT, Claude, Gemini, Cursor, Coze, Dify, MCP host, or other platform exports and APIs.
- Windows and macOS behavior, including APFS/NTFS-specific normalization and case handling (collision inputs are now rejected explicitly, but no non-Linux run was performed).
- Very large archives near the 128 MiB/512 MiB limits and performance under resource pressure.
- Detection of every credential format: screening remains heuristic and best-effort.
- Authenticity against fully self-consistent malicious repackaging: out of scope for hash-only verification; see the Integrity Trust Boundary in `references/FORMAT.md` and `references/SECURITY.md`.

## Reproduction

```bash
python scripts/test_workspace_easy_pack.py
```

The suite creates and removes its own temporary directories. It needs no network, third-party packages, credentials, or writes to the packaged source files.
