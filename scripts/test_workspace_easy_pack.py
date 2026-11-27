#!/usr/bin/env python3
"""Real local CLI tests using synthetic WorkspaceEasyPack fixtures."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "workspace_easy_pack.py"


class WorkspaceEasyPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="workspace-easy-pack-test-"))
        self.fixture = self.temp / "fixture"
        self.package = self.temp / "workspace-easy-pack.zip"
        self.secret_value = "sk-live-SYNTHETIC1234567890abcdef"
        self._create_fixture()
        result = self.run_cli(
            "export", "--input", str(self.fixture), "--output", str(self.package),
            "--source-platform", "synthetic-platform", "--source-agent", "synthetic-agent",
        )
        self.export_result = result

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def _create_fixture(self):
        files = {
            "profile/USER_PROFILE.md": "# User Profile\n\nPrefers concise technical English.\n",
            "agent/AGENT_IDENTITY.md": "# Agent Identity\n\nA careful research collaborator.\n",
            "agent/AGENT_INSTRUCTIONS.md": "# Instructions\n\nCite sources and state uncertainty.\n",
            "agent/WORKING_PROTOCOLS.md": "# Protocols\n\nConfirm destructive actions.\n",
            "memory/diary/2025-01-01.md": "# Diary\n\nStarted the migration project.\n",
            "memory/semantic-memory/facts.jsonl": '{"fact":"User prefers reversible migrations","timestamp":"2025-01-01T00:00:00Z"}\n',
            "memory/relationships/people.md": "# Relationships\n\nAlex owns the example project.\n",
            "projects/demo/PROGRESS.md": "# Progress\n\nPrototype complete.\n",
            "projects/demo/DECISIONS.md": "# Decisions\n\nUse open file formats.\n",
            "workflows/research/WORKFLOW.md": "# Workflow\n\nCollect, compare, cite.\n",
            "skills/demo/SKILL.md": "---\nname: demo\ndescription: Synthetic fixture\n---\n\n# Demo\n",
            "skills/demo/scripts/never_execute.py": f"from pathlib import Path\nPath({str(self.temp / 'IMPORTED_SCRIPT_EXECUTED')!r}).write_text('bad')\n",
            "tools/requirements.txt": "requests==2.32.3\n",
            "tools/mcp.json": '{"command":"example-server","env":{"API_KEY":"${API_KEY}"}}\n',
            "tools/.env.example": "API_KEY=${API_KEY}\nPASSWORD=\n",
            "platform/chatgpt/settings.json": '{"model":"synthetic","platform_only":true}\n',
            "misc/README.txt": "Unclassified but valuable original material.\n",
            "projects/demo/duplicate-a.txt": "Duplicate content must remain traceable.\n",
            "workflows/duplicate-b.txt": "Duplicate content must remain traceable.\n",
        }
        for relative, content in files.items():
            path = self.fixture / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        secret = self.fixture / "private" / "secrets.env"
        secret.parent.mkdir(parents=True, exist_ok=True)
        secret.write_text(f"API_KEY={self.secret_value}\n", encoding="utf-8")
        private_key = self.fixture / "private" / "id_rsa.pem"
        private_key.write_text("-----BEGIN PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----\n", encoding="utf-8")
        (self.fixture / "misc" / "data.bin").write_bytes(b"\x00\x01\x02\xff")

    def run_cli(self, *args, expected=0, cwd=None):
        completed = subprocess.run(
            [sys.executable, str(CLI), *args], text=True, capture_output=True, check=False, cwd=cwd,
        )
        self.assertEqual(completed.returncode, expected, f"stdout={completed.stdout}\nstderr={completed.stderr}")
        self.assertTrue(completed.stdout.strip(), "CLI must emit JSON on stdout")
        return json.loads(completed.stdout)

    def manifest(self, package=None):
        with zipfile.ZipFile(package or self.package) as archive:
            return json.loads(archive.read("manifest.json").decode("utf-8"))

    def test_01_exports_multiple_categories_and_retains_originals(self):
        self.assertEqual(self.export_result["status"], "success")
        manifest = self.manifest()
        categories = manifest["statistics"]["category_counts"]
        for category in ("profile", "agent", "memory", "projects", "workflows", "skills", "tools", "unknown"):
            self.assertGreater(categories.get(category, 0), 0)
        originals = [entry for entry in manifest["files"] if entry["file_type"] == "original"]
        with zipfile.ZipFile(self.package) as archive:
            for entry in originals:
                relative = entry["source"].split(":", 1)[1]
                self.assertEqual(archive.read(entry["path"]), (self.fixture / relative).read_bytes())

    def test_02_zip_is_generated_and_reopens_with_valid_crc(self):
        self.assertTrue(zipfile.is_zipfile(self.package))
        with zipfile.ZipFile(self.package) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("manifest.json", archive.namelist())
            self.assertIn("checksums.sha256", archive.namelist())

    def test_03_inspect_recognizes_files_and_dependencies(self):
        result = self.run_cli("inspect", "--package", str(self.package))
        report = result["report"]
        self.assertEqual(report["package_status"], "valid")
        self.assertGreaterEqual(len(report["summary"]["categories"]), 8)
        self.assertTrue(report["dependencies"])
        self.assertEqual(report["dependencies"][0]["status"], "target_environment_check_required")

    def test_04_restore_generates_workspace_without_executing_scripts(self):
        target = self.temp / "restored"
        result = self.run_cli(
            "restore", "--package", str(self.package), "--target", str(target),
            "--target-platform", "generic-target",
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue((target / "AGENT_BOOTSTRAP.md").is_file())
        self.assertTrue((target / "RESTORE_GUIDE.md").is_file())
        self.assertTrue((target / "profile" / "USER_PROFILE.md").is_file())
        self.assertTrue((target / "reports" / "restore-report.json").is_file())
        self.assertFalse((self.temp / "IMPORTED_SCRIPT_EXECUTED").exists())

    def test_05_sha256_manifest_and_checksums_are_correct(self):
        with zipfile.ZipFile(self.package) as archive:
            manifest = self.manifest()
            for entry in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), entry["sha256"])
            for line in archive.read("checksums.sha256").decode("utf-8").splitlines():
                digest, path = line.split("  ", 1)
                self.assertEqual(hashlib.sha256(archive.read(path)).hexdigest(), digest)

    def test_06_verify_detects_missing_file(self):
        broken = self.temp / "missing-file.zip"
        with zipfile.ZipFile(self.package) as source:
            manifest = self.manifest()
            removed = next(entry["path"] for entry in manifest["files"] if entry["file_type"] == "original")
            with zipfile.ZipFile(broken, "w") as target:
                for info in source.infolist():
                    if info.filename != removed:
                        target.writestr(info, source.read(info.filename))
        result = self.run_cli("verify", "--package", str(broken), expected=1)
        self.assertEqual(result["status"], "failed")
        self.assertIn(removed, result["report"]["integrity"]["missing_payload"])

    def test_07_sensitive_credentials_are_excluded_without_value_leakage(self):
        manifest = self.manifest()
        reasons = [entry["reason"] for entry in manifest["excluded_files"]]
        self.assertIn("embedded_credential", reasons)
        self.assertIn("sensitive_file_type", reasons)
        with zipfile.ZipFile(self.package) as archive:
            for name in archive.namelist():
                data = archive.read(name)
                self.assertNotIn(self.secret_value.encode(), data)
                self.assertNotIn(b"-----BEGIN PRIVATE KEY-----\nsynthetic", data)
            self.assertTrue(any(name.endswith("tools/.env.example") for name in archive.namelist()))

    def test_08_duplicates_are_preserved_and_reported(self):
        result = self.run_cli("inspect", "--package", str(self.package))
        duplicates = result["report"]["duplicates"]
        self.assertTrue(any(group["count"] >= 2 for group in duplicates))
        original_paths = [entry["path"] for entry in self.manifest()["files"] if entry["file_type"] == "original"]
        self.assertTrue(any(path.endswith("duplicate-a.txt") for path in original_paths))
        self.assertTrue(any(path.endswith("duplicate-b.txt") for path in original_paths))

    def test_09_invalid_zip_is_rejected(self):
        invalid = self.temp / "invalid.zip"
        invalid.write_bytes(b"not a zip archive")
        output = self.temp / "invalid-export.zip"
        result = self.run_cli("export", "--input", str(invalid), "--output", str(output), expected=2)
        self.assertEqual(result["error"]["code"], "invalid_zip")
        self.assertFalse(output.exists())

    def test_10_zip_slip_is_rejected_without_writing_escape_file(self):
        malicious = self.temp / "malicious.zip"
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("../escaped.txt", "must not escape")
        output = self.temp / "malicious-export.zip"
        result = self.run_cli("export", "--input", str(malicious), "--output", str(output), expected=2)
        self.assertEqual(result["error"]["code"], "unsafe_zip_path")
        self.assertFalse((self.temp / "escaped.txt").exists())
        self.assertFalse(output.exists())

    def test_11_platform_specific_configuration_is_marked_manual(self):
        result = self.run_cli("inspect", "--package", str(self.package))
        platform = result["report"]["platform_specific"]
        self.assertTrue(any("chatgpt" in item["markers"] for item in platform))
        self.assertTrue(any("mcp" in item["markers"] for item in platform))
        self.assertTrue(all(item["restore_mode"] == "manual_configuration" for item in platform))

    def test_12_verify_restored_workspace_and_detect_post_restore_loss(self):
        target = self.temp / "restored"
        self.run_cli("restore", "--package", str(self.package), "--target", str(target))
        passed = self.run_cli("verify", "--package", str(self.package), "--restored", str(target))
        self.assertEqual(passed["status"], "success")
        manifest = self.manifest()
        victim = next(entry["path"] for entry in manifest["files"] if entry["file_type"] == "original")
        (target / Path(victim)).unlink()
        failed = self.run_cli("verify", "--package", str(self.package), "--restored", str(target), expected=1)
        self.assertIn(victim, failed["report"]["restored"]["missing_files"])

    def test_13_restore_refuses_existing_target(self):
        target = self.temp / "existing"
        target.mkdir()
        sentinel = target / "keep.txt"
        sentinel.write_text("do not overwrite", encoding="utf-8")
        result = self.run_cli("restore", "--package", str(self.package), "--target", str(target), expected=2)
        self.assertEqual(result["error"]["code"], "target_exists")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not overwrite")

    def test_14_unknown_files_are_retained(self):
        manifest = self.manifest()
        unknown = [entry for entry in manifest["files"] if entry["file_type"] == "original" and entry["data_category"] == "unknown"]
        self.assertTrue(any(entry["path"].endswith("misc/README.txt") for entry in unknown))
        self.assertTrue(any(entry["path"].endswith("misc/data.bin") for entry in unknown))

    def test_15_inspect_and_verify_write_real_reports(self):
        inspect_report = self.temp / "inspection.md"
        verify_report = self.temp / "verification.json"
        self.run_cli("inspect", "--package", str(self.package), "--report", str(inspect_report))
        self.run_cli("verify", "--package", str(self.package), "--report", str(verify_report))
        self.assertIn("WorkspaceEasyPack Inspect Report", inspect_report.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(verify_report.read_text(encoding="utf-8"))["status"], "passed")

    def test_16_existing_safe_zip_input_is_imported(self):
        existing = self.temp / "existing-platform-export.zip"
        with zipfile.ZipFile(existing, "w") as archive:
            archive.writestr("memory/diary/imported.md", "Imported diary entry.\n")
            archive.writestr("projects/zip-project/PROGRESS.md", "ZIP project imported.\n")
        output = self.temp / "from-existing-export.zip"
        result = self.run_cli("export", "--input", str(existing), "--output", str(output))
        self.assertEqual(result["original_files"], 2)
        manifest = self.manifest(output)
        self.assertTrue(any("!/" in entry["source"] for entry in manifest["files"] if entry["file_type"] == "original"))
        inspected = self.run_cli("inspect", "--package", str(output))
        self.assertEqual(inspected["report"]["package_status"], "valid")

    def test_17_verify_detects_content_tampering(self):
        tampered = self.temp / "tampered.zip"
        with zipfile.ZipFile(self.package) as source:
            manifest = self.manifest()
            victim = next(entry["path"] for entry in manifest["files"] if entry["file_type"] == "original")
            with zipfile.ZipFile(tampered, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == victim:
                        data += b"tampered"
                    target.writestr(info, data)
        result = self.run_cli("verify", "--package", str(tampered), expected=1)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(item["path"] == victim for item in result["report"]["integrity"]["hash_mismatches"]))
        self.assertTrue(any(item["path"] == victim for item in result["report"]["integrity"]["checksum_mismatches"]))

    # --- H1 regression: symlink output path escape ---

    def _assert_unsafe_path(self, result):
        self.assertEqual(result["error"]["code"], "unsafe_output_path")
        self.assertIn("symbolic link", result["error"]["message"])

    def test_18_restore_rejects_broken_symlink_target(self):
        escape = self.temp / "escape-target"
        link = self.temp / "broken-target-link"
        os.symlink(escape, link)
        result = self.run_cli("restore", "--package", str(self.package), "--target", str(link), expected=2)
        self._assert_unsafe_path(result)
        self.assertFalse(escape.exists(), "no files may be created at the symlink destination")
        self.assertTrue(link.is_symlink(), "the user's symlink must not be removed")

    def test_19_restore_rejects_relative_broken_symlink_target(self):
        work = self.temp / "relative-case"
        work.mkdir()
        os.symlink("missing-inner-target", work / "rel-link")
        result = self.run_cli(
            "restore", "--package", str(self.package), "--target", "rel-link", expected=2, cwd=work,
        )
        self._assert_unsafe_path(result)
        self.assertFalse((work / "missing-inner-target").exists())
        self.assertTrue((work / "rel-link").is_symlink())

    def test_20_restore_rejects_symlink_parent_directory(self):
        real_dir = self.temp / "real-parent"
        real_dir.mkdir()
        link_dir = self.temp / "linked-parent"
        os.symlink(real_dir, link_dir)
        result = self.run_cli(
            "restore", "--package", str(self.package), "--target", str(link_dir / "restored"), expected=2,
        )
        self._assert_unsafe_path(result)
        self.assertEqual(list(real_dir.iterdir()), [], "nothing may be created through the symlinked parent")

    def test_21_export_rejects_symlink_output_paths(self):
        escape = self.temp / "escaped-output"
        link = self.temp / "broken-output-link"
        os.symlink(escape, link)
        result = self.run_cli("export", "--input", str(self.fixture), "--output", str(link), expected=2)
        self._assert_unsafe_path(result)
        self.assertFalse(escape.exists())
        real_dir = self.temp / "real-output-parent"
        real_dir.mkdir()
        link_dir = self.temp / "linked-output-parent"
        os.symlink(real_dir, link_dir)
        result = self.run_cli(
            "export", "--input", str(self.fixture), "--output", str(link_dir / "out.zip"), expected=2,
        )
        self._assert_unsafe_path(result)
        self.assertEqual(list(real_dir.iterdir()), [])

    def test_22_report_options_reject_symlink_paths(self):
        for command in ("inspect", "verify"):
            escape = self.temp / f"escaped-{command}-report"
            link = self.temp / f"broken-{command}-report-link"
            os.symlink(escape, link)
            result = self.run_cli(command, "--package", str(self.package), "--report", str(link), expected=2)
            self._assert_unsafe_path(result)
            self.assertFalse(escape.exists())

    def test_23_verify_rejects_symlink_restored_path(self):
        restored = self.temp / "verify-restore-target"
        self.run_cli("restore", "--package", str(self.package), "--target", str(restored))
        link = self.temp / "restored-link"
        os.symlink(restored, link)
        result = self.run_cli("verify", "--package", str(self.package), "--restored", str(link), expected=2)
        self._assert_unsafe_path(result)
        broken = self.temp / "broken-restored-link"
        os.symlink(self.temp / "nowhere", broken)
        result = self.run_cli("verify", "--package", str(self.package), "--restored", str(broken), expected=2)
        self._assert_unsafe_path(result)
        self.assertFalse((self.temp / "nowhere").exists())

    def test_24_normal_output_paths_still_work(self):
        output = self.temp / "normal-export.zip"
        self.run_cli("export", "--input", str(self.fixture), "--output", str(output))
        restored = self.temp / "normal-restored"
        self.run_cli("restore", "--package", str(output), "--target", str(restored))
        report_path = self.temp / "normal-report.md"
        self.run_cli("inspect", "--package", str(output), "--report", str(report_path))
        verified = self.run_cli("verify", "--package", str(output), "--restored", str(restored))
        self.assertEqual(verified["status"], "success")
        self.assertEqual(verified["report"]["status"], "passed")
        self.assertEqual(verified["report"]["restored"]["unexpected_files"], [])
        self.assertTrue(report_path.is_file())

    # --- M1 regression: broader credential-shaped token detection ---

    def test_25_extended_token_patterns_are_excluded(self):
        tokens = {
            "google.txt": "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
            "huggingface.txt": "hf_abcdefghijklmnopqrstuvwxyz12345",
            "jwt.txt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c",
            "gitlab.txt": "glpat-abcdefghijklmnopqrst12",
            "grok.txt": "xai-abcdefghijklmnopqrstuvwxyz12",
        }
        source = self.temp / "token-fixture"
        source.mkdir()
        for name, value in tokens.items():
            (source / name).write_text(value + "\n", encoding="utf-8")
        output = self.temp / "token-package.zip"
        result = self.run_cli("export", "--input", str(source), "--output", str(output))
        self.assertEqual(result["excluded_files"], len(tokens))
        manifest = self.manifest(output)
        self.assertEqual(
            sorted(entry["reason"] for entry in manifest["excluded_files"]),
            ["credential_shaped_value"] * len(tokens),
        )
        with zipfile.ZipFile(output) as archive:
            for info in archive.infolist():
                payload = archive.read(info.filename)
                for value in tokens.values():
                    self.assertNotIn(value.encode(), payload, f"secret value leaked into {info.filename}")

    def test_26_credential_mentions_and_templates_are_retained(self):
        source = self.temp / "docs-fixture"
        source.mkdir()
        (source / "ROTATION_GUIDE.md").write_text(
            "# Credential hygiene\n\nThis guide explains API key rotation and token storage without any values.\n",
            encoding="utf-8",
        )
        (source / ".env.example").write_text("API_KEY=${API_KEY}\nTOKEN=\n", encoding="utf-8")
        output = self.temp / "docs-package.zip"
        result = self.run_cli("export", "--input", str(source), "--output", str(output))
        self.assertEqual(result["excluded_files"], 0)
        manifest = self.manifest(output)
        retained = {entry["path"] for entry in manifest["files"] if entry["file_type"] == "original"}
        self.assertTrue(any(path.endswith("ROTATION_GUIDE.md") for path in retained))
        self.assertTrue(any(path.endswith(".env.example") for path in retained))

    # --- M2 regression: restored-directory difference detection ---

    def _restore_for_verify(self, name):
        target = self.temp / name
        self.run_cli("restore", "--package", str(self.package), "--target", str(target))
        return target

    def test_27_verify_clean_restored_directory_passes(self):
        target = self._restore_for_verify("clean-restored")
        result = self.run_cli("verify", "--package", str(self.package), "--restored", str(target))
        restored = result["report"]["restored"]
        self.assertEqual(restored["status"], "passed")
        self.assertEqual(restored["unexpected_files"], [])
        self.assertEqual(restored["missing_files"], [])
        self.assertEqual(restored["expected_file_count"], restored["actual_file_count"])

    def test_28_verify_detects_missing_restored_file(self):
        target = self._restore_for_verify("missing-restored")
        manifest = self.manifest()
        victim = next(entry["path"] for entry in manifest["files"] if entry["file_type"] == "original")
        (target / victim).unlink()
        result = self.run_cli("verify", "--package", str(self.package), "--restored", str(target), expected=1)
        restored = result["report"]["restored"]
        self.assertEqual(restored["status"], "failed")
        self.assertIn(victim, restored["missing_files"])
        self.assertEqual(restored["unexpected_files"], [])

    def test_29_verify_detects_modified_restored_file(self):
        target = self._restore_for_verify("modified-restored")
        manifest = self.manifest()
        victim = next(entry["path"] for entry in manifest["files"] if entry["file_type"] == "original")
        (target / victim).write_bytes(b"locally modified content\n")
        result = self.run_cli("verify", "--package", str(self.package), "--restored", str(target), expected=1)
        restored = result["report"]["restored"]
        self.assertEqual(restored["status"], "failed")
        self.assertTrue(any(item["path"] == victim for item in restored["hash_mismatches"]))

    def test_30_verify_detects_unexpected_restored_file_in_json_and_markdown(self):
        target = self._restore_for_verify("unexpected-restored")
        extra = target / "INJECTED_BY_TEST.txt"
        extra.write_text("extra file\n", encoding="utf-8")
        report_path = self.temp / "restored-diff.md"
        result = self.run_cli(
            "verify", "--package", str(self.package), "--restored", str(target),
            "--report", str(report_path), expected=1,
        )
        restored = result["report"]["restored"]
        self.assertEqual(restored["status"], "failed")
        self.assertEqual(restored["unexpected_files"], ["INJECTED_BY_TEST.txt"])
        self.assertEqual(result["report"]["package_status"], "valid")
        self.assertTrue(extra.is_file(), "verification must never delete unexpected files")
        markdown = report_path.read_text(encoding="utf-8")
        self.assertIn("Unexpected Files: 1", markdown)
        self.assertIn("INJECTED_BY_TEST.txt", markdown)

    # --- L1 regression: Unicode normalization path collisions ---

    def test_31_normal_unicode_names_are_accepted(self):
        cases = {"nfc": "caf\u00e9-notes.md", "nfd": "cafe\u0301-notes.md", "cjk": "项目进度.md"}
        for label, filename in cases.items():
            source = self.temp / f"unicode-{label}"
            source.mkdir()
            (source / filename).write_text(f"unicode {label}\n", encoding="utf-8")
            output = self.temp / f"unicode-{label}.zip"
            self.run_cli("export", "--input", str(source), "--output", str(output))
            manifest = self.manifest(output)
            original_names = [entry["path"] for entry in manifest["files"] if entry["file_type"] == "original"]
            self.assertTrue(any(path.endswith(filename) for path in original_names), filename)

    def test_32_unicode_colliding_zip_is_rejected(self):
        nfc = "caf\u00e9.txt"
        nfd = "cafe\u0301.txt"
        source = self.temp / "unicode-collision.zip"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr(nfc, "NFC")
            archive.writestr(nfd, "NFD")
        output = self.temp / "unicode-collision-out.zip"
        result = self.run_cli("export", "--input", str(source), "--output", str(output), expected=2)
        self.assertEqual(result["error"]["code"], "duplicate_zip_path")
        self.assertIn("Unicode", result["error"]["message"])
        self.assertFalse(output.exists())

    def test_33_unicode_colliding_directory_is_rejected(self):
        nfc = "caf\u00e9.txt"
        nfd = "cafe\u0301.txt"
        source = self.temp / "unicode-dir-collision"
        source.mkdir()
        (source / nfc).write_text("NFC", encoding="utf-8")
        (source / nfd).write_text("NFD", encoding="utf-8")
        output = self.temp / "unicode-dir-collision-out.zip"
        result = self.run_cli("export", "--input", str(source), "--output", str(output), expected=2)
        self.assertEqual(result["error"]["code"], "path_conflict")
        self.assertIn("Unicode", result["error"]["message"])
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
