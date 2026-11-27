#!/usr/bin/env python3
"""WorkspaceEasyPack v0.1: local, platform-neutral AI workspace archives."""

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone


PACKAGE_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
MAX_FILES = 20000
MAX_MEMBER_SIZE = 128 * 1024 * 1024
MAX_TOTAL_SIZE = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000
CATEGORIES = (
    "profile",
    "agent",
    "memory",
    "projects",
    "workflows",
    "skills",
    "tools",
    "unknown",
)
CANONICAL_NAMES = {
    "USER_PROFILE.md": "profile/USER_PROFILE.md",
    "AGENT_IDENTITY.md": "agent/AGENT_IDENTITY.md",
    "AGENT_INSTRUCTIONS.md": "agent/AGENT_INSTRUCTIONS.md",
    "WORKING_PROTOCOLS.md": "agent/WORKING_PROTOCOLS.md",
}
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml",
    ".csv", ".xml", ".html", ".py", ".js", ".ts", ".sh", ".env",
}
PRIVATE_KEY_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
SENSITIVE_FILENAMES = {
    ".netrc", ".pgpass", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials.json", "secrets.json", "secrets.yaml", "secrets.yml",
}
SECRET_KEYS = (
    r"api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|"
    r"password|passwd|client[_-]?secret|secret[_-]?key|private[_-]?key|"
    r"aws[_-]?secret[_-]?access[_-]?key"
)
QUOTED_SECRET_RE = re.compile(
    r"(?i)(?:[\"']?)(?:" + SECRET_KEYS + r")(?:[\"']?)\s*[:=]\s*[\"']([^\"'\r\n]+)[\"']"
)
UNQUOTED_SECRET_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:" + SECRET_KEYS + r")\s*[:=]\s*([^\s,;#}\]]+)"
)
BEARER_RE = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+([A-Za-z0-9._~+/=-]{12,})")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
TOKEN_RES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxai-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)
PLATFORM_MARKERS = {
    "chatgpt": ("chatgpt", "openai"),
    "claude": ("claude", "anthropic"),
    "gemini": ("gemini",),
    "cursor": (".cursor", "cursorrules"),
    "vscode": (".vscode",),
    "dify": ("dify",),
    "coze": ("coze",),
    "mcp": ("mcp.json", ".mcp.json", "mcp-config"),
}


class WorkspaceError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return (slug or "input")[:80]


def one_line(value, fallback="unspecified"):
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    return (cleaned or fallback)[:160]


def safe_user_path(value, label):
    """Resolve a user-supplied path without ever following symbolic links.

    Every existing component of the original path, including parent directories,
    is checked with lstat semantics before resolution. Broken, relative, and
    intermediate symlinks are therefore rejected instead of being followed.
    """
    expanded = Path(value).expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    current = Path(expanded.anchor)
    for part in expanded.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise WorkspaceError(
                "unsafe_output_path",
                f"{label} is unsafe: path component '{current}' is a symbolic link; refusing to follow it.",
            )
    return expanded.resolve()


def normalize_archive_path(name):
    if not isinstance(name, str) or not name or "\x00" in name:
        raise WorkspaceError("unsafe_zip_path", "ZIP contains an empty or invalid path.")
    if "\\" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise WorkspaceError("unsafe_zip_path", "ZIP contains an absolute or non-portable path.")
    stripped = name[:-1] if name.endswith("/") else name
    parts = stripped.split("/")
    if not stripped or any(part in ("", ".", "..") for part in parts):
        raise WorkspaceError("unsafe_zip_path", "ZIP contains path traversal or ambiguous path segments.")
    normalized = "/".join(parts)
    if len(normalized) > 1024:
        raise WorkspaceError("unsafe_zip_path", "ZIP path exceeds the 1024 character limit.")
    return normalized


def safe_zip_members(archive):
    infos = archive.infolist()
    if len(infos) > MAX_FILES:
        raise WorkspaceError("zip_limit_exceeded", "ZIP contains too many entries.")
    members = []
    seen = set()
    casefold_seen = set()
    total_size = 0
    for info in infos:
        path = normalize_archive_path(info.filename)
        if info.flag_bits & 0x1:
            raise WorkspaceError("encrypted_zip", "Encrypted ZIP entries are not supported.")
        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if file_type == stat.S_IFLNK:
            raise WorkspaceError("unsafe_zip_link", "ZIP symbolic links are not supported.")
        if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise WorkspaceError("unsafe_zip_file_type", "ZIP special files are not supported.")
        normalization_key = unicodedata.normalize("NFC", path).casefold()
        if path in seen or normalization_key in casefold_seen:
            raise WorkspaceError(
                "duplicate_zip_path",
                "ZIP contains duplicate paths or paths colliding after Unicode NFC normalization/case folding.",
            )
        seen.add(path)
        casefold_seen.add(normalization_key)
        if info.is_dir():
            continue
        if info.file_size > MAX_MEMBER_SIZE:
            raise WorkspaceError("zip_limit_exceeded", "A ZIP entry exceeds the 128 MiB limit.")
        total_size += info.file_size
        if total_size > MAX_TOTAL_SIZE:
            raise WorkspaceError("zip_limit_exceeded", "ZIP uncompressed content exceeds the 512 MiB limit.")
        if info.file_size > 1024 * 1024 and info.compress_size > 0:
            if info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise WorkspaceError("zip_limit_exceeded", "ZIP entry has an unsafe compression ratio.")
        members.append((path, info))
    return members


def open_zip(path):
    try:
        return zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise WorkspaceError("invalid_zip", "Input is not a readable ZIP archive.") from exc


def read_regular_file(path):
    try:
        size = path.stat().st_size
        if size > MAX_MEMBER_SIZE:
            return None, size, "file_too_large_for_v0_1"
        with open(path, "rb") as handle:
            data = handle.read(MAX_MEMBER_SIZE + 1)
        if len(data) > MAX_MEMBER_SIZE:
            return None, size, "file_too_large_for_v0_1"
        return data, size, None
    except OSError as exc:
        raise WorkspaceError("input_read_failed", "A user-provided input file could not be read.") from exc


def is_template_name(name):
    lower = name.lower()
    return any(marker in lower for marker in ("example", "sample", "template", "placeholder"))


def placeholder_value(value):
    cleaned = value.strip().strip("\"'").strip()
    lower = cleaned.lower()
    if not cleaned:
        return True
    if lower in {
        "null", "none", "redacted", "example", "sample", "dummy", "changeme",
        "change-me", "your-api-key", "your_api_key", "your-token", "your_token",
        "***", "xxx", "<redacted>",
    }:
        return True
    if cleaned.startswith(("<", "${", "{{", "$(")):
        return True
    if lower.startswith(("your_", "your-", "replace_", "replace-", "insert_", "example_", "test_")):
        return True
    return False


def sensitive_reason(name, data):
    base = PurePosixPath(name).name
    lower = base.lower()
    suffix = PurePosixPath(lower).suffix
    if suffix in PRIVATE_KEY_SUFFIXES or (lower in SENSITIVE_FILENAMES and not is_template_name(lower)):
        return "sensitive_file_type"
    if b"\x00" in data[:4096] and suffix not in TEXT_SUFFIXES:
        return None
    text = data.decode("utf-8", errors="replace")
    if PRIVATE_KEY_RE.search(text):
        return "private_key_material"
    for pattern in (QUOTED_SECRET_RE, UNQUOTED_SECRET_RE, BEARER_RE):
        for match in pattern.finditer(text):
            if not placeholder_value(match.group(1)):
                return "embedded_credential"
    for pattern in TOKEN_RES:
        if pattern.search(text):
            return "credential_shaped_value"
    return None


def classify_path(path):
    lower = path.lower()
    parts = set(PurePosixPath(lower).parts)
    base = PurePosixPath(lower).name
    if base == "skill.md" or parts.intersection({"skills", "skill", "plugins", "plugin"}):
        return "skills"
    if base in {"user_profile.md", "profile.md", "preferences.md", "about-me.md"}:
        return "profile"
    if base in {
        "agent_identity.md", "agent_instructions.md", "working_protocols.md",
        "system_instructions.md", "system-prompt.md", "persona.md", ".cursorrules",
    }:
        return "agent"
    if base in {"mcp.json", ".mcp.json", "requirements.txt", "package.json", "pyproject.toml", "environment.yml"}:
        return "tools"
    if base in {"todo.md", "decisions.md", "progress.md", "roadmap.md"}:
        return "projects"
    if base in {"workflow.md", "prompt.md", "playbook.md", "runbook.md"}:
        return "workflows"
    if parts.intersection({"memory", "memories", "diary", "semantic-memory", "relationships", "revision-history", "conversations"}):
        return "memory"
    if parts.intersection({"tools", "tool-config", "environment", "mcp"}):
        return "tools"
    if parts.intersection({"profile", "preferences", "user-profile"}):
        return "profile"
    if parts.intersection({"agent", "agents", "instructions", "persona"}):
        return "agent"
    if parts.intersection({"projects", "project"}):
        return "projects"
    if parts.intersection({"workflows", "workflow", "prompts", "playbooks", "runbooks"}):
        return "workflows"
    return "unknown"


def platform_findings(path):
    lower = path.lower()
    found = []
    for platform, markers in PLATFORM_MARKERS.items():
        if any(marker in lower for marker in markers):
            found.append(platform)
    return found


def media_type(path):
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def template_path(name):
    path = Path(__file__).resolve().parent.parent / "assets" / "templates" / name
    if not path.is_file():
        raise WorkspaceError("missing_skill_asset", "A required WorkspaceEasyPack template is unavailable.")
    return path


def add_staged_file(staging, archive_path, data, files, **metadata):
    normalized = normalize_archive_path(archive_path)
    destination = staging.joinpath(*PurePosixPath(normalized).parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(destination, "xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise WorkspaceError("internal_path_collision", "Two package outputs resolved to the same path.") from exc
    entry = {
        "path": normalized,
        "file_type": metadata.pop("file_type", "generated"),
        "data_category": metadata.pop("data_category", "unknown"),
        "size": len(data),
        "sha256": sha256_bytes(data),
        "source": metadata.pop("source", "workspace-easy-pack"),
        "media_type": media_type(normalized),
        "ai_transformed": metadata.pop("ai_transformed", False),
    }
    entry.update(metadata)
    files.append(entry)
    return entry


def check_archive_path_collisions(entries):
    """Reject archive paths that collide after Unicode NFC normalization/case folding.

    Original file names are never rewritten; colliding inputs fail with an
    explicit error instead of being silently renamed or overwritten.
    """
    seen = {}
    for entry in entries:
        path = entry["path"]
        key = unicodedata.normalize("NFC", path).casefold()
        previous = seen.get(key)
        if previous is not None and previous != path:
            raise WorkspaceError(
                "path_conflict",
                f"Archive paths collide after Unicode NFC normalization/case folding: '{path}' and '{previous}'.",
            )
        seen[key] = path


def duplicate_groups(entries):
    groups = defaultdict(list)
    for entry in entries:
        if entry.get("file_type") == "original":
            groups[entry["sha256"]].append(entry["path"])
    return [
        {"sha256": digest, "paths": sorted(paths), "count": len(paths)}
        for digest, paths in sorted(groups.items()) if len(paths) > 1
    ]


def collect_directory_files(root, output_path, excluded):
    collected = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for dirname in sorted(dirnames):
            candidate = current_path / dirname
            if candidate.is_symlink():
                excluded.append({"source": f"directory:{root.name}/{dirname}", "reason": "symbolic_link", "size": None, "sha256": None})
            else:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                excluded.append({"source": f"directory:{root.name}/{relative}", "reason": "symbolic_link", "size": None, "sha256": None})
                continue
            if output_path and path.resolve() == output_path:
                excluded.append({"source": f"directory:{root.name}/{relative}", "reason": "output_archive", "size": None, "sha256": None})
                continue
            if not path.is_file():
                excluded.append({"source": f"directory:{root.name}/{relative}", "reason": "non_regular_file", "size": None, "sha256": None})
                continue
            collected.append((path, relative))
    return collected


def command_export(args):
    output = safe_user_path(args.output, "--output")
    output_exists = output.exists()
    if output_exists and not args.overwrite:
        raise WorkspaceError("output_exists", "Output archive exists; pass --overwrite only with explicit user authorization.")
    if output_exists and not output.is_file():
        raise WorkspaceError("invalid_output", "Output path is not a regular file.")
    if not args.input:
        raise WorkspaceError("missing_input", "At least one explicit input file or directory is required.")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".workspace-easy-pack-export-", dir=str(output.parent)))
    temp_output = output.parent / f".{output.name}.{os.getpid()}.tmp"
    files = []
    excluded = []
    original_entries = []
    derived_by_category = defaultdict(list)
    total_original_size = 0
    try:
        for input_index, raw_input in enumerate(args.input, 1):
            source_path = Path(raw_input).expanduser()
            try:
                resolved = source_path.resolve(strict=True)
            except OSError as exc:
                raise WorkspaceError("input_not_found", "A user-provided input path does not exist.") from exc
            if resolved.is_symlink() or source_path.is_symlink():
                excluded.append({"source": f"input[{input_index}]", "reason": "symbolic_link", "size": None, "sha256": None})
                continue
            source_id = f"{input_index:03d}-{slugify(resolved.name)}"
            local_items = []
            if resolved.is_dir():
                local_items = [(path, rel, f"input[{input_index}]:{rel}") for path, rel in collect_directory_files(resolved, output, excluded)]
            elif resolved.is_file() and resolved.suffix.lower() == ".zip":
                with open_zip(resolved) as imported:
                    for rel, info in safe_zip_members(imported):
                        data = imported.read(info)
                        local_items.append((None, rel, f"input[{input_index}]:{resolved.name}!/{rel}", data, info.file_size))
            elif resolved.is_file():
                local_items = [(resolved, resolved.name, f"input[{input_index}]:{resolved.name}")]
            else:
                excluded.append({"source": f"input[{input_index}]", "reason": "non_regular_file", "size": None, "sha256": None})

            for item in local_items:
                if len(item) == 3:
                    path, rel, locator = item
                    data, size, read_exclusion = read_regular_file(path)
                    if read_exclusion:
                        excluded.append({"source": locator, "reason": read_exclusion, "size": size, "sha256": None})
                        continue
                else:
                    _, rel, locator, data, size = item
                rel = normalize_archive_path(rel)
                total_original_size += len(data)
                if total_original_size > MAX_TOTAL_SIZE:
                    raise WorkspaceError("input_limit_exceeded", "Total input exceeds the 512 MiB v0.1 limit.")
                reason = sensitive_reason(rel, data)
                if reason:
                    excluded.append({"source": locator, "reason": reason, "size": len(data), "sha256": sha256_bytes(data)})
                    continue
                category = classify_path(rel)
                original_path = f"source/{source_id}/{rel}"
                original = add_staged_file(
                    staging, original_path, data, files,
                    file_type="original", data_category=category, source=locator,
                    ai_transformed=False,
                )
                original_entries.append(original)
                if category != "unknown":
                    if rel in CANONICAL_NAMES.values():
                        destination = rel
                    elif PurePosixPath(rel).name in CANONICAL_NAMES and not any(
                        entry["path"] == CANONICAL_NAMES[PurePosixPath(rel).name] for entry in files
                    ):
                        destination = CANONICAL_NAMES[PurePosixPath(rel).name]
                    else:
                        destination = f"{category}/{source_id}/{rel}"
                    derived = add_staged_file(
                        staging, destination, data, files,
                        file_type="normalized_copy", data_category=category,
                        source="deterministic-category-copy", ai_transformed=False,
                        derived_from=[original_path], transformations=["deterministic-category-copy"],
                    )
                    derived_by_category[category].append(derived)

        for category in sorted(derived_by_category):
            lines = [
                f"# {category.replace('-', ' ').title()} Index", "",
                "Generated by WorkspaceEasyPack without AI rewriting.", "",
                "| Restored file | Original file | SHA-256 |", "|---|---|---|",
            ]
            for entry in sorted(derived_by_category[category], key=lambda item: item["path"]):
                lines.append(f"| {entry['path']} | {entry['derived_from'][0]} | {entry['sha256']} |")
            lines.append("")
            add_staged_file(
                staging, f"{category}/INDEX.md", "\n".join(lines).encode("utf-8"), files,
                file_type="generated_index", data_category=category,
                derived_from=[entry["path"] for entry in derived_by_category[category]],
            )

        duplicates = duplicate_groups(original_entries)
        guide = template_path("restore-guide.md").read_text(encoding="utf-8")
        guide = guide.replace("{{GENERATED_AT}}", utc_now()).replace("{{PACKAGE_VERSION}}", PACKAGE_VERSION)
        add_staged_file(
            staging, "RESTORE_GUIDE.md", guide.encode("utf-8"), files,
            file_type="generated_guide", data_category="unknown",
        )
        export_report = {
            "report_type": "export",
            "generated_at": utc_now(),
            "package_version": PACKAGE_VERSION,
            "status": "success",
            "original_file_count": len(original_entries),
            "normalized_copy_count": sum(len(items) for items in derived_by_category.values()),
            "excluded_file_count": len(excluded),
            "category_counts": dict(sorted(Counter(entry["data_category"] for entry in original_entries).items())),
            "duplicates": duplicates,
            "excluded_files": excluded,
            "ai_content_transformation": False,
            "notes": [
                "Unknown files are retained under source/ and marked unknown.",
                "Sensitive files are excluded in full; no secret values are included in reports.",
                "Platform adapters and external account access were not used.",
            ],
        }
        add_staged_file(
            staging, "reports/export-report.json", json_bytes(export_report), files,
            file_type="generated_report", data_category="unknown",
        )
        check_archive_path_collisions(files)
        manifest = {
            "package_name": one_line(args.package_name or output.stem, "workspace-easy-pack"),
            "package_version": PACKAGE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "export_timestamp": utc_now(),
            "source_platform": one_line(args.source_platform, "") or None,
            "source_agent": one_line(args.source_agent, "") or None,
            "files": sorted(files, key=lambda entry: entry["path"]),
            "excluded_files": excluded,
            "statistics": {
                "payload_file_count": len(files),
                "original_file_count": len(original_entries),
                "excluded_file_count": len(excluded),
                "duplicate_group_count": len(duplicates),
                "category_counts": dict(sorted(Counter(entry["data_category"] for entry in original_entries).items())),
            },
            "integrity": {
                "algorithm": "SHA-256",
                "manifest_scope": "All payload files except manifest.json and checksums.sha256",
                "checksums_scope": "manifest.json and all payload files; checksums.sha256 excludes itself",
            },
            "capabilities": {
                "ai_summarization": False,
                "platform_api_access": False,
                "scripts_executed_from_inputs": False,
            },
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(json_bytes(manifest))
        checksum_lines = []
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "checksums.sha256":
                relative = path.relative_to(staging).as_posix()
                checksum_lines.append(f"{sha256_file(path)}  {relative}")
        (staging / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging).as_posix())
        with open_zip(temp_output) as archive:
            safe_zip_members(archive)
            bad_member = archive.testzip()
            if bad_member:
                raise WorkspaceError("archive_self_test_failed", "Generated ZIP failed its CRC self-test.")
        if output.exists() and not args.overwrite:
            raise WorkspaceError("output_exists", "Output archive appeared during export; refusing to overwrite it.")
        os.replace(temp_output, output)
        return {
            "status": "success",
            "operation": "export",
            "package": str(output),
            "package_version": PACKAGE_VERSION,
            "original_files": len(original_entries),
            "payload_files": len(files),
            "excluded_files": len(excluded),
            "duplicate_groups": len(duplicates),
            "manifest": "manifest.json",
            "export_report": "reports/export-report.json",
        }
    finally:
        if temp_output.exists():
            temp_output.unlink()
        shutil.rmtree(staging, ignore_errors=True)


def validate_manifest(manifest):
    required = {
        "package_name", "package_version", "schema_version", "export_timestamp",
        "source_platform", "source_agent", "files", "excluded_files",
    }
    if not isinstance(manifest, dict) or not required.issubset(manifest):
        raise WorkspaceError("invalid_manifest", "manifest.json is missing required top-level fields.")
    if not isinstance(manifest["files"], list) or not isinstance(manifest["excluded_files"], list):
        raise WorkspaceError("invalid_manifest", "Manifest files and exclusions must be arrays.")
    entry_required = {"path", "file_type", "data_category", "size", "sha256", "source", "ai_transformed"}
    seen = set()
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not entry_required.issubset(entry):
            raise WorkspaceError("invalid_manifest", "A manifest file entry is missing required fields.")
        path = normalize_archive_path(entry["path"])
        if path in seen or path in {"manifest.json", "checksums.sha256"}:
            raise WorkspaceError("invalid_manifest", "Manifest contains duplicate or reserved payload paths.")
        seen.add(path)
        if not isinstance(entry["size"], int) or entry["size"] < 0:
            raise WorkspaceError("invalid_manifest", "Manifest file size must be a non-negative integer.")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise WorkspaceError("invalid_manifest", "Manifest contains an invalid SHA-256 value.")
        if entry["data_category"] not in CATEGORIES:
            raise WorkspaceError("invalid_manifest", "Manifest contains an unknown data category.")
        for original in entry.get("derived_from", []):
            normalize_archive_path(original)


def parse_checksums(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError("invalid_checksums", "checksums.sha256 is not UTF-8 text.") from exc
    records = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        if not match:
            raise WorkspaceError("invalid_checksums", "checksums.sha256 contains a malformed line.")
        digest, path = match.groups()
        path = normalize_archive_path(path)
        if path in records:
            raise WorkspaceError("invalid_checksums", "checksums.sha256 contains duplicate paths.")
        records[path] = digest
    return records


def hash_zip_member(archive, info):
    digest = hashlib.sha256()
    size = 0
    try:
        with archive.open(info, "r") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise WorkspaceError("zip_read_failed", "A ZIP member could not be read or failed its CRC check.") from exc
    return size, digest.hexdigest()


def dependency_declarations(names, archive, info_by_path):
    declarations = []
    for path in sorted(names):
        base = PurePosixPath(path).name.lower()
        packages = []
        if base == "requirements.txt":
            text = archive.read(info_by_path[path]).decode("utf-8", errors="replace")
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    packages.append(line)
        elif base == "package.json":
            try:
                value = json.loads(archive.read(info_by_path[path]).decode("utf-8"))
                for section in ("dependencies", "devDependencies", "optionalDependencies"):
                    packages.extend(f"{name}@{version}" for name, version in value.get(section, {}).items())
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                packages = ["unparseable-package.json"]
        elif base == "skill.md":
            text = archive.read(info_by_path[path]).decode("utf-8", errors="replace")
            packages.extend(re.findall(r"^\s*-\s*([A-Za-z0-9_.-]+(?:==|>=|<=|~=|>|<)[^\s#]+)", text, re.MULTILINE))
        if packages:
            declarations.append({
                "source": path,
                "declared": sorted(set(packages)),
                "status": "target_environment_check_required",
            })
    return declarations


def missing_markdown_references(names, archive, info_by_path):
    missing = []
    for path in sorted(name for name in names if name.startswith("source/") and name.lower().endswith(".md")):
        text = archive.read(info_by_path[path]).decode("utf-8", errors="replace")
        for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text):
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
                continue
            target = target.split("?", 1)[0]
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            if resolved.startswith("../") or resolved not in names:
                missing.append({"source": path, "reference": target, "status": "missing_or_external"})
    return missing


def inspect_package(package_path):
    package = Path(package_path).expanduser()
    if not package.is_file():
        raise WorkspaceError("package_not_found", "WorkspaceEasyPack archive does not exist.")
    with open_zip(package) as archive:
        members = safe_zip_members(archive)
        names = {path for path, _ in members}
        info_by_path = dict(members)
        if "manifest.json" not in names:
            raise WorkspaceError("invalid_manifest", "Archive has no root manifest.json.")
        try:
            manifest = json.loads(archive.read(info_by_path["manifest.json"]).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WorkspaceError("invalid_manifest", "manifest.json is not valid UTF-8 JSON.") from exc
        validate_manifest(manifest)
        if "checksums.sha256" not in names:
            raise WorkspaceError("invalid_checksums", "Archive has no root checksums.sha256.")
        checksums = parse_checksums(archive.read(info_by_path["checksums.sha256"]))
        actual_hashes = {}
        for path, info in members:
            actual_hashes[path] = hash_zip_member(archive, info)

        manifest_paths = {entry["path"] for entry in manifest["files"]}
        missing_payload = sorted(manifest_paths - names)
        unexpected_payload = sorted(names - manifest_paths - {"manifest.json", "checksums.sha256"})
        size_mismatches = []
        hash_mismatches = []
        for entry in manifest["files"]:
            path = entry["path"]
            if path not in names:
                continue
            actual_size = info_by_path[path].file_size
            actual_hash = actual_hashes[path][1]
            if actual_size != entry["size"]:
                size_mismatches.append({"path": path, "expected": entry["size"], "actual": actual_size})
            if actual_hash != entry["sha256"]:
                hash_mismatches.append({"path": path, "expected": entry["sha256"], "actual": actual_hash})
        missing_checksums = sorted((names - {"checksums.sha256"}) - set(checksums))
        stale_checksums = sorted(set(checksums) - names)
        checksum_mismatches = [
            {"path": path, "expected": checksums[path], "actual": actual_hashes[path][1]}
            for path in sorted(set(checksums) & names) if checksums[path] != actual_hashes[path][1]
        ]

        sensitive = []
        platform = []
        for path, info in members:
            data = archive.read(info)
            reason = sensitive_reason(path, data)
            if reason:
                sensitive.append({"path": path, "reason": reason, "action": "manual_review_do_not_publish"})
            markers = platform_findings(path)
            if markers:
                platform.append({"path": path, "markers": sorted(set(markers)), "restore_mode": "manual_configuration"})

        integrity_issues = (
            missing_payload + unexpected_payload + size_mismatches + hash_mismatches
            + missing_checksums + stale_checksums + checksum_mismatches
        )
        categories = {}
        for category in CATEGORIES:
            category_entries = [entry for entry in manifest["files"] if entry["data_category"] == category]
            if category_entries:
                categories[category] = {
                    "files": len(category_entries),
                    "original_files": sum(entry["file_type"] == "original" for entry in category_entries),
                    "normalized_copies": sum(entry["file_type"] == "normalized_copy" for entry in category_entries),
                }
        direct_restore = sorted(
            entry["path"] for entry in manifest["files"]
            if entry["file_type"] in {"normalized_copy", "generated_guide"}
        )
        manual = [item["path"] for item in platform]
        manual.extend(entry["source"] for entry in manifest["excluded_files"])
        report = {
            "report_type": "inspect",
            "generated_at": utc_now(),
            "package_name": manifest["package_name"],
            "package_version": manifest["package_version"],
            "schema_version": manifest["schema_version"],
            "source_platform": manifest["source_platform"],
            "source_agent": manifest["source_agent"],
            "package_status": "valid" if not integrity_issues else "invalid",
            "summary": {
                "archive_files": len(names),
                "manifest_payload_files": len(manifest_paths),
                "categories": categories,
                "duplicate_groups": len(duplicate_groups(manifest["files"])),
                "sensitive_findings": len(sensitive),
                "platform_specific_files": len(platform),
            },
            "integrity": {
                "missing_payload": missing_payload,
                "unexpected_payload": unexpected_payload,
                "size_mismatches": size_mismatches,
                "hash_mismatches": hash_mismatches,
                "missing_checksums": missing_checksums,
                "stale_checksums": stale_checksums,
                "checksum_mismatches": checksum_mismatches,
                "manifest_present": True,
                "checksums_present": True,
            },
            "duplicates": duplicate_groups(manifest["files"]),
            "dependencies": dependency_declarations(names, archive, info_by_path),
            "missing_internal_references": missing_markdown_references(names, archive, info_by_path),
            "platform_specific": platform,
            "sensitive_findings": sensitive,
            "restoration": {
                "direct_restore_or_read": direct_restore,
                "manual_configuration": sorted(set(manual)),
                "original_files_preserved_under": "source/",
                "unknown_files_require_review": categories.get("unknown", {}).get("original_files", 0),
                "platform_behavior_equivalence_guaranteed": False,
            },
        }
        return report


def markdown_report(report):
    lines = [
        f"# WorkspaceEasyPack {report['report_type'].title()} Report", "",
        f"- Generated: {report['generated_at']}",
        f"- Package: {report.get('package_name', 'unknown')}",
        f"- Status: {report.get('package_status', report.get('status', 'unknown'))}", "",
        "## Summary", "",
    ]
    for key, value in report.get("summary", {}).items():
        if not isinstance(value, (dict, list)):
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.extend(["", "## Integrity", ""])
    integrity = report.get("integrity", {})
    for key, value in integrity.items():
        count = len(value) if isinstance(value, list) else value
        lines.append(f"- {key.replace('_', ' ').title()}: {count}")
    for section, title in (
        ("duplicates", "Duplicate Content"),
        ("dependencies", "Dependencies Requiring Target Checks"),
        ("platform_specific", "Platform-Specific Configuration"),
        ("sensitive_findings", "Sensitive Findings"),
    ):
        items = report.get(section, [])
        lines.extend(["", f"## {title}", ""])
        lines.append(f"- Count: {len(items)}")
    if report.get("restored"):
        lines.extend(["", "## Restored Workspace", ""])
        for key, value in report["restored"].items():
            if isinstance(value, list):
                lines.append(f"- {key.replace('_', ' ').title()}: {len(value)}")
                for item in value[:50]:
                    label = item.get("path") if isinstance(item, dict) else item
                    lines.append(f"  - {label if label is not None else json.dumps(item, sort_keys=True)}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.extend([
        "", "## Scope", "",
        "This report reflects local file inspection only. Real platform APIs and behavior equivalence were not tested.",
        "No secret values are reproduced in this report.", "",
    ])
    return "\n".join(lines)


def write_report(path_value, report, overwrite=False):
    if not path_value:
        return None
    path = safe_user_path(path_value, "--report")
    if path.exists() and not overwrite:
        raise WorkspaceError("report_exists", "Report path exists; pass --overwrite only with explicit user authorization.")
    if path.exists() and not path.is_file():
        raise WorkspaceError("invalid_report_path", "Report path is not a regular file.")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = markdown_report(report).encode("utf-8") if path.suffix.lower() in {".md", ".markdown"} else json_bytes(report)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        temporary.write_bytes(data)
        if path.exists() and not overwrite:
            raise WorkspaceError("report_exists", "Report path appeared during processing; refusing to overwrite it.")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return str(path)


def command_inspect(args):
    report = inspect_package(args.package)
    report_path = write_report(args.report, report, args.overwrite)
    result = {"status": "success", "operation": "inspect", "report_path": report_path, "report": report}
    return result, 0 if report["package_status"] == "valid" else 1


def command_verify(args):
    report = inspect_package(args.package)
    verification = {
        "report_type": "verify",
        "generated_at": report["generated_at"],
        "package_name": report["package_name"],
        "package_version": report["package_version"],
        "package_status": report["package_status"],
        "summary": report["summary"],
        "integrity": report["integrity"],
        "duplicates": report["duplicates"],
        "dependencies": report["dependencies"],
        "platform_specific": report["platform_specific"],
        "sensitive_findings": report["sensitive_findings"],
    }
    restored_result = None
    if args.restored:
        restored = safe_user_path(args.restored, "--restored")
        if not restored.is_dir() or restored.is_symlink():
            raise WorkspaceError("invalid_restored_directory", "Restored target must be a real directory, not a symbolic link.")
        restored_result = {
            "path": str(restored), "missing_files": [], "unexpected_files": [],
            "size_mismatches": [], "hash_mismatches": [],
            "manifest_match": False, "checksums_match": False,
        }
        with open_zip(Path(args.package).expanduser()) as archive:
            members = dict(safe_zip_members(archive))
            manifest = json.loads(archive.read(members["manifest.json"]).decode("utf-8"))
            validate_manifest(manifest)
            for special in ("manifest.json", "checksums.sha256"):
                target = restored.joinpath(*PurePosixPath(special).parts)
                restored_result["manifest_match" if special == "manifest.json" else "checksums_match"] = (
                    target.is_file() and sha256_file(target) == sha256_bytes(archive.read(members[special]))
                )
            for entry in manifest["files"]:
                relative = normalize_archive_path(entry["path"])
                target = restored.joinpath(*PurePosixPath(relative).parts)
                if not target.is_file() or target.is_symlink():
                    restored_result["missing_files"].append(relative)
                    continue
                size = target.stat().st_size
                if size != entry["size"]:
                    restored_result["size_mismatches"].append({"path": relative, "expected": entry["size"], "actual": size})
                actual_hash = sha256_file(target)
                if actual_hash != entry["sha256"]:
                    restored_result["hash_mismatches"].append({"path": relative, "expected": entry["sha256"], "actual": actual_hash})
        expected_restored = {entry["path"] for entry in manifest["files"]}
        expected_restored.update({
            "manifest.json", "checksums.sha256", "AGENT_BOOTSTRAP.md",
            "reports/restore-report.json", "reports/restore-report.md",
        })
        actual_restored = set()
        for current, dirnames, filenames in os.walk(restored, followlinks=False):
            current_path = Path(current)
            for dirname in dirnames:
                if (current_path / dirname).is_symlink():
                    actual_restored.add((current_path / dirname).relative_to(restored).as_posix())
            for filename in filenames:
                actual_restored.add((current_path / filename).relative_to(restored).as_posix())
        restored_result["unexpected_files"] = sorted(actual_restored - expected_restored)
        restored_result["expected_file_count"] = len(expected_restored)
        restored_result["actual_file_count"] = len(actual_restored)
        restored_result["status"] = "passed" if (
            not restored_result["missing_files"] and not restored_result["unexpected_files"]
            and not restored_result["size_mismatches"]
            and not restored_result["hash_mismatches"] and restored_result["manifest_match"]
            and restored_result["checksums_match"]
        ) else "failed"
        verification["restored"] = restored_result
    passed = report["package_status"] == "valid" and (not restored_result or restored_result["status"] == "passed")
    verification["status"] = "passed" if passed else "failed"
    verification["verification_scope"] = "package_and_restored_files" if restored_result else "package_only"
    report_path = write_report(args.report, verification, args.overwrite)
    return {"status": "success" if passed else "failed", "operation": "verify", "report_path": report_path, "report": verification}, 0 if passed else 1


def command_restore(args):
    target = safe_user_path(args.target, "--target")
    if target.exists() or target.is_symlink():
        raise WorkspaceError("target_exists", "Restore target must not exist; existing files are never overwritten.")
    report = inspect_package(args.package)
    if report["package_status"] != "valid":
        raise WorkspaceError("package_integrity_failed", "Restore refused because package integrity checks failed.")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".workspace-easy-pack-restore-", dir=str(target.parent)))
    renamed = False
    try:
        with open_zip(Path(args.package).expanduser()) as archive:
            for path, info in safe_zip_members(archive):
                destination = staging.joinpath(*PurePosixPath(path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, open(destination, "xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
        bootstrap = template_path("agent-bootstrap.md").read_text(encoding="utf-8")
        replacements = {
            "GENERATED_AT": utc_now(),
            "TARGET_PLATFORM": one_line(args.target_platform, "generic"),
            "TARGET_AGENT": one_line(args.target_agent, "generic"),
            "SOURCE_PLATFORM": one_line(report.get("source_platform"), "unknown"),
            "CATEGORY_SUMMARY": json.dumps(report["summary"]["categories"], ensure_ascii=False, sort_keys=True),
            "MANUAL_COUNT": str(len(report["restoration"]["manual_configuration"])),
            "SENSITIVE_COUNT": str(len(report["sensitive_findings"])),
        }
        for key, value in replacements.items():
            bootstrap = bootstrap.replace("{{" + key + "}}", value)
        (staging / "AGENT_BOOTSTRAP.md").write_text(bootstrap, encoding="utf-8")
        restore_report = {
            "report_type": "restore",
            "generated_at": utc_now(),
            "status": "success",
            "package_name": report["package_name"],
            "target_platform": one_line(args.target_platform, "generic"),
            "target_agent": one_line(args.target_agent, "generic"),
            "target_directory_name": target.name,
            "files_restored": report["summary"]["archive_files"],
            "categories": report["summary"]["categories"],
            "manual_configuration": report["restoration"]["manual_configuration"],
            "dependencies": report["dependencies"],
            "platform_specific": report["platform_specific"],
            "sensitive_findings": report["sensitive_findings"],
            "overwrote_existing_files": False,
            "imported_scripts_executed": False,
            "compatibility_notes": [
                "Original files were preserved under source/.",
                "Deterministic normalized copies were restored under category directories.",
                "Platform-specific settings require manual review; no platform API adapter was invoked.",
                "Model behavior, memories outside the package, and unavailable platform features cannot be reproduced.",
            ],
        }
        reports_dir = staging / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "restore-report.json").write_bytes(json_bytes(restore_report))
        (reports_dir / "restore-report.md").write_text(markdown_report(restore_report), encoding="utf-8")
        if target.exists() or target.is_symlink():
            raise WorkspaceError("target_exists", "Restore target appeared during processing; refusing to overwrite it.")
        os.rename(staging, target)
        renamed = True
        return {
            "status": "success",
            "operation": "restore",
            "target": str(target),
            "files_restored": report["summary"]["archive_files"],
            "bootstrap": str(target / "AGENT_BOOTSTRAP.md"),
            "restore_guide": str(target / "RESTORE_GUIDE.md"),
            "restore_report": str(target / "reports" / "restore-report.json"),
            "manual_configuration_items": len(report["restoration"]["manual_configuration"]),
            "overwrote_existing_files": False,
        }
    finally:
        if not renamed:
            shutil.rmtree(staging, ignore_errors=True)


def build_parser():
    parser = argparse.ArgumentParser(prog="workspace_easy_pack.py", description="WorkspaceEasyPack v0.1 local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export", help="Create a portable workspace ZIP backup")
    export.add_argument("--input", action="append", required=True, help="Explicit file, directory, or safe ZIP input; repeat as needed")
    export.add_argument("--output", required=True, help="Output ZIP path")
    export.add_argument("--package-name")
    export.add_argument("--source-platform")
    export.add_argument("--source-agent")
    export.add_argument("--overwrite", action="store_true", help="Explicitly authorize replacing only the output archive")

    inspect = subparsers.add_parser("inspect", help="Inspect package content, integrity, risks, and restorability")
    inspect.add_argument("--package", required=True)
    inspect.add_argument("--report")
    inspect.add_argument("--overwrite", action="store_true")

    restore = subparsers.add_parser("restore", help="Restore to a new target directory without overwriting")
    restore.add_argument("--package", required=True)
    restore.add_argument("--target", required=True)
    restore.add_argument("--target-platform")
    restore.add_argument("--target-agent")

    verify = subparsers.add_parser("verify", help="Verify package SHA-256 and optional restored files")
    verify.add_argument("--package", required=True)
    verify.add_argument("--restored")
    verify.add_argument("--report")
    verify.add_argument("--overwrite", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = command_export(args)
            exit_code = 0
        elif args.command == "inspect":
            result, exit_code = command_inspect(args)
        elif args.command == "restore":
            result = command_restore(args)
            exit_code = 0
        elif args.command == "verify":
            result, exit_code = command_verify(args)
        else:
            raise WorkspaceError("unsupported_command", "Unsupported operation.")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return exit_code
    except WorkspaceError as exc:
        result = {"status": "error", "error": {"code": exc.code, "message": exc.message, "details": exc.details}}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        result = {"status": "error", "error": {"code": "local_operation_failed", "message": "A local file operation failed; no success is claimed.", "details": {}}}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
