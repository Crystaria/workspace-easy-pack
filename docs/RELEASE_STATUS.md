# Release status — 0.1.0

_Last reviewed: 2026-11-27_

## Verdict

**Pre-release. Not ready for a "stable" tag, and not ready to publish a binary
`.skill` bundle.** The source tree is publishable for review.

## Checklist

| Item | State | Notes |
|---|---|---|
| Version recorded | done | `VERSION` = `0.1.0`; `PACKAGE_VERSION` = `0.1.0`; `SCHEMA_VERSION` = `1.0` |
| Full source present | done | `SKILL.md`, `scripts/`, `references/`, `assets/` |
| Docs present | done | `README.md`, `docs/INSTALL.md`, `docs/VERIFY.md`, `docs/KNOWN_LIMITATIONS.md` |
| Checksums of source tree | done | `SHA256SUMS.txt` |
| License | done | MIT-0 (`LICENSE`, `assets/LICENSE`) |
| `.skill` bundle included | **blocked** | file absent from the provided source directory |
| `.skill` size + SHA-256 verified | **blocked** | expected 38,803 B / `438fd7ad…6528de3`, unverified |
| Round-1 audit report included | **missing** | only referenced by `references/test-report.md` |
| Round-2 independent audit | **pending** | `references/test-report.md` states "pending independent re-audit" |
| Real-platform testing | **not done** | synthetic fixtures only |
| macOS conformance | **fails as shipped** | `/var` + `/tmp` symlinks rejected by `safe_user_path` |
| Secret scan of committed files | done | hits are synthetic fixtures only |

## Blockers before publishing a bundle

1. Obtain `workspace-easy-pack.skill` and confirm 38,803 bytes /
   `438fd7ad3e53a229e522684f3097a3a90948109a9ab7fbd963c9075576528de3`.
2. Obtain or reconstruct the round-1 audit report and attach the round-2 report
   once it exists, so the "pending re-audit" status can be closed.
3. Decide the macOS policy: document "use real paths", or change
   `safe_user_path` to tolerate the OS-provided `/var` and `/tmp` links. Changing
   it is a behaviour change and needs its own review.

## What is explicitly out of scope for 0.1.0

Platform connectors, cloud sync, GUI, background service, external signatures /
key management, AI-interpreted payloads, and any behaviour-equivalence claim.
