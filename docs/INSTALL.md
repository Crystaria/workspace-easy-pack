# Install and run

## Requirements

- Python 3.9 or later. Only the standard library is used — no `pip install`.
- A writable output directory that does **not** live under a symbolic link
  (see [macOS note](#macos-note)).

## Option A — use the repository directly

```bash
git clone <this-repo> && cd workspace-easy-pack
python3 -VV          # expect 3.9+
python3 scripts/workspace_easy_pack.py --help
```

## Option B — install as an Agent Skill

The Skill distribution is a single `workspace-easy-pack.skill` bundle. Load it in
an Agent Skills–compatible host, then run the CLI from the unpacked Skill
directory:

```bash
python3 scripts/workspace_easy_pack.py export --input ./workspace --output ./workspace-easy-pack.zip
```

The `.skill` bundle is not committed here yet; see
[../dist/README.md](../dist/README.md) for its expected size and SHA-256.

## First run walkthrough

```bash
# 1. Export — repeat --input for every explicit source
python3 scripts/workspace_easy_pack.py export \
  --input ./projects \
  --input ./memories.jsonl \
  --output ./workspace-easy-pack.zip \
  --source-platform "unknown" --source-agent "unknown"

# 2. Inspect before sharing (Markdown or .json)
python3 scripts/workspace_easy_pack.py inspect \
  --package ./workspace-easy-pack.zip --report ./inspection.md

# 3. Restore into a path that must not exist yet
python3 scripts/workspace_easy_pack.py restore \
  --package ./workspace-easy-pack.zip \
  --target ./restored-workspace \
  --target-platform "generic" --target-agent "new-agent"

# 4. Verify package + restored tree
python3 scripts/workspace_easy_pack.py verify \
  --package ./workspace-easy-pack.zip \
  --restored ./restored-workspace --report ./verification.json
```

Then read `AGENT_BOOTSTRAP.md` and `reports/restore-report.*` in the restored
workspace and decide **manually** which instructions, Skills, workflows and
tools to adopt. Recreate credentials in the target environment; never copy them
out of an archive.

## Safety rules in force

- Only `--input` paths are read. No directory scanning, no external accounts.
- Existing outputs are never replaced without an explicit `--overwrite`.
- Restore never writes into an existing target directory.
- Imported scripts and configuration are treated as data and never executed.
- Output paths containing symlink components are rejected (`unsafe_output_path`).

## macOS note

On macOS, `tempfile.gettempdir()` returns `/var/folders/...` and both `/var` and
`/tmp` are symbolic links. Because `safe_user_path` rejects *any* symlinked path
component, commands run under those paths fail with:

```json
{"error": {"code": "unsafe_output_path", "message": "--output is unsafe: path component '/var' is a symbolic link; refusing to follow it."}, "status": "error"}
```

Use real paths such as `/Users/<you>/Documents/work/...` instead, and set
`TMPDIR` to a real directory when running the test suite:

```bash
mkdir -p "$HOME/wep-tmp" && TMPDIR="$HOME/wep-tmp" python3 scripts/test_workspace_easy_pack.py
```

## Uninstall

Nothing is installed outside the repository directory. Delete the clone and any
generated archives you no longer need. The tool never touches the paths you fed
to `--input`.
