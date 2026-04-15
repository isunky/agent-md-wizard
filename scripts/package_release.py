#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
}

EXCLUDE_FILES = {
    ".DS_Store",
    "Thumbs.db",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_git(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError("git command not found - is Git installed and in PATH?") from None
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git {' '.join(args)} failed (exit {e.returncode}): {e.stderr}") from e


def default_version() -> str:
    latest_tag = run_git(["describe", "--tags", "--abbrev=0"])
    if latest_tag:
        return latest_tag
    return "v0.1.0"


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDE_FILES:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def iter_skill_files(skill_dir: Path):
    for path in sorted(skill_dir.rglob("*")):
        if path.is_file() and should_include(path.relative_to(skill_dir)):
            yield path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(version: str, zip_name: str, skill_dir: Path, included_paths: list[str]) -> dict:
    return {
        "name": "agent-md-wizard",
        "version": version,
        "artifact": zip_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/isunky/agent-md-wizard",
        "commit": run_git(["rev-parse", "HEAD"]),
        "commit_short": run_git(["rev-parse", "--short", "HEAD"]),
        "source_dir": str(skill_dir.relative_to(repo_root())).replace("\\", "/"),
        "install_target": "~/.codex/skills/agent-md-wizard",
        "included_files": included_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standard release package for the agent-md-wizard skill.")
    parser.add_argument("--version", default=default_version(), help="Version label used in artifact names, e.g. v0.1.0")
    parser.add_argument(
        "--skill-dir",
        default=str(repo_root() / "skills" / "agent-md-wizard"),
        help="Path to the skill directory to package",
    )
    parser.add_argument(
        "--dist-dir",
        default=str(repo_root() / "dist"),
        help="Output directory for release artifacts",
    )
    args = parser.parse_args()

    version = args.version.strip()
    if not version:
        raise SystemExit("Version must not be empty.")

    skill_dir = Path(args.skill_dir).resolve()
    dist_dir = Path(args.dist_dir).resolve()
    if not skill_dir.exists():
        raise SystemExit(f"Skill directory not found: {skill_dir}")

    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / f"agent-md-wizard-{version}.zip"
    manifest_path = dist_dir / f"agent-md-wizard-{version}-manifest.json"
    sha_path = dist_dir / f"agent-md-wizard-{version}.sha256.txt"

    included_paths: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agent-md-wizard-package-") as temp_dir:
        staging_root = Path(temp_dir) / "agent-md-wizard"
        staging_root.mkdir(parents=True, exist_ok=True)

        for source in iter_skill_files(skill_dir):
            relative = source.relative_to(skill_dir)
            target = staging_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            included_paths.append(f"agent-md-wizard/{relative.as_posix()}")

        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for staged in sorted(staging_root.rglob("*")):
                if staged.is_file():
                    archive.write(staged, staged.relative_to(Path(temp_dir)))

    manifest = build_manifest(version, zip_path.name, skill_dir, included_paths)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sha_path.write_text(f"{sha256_of(zip_path)}  {zip_path.name}\n", encoding="utf-8")

    print(f"Created: {zip_path}")
    print(f"Created: {manifest_path}")
    print(f"Created: {sha_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
