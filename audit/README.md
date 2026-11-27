# Audit status

This directory holds audit evidence only. **No audit report text has been
invented or reconstructed here.**

## Round 1 — independent technical audit

Status: **partially represented.**

- Findings raised: `H1` symlink output escape, `M1` credential-detection gaps,
  `M2` restored extra files invisible, `M3` integrity trust boundary
  undocumented, `L1` Unicode NFC/NFD path collisions.
- All five were fixed in this build. The fix mapping, code locations and
  test evidence are in [`round-1-fix/test-report.md`](round-1-fix/test-report.md)
  (same content as `../references/test-report.md`).
- **The round-1 audit report document itself is not in this repository** — it
  was not present in the provided source directory. Add it here (for example
  `round-1/audit-report.md`) before describing this repository as
  "audit-complete".

## Round 2 — independent review

Status: **completed — PARTIAL (conditional pass).**

| Item | Result |
|---|---|
| H1 — symlink output escape | fix verified |
| M1 — credential detection gaps | fix verified |
| M2 — restored extra files invisible | fix verified |
| M3 — integrity trust boundary documentation | documentation matches implementation |
| L1 — Unicode NFC/NFD collisions | fix verified |
| N1 — Medium | TOCTOU race under specific concurrent conditions |
| N2 — Low | Credential detection stays heuristic and still misses some formats (`github_pat_`, `sk_live_`, `npm_`, others) |
| N3 — Low | macOS system symlinks (`/var`, `/tmp`) can make operations fail |

**This is not a full pass.** N1, N2 and N3 remain open and are tracked as items
16, 3 and 7 in [`../docs/KNOWN_LIMITATIONS.md`](../docs/KNOWN_LIMITATIONS.md).

**The round-2 report text is not in this repository.** The table above is an
outcome summary only — no report content was reconstructed, and no report file
should be added here unless the original can be obtained.

## What can be honestly said today

> The 0.1.0 source fixes the five findings from the first independent audit
> (H1, M1, M2, M3, L1). The second independent review returned **PARTIAL
> (conditional pass)**: those fixes were verified, and N1 (Medium), N2 (Low) and
> N3 (Low) remain open. Local tests are 33 passing on synthetic fixtures in the
> recorded Linux environment.
