# Known limitations — v0.1.0

Every item below is a documented boundary, not a bug report. Where a limit was
observed on a specific machine it is marked **[verified]** or **[unverified]**.

## Integrity

1. **Hash-only integrity.** SHA-256 and `checksums.sha256` detect disagreement
   between file bytes and recorded hashes. If payload, `manifest.json` and
   `checksums.sha256` are modified together and all hashes recomputed, the
   archive stays internally self-consistent. v0.1 has no signature or key
   management. → keep a trusted package hash outside the archive.
2. **No provenance for the `.skill` bundle.** The bundle's expected size
   (38,803 bytes) and SHA-256
   (`438fd7ad…6528de3`) were supplied out of band and have **not** been
   verified, because the file was absent from the provided source directory.
   **[verified: file missing]**

## Credential handling

3. **Heuristic screening.** Patterns cover the documented shapes (OpenAI `sk-`,
   GitHub `gh*_`, AWS `AKIA`, Slack `xox*`, Google `AIza`, Hugging Face `hf_`,
   GitLab `glpat-`, xAI/Grok `xai-`, Groq `gsk_`, three-segment JWTs). Other
   formats, bespoke secrets and sensitive non-credential information are not
   guaranteed to be detected. Always review `excluded_files` and the archive
   before sharing.
4. **Exclusion is whole-file.** A suspect file is dropped in full; there is no
   partial redaction and no secret value is ever written into a report.

## Platform coverage

5. **No real platform conformance.** No genuine ChatGPT, Claude, Gemini, Cursor,
   Coze, Dify or MCP export/API was exercised. Recognising a platform config file
   means "manual review required", never "automatically converted".
   **[unverified]**
6. **Windows not verified.** Path, case-folding and normalization behaviour was
   never executed on Windows. **[unverified]**
7. **macOS only partially usable.** `safe_user_path` rejects any output path with
   a symlinked component, and macOS exposes `/var` and `/tmp` as symlinks. As a
   result the stock test suite fails on macOS (`33/33` failing with
   `unsafe_output_path: path component '/var' is a symbolic link`) and any
   `--output` / `--target` / `--report` under `TMPDIR` is refused. Use real paths
   under your home directory, or set `TMPDIR` to a real directory.
   **[verified on darwin, Python 3.14.2, 2026-11-27]**
8. **Scale limits are untested at the edges.** 20,000 entries / 128 MiB per file
   / 512 MiB total / 1000:1 ratio are enforced, but behaviour near those limits
   and under memory pressure was not measured. **[unverified]**

## Fidelity and scope

9. **No AI interpretation.** v0.1 copies bytes deterministically; memories are
   not summarized and no traits are inferred. Restored content is not
   re-expressed for the target model.
10. **No behaviour equivalence.** Restoring a workspace does not reproduce how
    another host or model behaved. API-only platform state is absent unless the
    user supplies an export.
11. **No connectors, sync, GUI or service.** None exist in v0.1.
12. **Restore never overwrites.** An existing target directory is refused by
    design; there is no merge mode.
13. **Archive identity is preserved literally.** Names that collide after Unicode
    NFC normalization or case folding are rejected (`duplicate_zip_path`,
    `path_conflict`) rather than silently renamed.

## Release process

14. **Audit status.** The first independent audit's findings H1, M1, M2, M3 and
    L1 are addressed in this build, but the **second independent audit has not
    been completed**, and the audit reports themselves are not in this
    repository. See [../audit/README.md](../audit/README.md).
15. **Synthetic fixtures only.** All tests run on generated data; token strings
    in `scripts/test_workspace_easy_pack.py` are deliberate placeholders and are
    not usable credentials.
