# Verifying a release or a package

Three different things can be verified. Keep them separate.

## 1. Verify the distributed source tree (this repository)

```bash
cd workspace-easy-pack
shasum -a 256 -c SHA256SUMS.txt     # macOS / BSD
sha256sum -c SHA256SUMS.txt         # GNU coreutils
```

`SHA256SUMS.txt` covers the Skill source files as published in release `0.1.0`.
A single mismatch means the tree differs from the published release.

## 2. Verify a generated workspace package

```bash
python3 scripts/workspace_easy_pack.py verify \
  --package ./workspace-easy-pack.zip --report ./verification.json
```

Checks the manifest, `checksums.sha256`, file paths, counts, sizes and the actual
SHA-256 of every payload. Add `--restored <dir>` to also diff a restored tree
(`missing_files`, `size_mismatches`, `hash_mismatches`, `unexpected_files`).
Exit code `1` means integrity failures were reported; `0` means clean.

## 3. Verify the `.skill` distribution bundle

Expected identity, supplied out of band:

| Field | Expected value |
|---|---|
| Size | 38,803 bytes |
| SHA-256 | `438fd7ad3e53a229e522684f3097a3a90948109a9ab7fbd963c9075576528de3` |

```bash
stat -f '%z bytes' workspace-easy-pack.skill      # macOS
stat -c '%s bytes' workspace-easy-pack.skill      # Linux
shasum -a 256 workspace-easy-pack.skill
```

Current status: **the bundle is not present in this repository and has not been
verified.** An earlier attempt to locate `workspace-easy-pack.skill` on the
authoring machine found only the source drop
`dist/project_20261127_101507.tar.gz`
(32,372 bytes, SHA-256 `983fae89c62955f983b070419477a3aa65d1b2b1494736e89c2118bdc110f4d0`),
which is a different artifact with a different size and hash. Do not republish a
bundle until its hash matches the table above.

## Trust boundary

- SHA-256 and `checksums.sha256` prove that bytes and recorded hashes agree.
- They cannot prove authenticity if payload, `manifest.json` and
  `checksums.sha256` were modified together and all hashes recomputed.
- v0.1 has no external signature. For high-value backups, store the package hash
  outside the archive and compare before restoring.
