# dist/ — release artifacts

## Contents

| File | Size | SHA-256 | Meaning |
|---|---|---|---|
| `project_20261127_101507.tar.gz` | 32,372 bytes | `983fae89c62955f983b070419477a3aa65d1b2b1494736e89c2118bdc110f4d0` | Source drop exactly as received (`projects/workspace-easy-pack/…`). Stored unmodified for provenance; the unpacked tree is the repository root. |

## Missing artifact

`workspace-easy-pack.skill` — the installable bundle — is **not here** and has
**not** been verified. Expected identity:

| Field | Expected value | Observed |
|---|---|---|
| Size | 38,803 bytes | not found |
| SHA-256 | `438fd7ad3e53a229e522684f3097a3a90948109a9ab7fbd963c9075576528de3` | not found |

The source drop above is a *different* artifact: different size, different hash.
It must not be renamed or substituted for the bundle.

## Adding the bundle later

1. Place the real `workspace-easy-pack.skill` in this directory.
2. Confirm `stat` size and `shasum -a 256` match the table above.
3. Append its hash to `../SHA256SUMS.txt`.
4. Update `README.md`, `docs/VERIFY.md` and `docs/RELEASE_STATUS.md`, then tag.

Note: `../.gitignore` deliberately re-includes `dist/*.gz` and `dist/*.skill`,
because the upstream `.gitignore` that shipped with the source ignored `dist`,
`*.skill`, `*.gz` and `*.zip`.
