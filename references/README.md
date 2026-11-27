# WorkspaceEasyPack v0.1

**Pack your AI workspace. Take it anywhere.**

WorkspaceEasyPack is a local Agent Skill for exporting, inspecting, restoring, and verifying AI workspace assets. It uses standard ZIP, JSON, Markdown, and SHA-256 without a cloud service or a required third-party Python package.

## Scope

The Skill preserves user profiles, agent instructions, memories, project material, workflows, Skills and plugins, and tool configuration. Original files are retained under `source/`; recognized content also receives deterministic category copies. Unknown files remain in the archive. Credential screening is heuristic and best-effort: suspected secrets are excluded in full and recorded without secret values, but you must review `excluded_files` and the archive contents before sharing.

## Install and Run

Load the distributed `workspace-easy-pack.skill` in an Agent Skills-compatible host. From the unpacked Skill directory, invoke the CLI with Python 3.9 or later:

```bash
python scripts/workspace_easy_pack.py export --input ./workspace --output ./workspace-easy-pack.zip
python scripts/workspace_easy_pack.py inspect --package ./workspace-easy-pack.zip --report ./inspection.md
python scripts/workspace_easy_pack.py restore --package ./workspace-easy-pack.zip --target ./restored-workspace
python scripts/workspace_easy_pack.py verify --package ./workspace-easy-pack.zip --restored ./restored-workspace --report ./verification.json
```

Repeat `--input` for multiple files, directories, or ZIP exports. Export and report outputs refuse replacement unless `--overwrite` is explicitly supplied. Restore always requires a target path that does not exist.

## Test

```bash
python scripts/test_workspace_easy_pack.py
```

The tests execute real local CLI operations against synthetic fixtures. They do not establish compatibility with real hosted platform exports or APIs. See `references/test-report.md` for executed results and `references/FORMAT.md` for the package contract.

## Security and Limits

Only explicitly supplied inputs are read. Imported scripts are never executed. Unsafe ZIP paths, links, special files, encrypted entries, excessive expansion, and Unicode-normalization path collisions are rejected. Output paths containing symbolic link components are refused instead of being followed. Restored-directory verification reports missing, modified, and unexpected files without deleting them. SHA-256 and checksums prove internal consistency, not authenticity: keep a trusted package hash outside the archive for high-value backups. Secret detection is risk reduction, not a guarantee. Review archives before sharing and recreate credentials directly in the target environment.

No platform connector, cloud sync, GUI, background service, or behavior-equivalence claim is included in v0.1.

## License

MIT-0. See `assets/LICENSE` in the Skill distribution.
