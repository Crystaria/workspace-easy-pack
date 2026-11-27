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

## Round 2 — independent re-audit

Status: **not started / not received.**

`references/test-report.md` states verbatim: "Status: **pending independent
re-audit** … Passing these tests is not a substitute for a new independent
security review."

Do not claim a clean second audit until a report exists in this directory.

## What can be honestly said today

> The 0.1.0 source addresses the five findings from the first independent audit,
> with 33 passing local tests on synthetic fixtures, and is awaiting its second
> independent audit.
