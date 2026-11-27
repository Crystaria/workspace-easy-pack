# Release status — 0.1.0

_Last reviewed: 2026-11-27_

## Verdict

**Pre-release. Not ready for a "stable" tag, and not ready to publish a binary
`.skill` bundle.** The source tree is publishable for review.

The second independent review returned **PARTIAL (conditional pass)** — see
[Audit outcome](#audit-outcome).

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
| Round-2 independent audit | **PARTIAL** | H1/M1/M2/L1 fixes verified; M3 documentation consistent with implementation; open N1 (Medium), N2 (Low), N3 (Low) |
| Real-platform testing | **not done** | synthetic fixtures only |
| macOS conformance | **fails as shipped** | `/var` + `/tmp` symlinks rejected by `safe_user_path` |
| Secret scan of committed files | done | hits are synthetic fixtures only |

## Audit outcome

Second independent review: **PARTIAL (conditional pass)**.

| Item | Result |
|---|---|
| H1 — symlink output escape | fix verified |
| M1 — credential detection gaps | fix verified |
| M2 — restored extra files invisible | fix verified |
| M3 — integrity trust boundary documentation | documentation matches implementation |
| L1 — Unicode NFC/NFD collisions | fix verified |

Open items from that review:

| ID | Severity | Finding |
|---|---|---|
| N1 | Medium | TOCTOU race under specific concurrent conditions. |
| N2 | Low | Credential detection is heuristic and still misses some formats (for example `github_pat_`, `sk_live_`, `npm_`). |
| N3 | Low | macOS system symlinks (`/var`, `/tmp`) can make operations fail. |

The review therefore does not constitute a full pass. Report texts are not
archived in this repository; only this outcome summary is recorded, and no
report content has been reconstructed. See [../audit/README.md](../audit/README.md).

## Blockers before publishing a bundle

1. Obtain `workspace-easy-pack.skill` and confirm 38,803 bytes /
   `438fd7ad3e53a229e522684f3097a3a90948109a9ab7fbd963c9075576528de3`.
2. Resolve or explicitly accept N1 (TOCTOU race under specific concurrent
   conditions). The current status is a conditional pass, not a full pass.
3. Archive the round-1 and round-2 audit report texts in `audit/` if they can be
   obtained. The PARTIAL outcome is recorded here, but no report text exists in
   this repository, so the claim cannot be traced back to a document.
4. Decide the macOS policy (N3): document "use real paths", or change
   `safe_user_path` to tolerate the OS-provided `/var` and `/tmp` links. Changing
   it is a behaviour change and needs its own review.

## What is explicitly out of scope for 0.1.0

Platform connectors, cloud sync, GUI, background service, external signatures /
key management, AI-interpreted payloads, and any behaviour-equivalence claim.
