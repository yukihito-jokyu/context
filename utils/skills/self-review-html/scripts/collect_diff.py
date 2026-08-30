#!/usr/bin/env python3
"""Collect a PR-style Git diff as deterministic JSON without changing Git state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} に失敗しました: {message}")
    return result.stdout if binary else result.stdout.decode("utf-8", errors="replace")


def resolve_repo(path: Path) -> Path:
    root = str(git(path, "rev-parse", "--show-toplevel")).strip()
    return Path(root).resolve()


def resolve_commit(repo: Path, ref: str) -> str:
    return str(git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")).strip()


def name_status(repo: Path, args: list[str]) -> list[tuple[str, str, str]]:
    raw = bytes(git(repo, *args, "--name-status", "-z", "--find-renames", binary=True))
    parts = raw.decode("utf-8", errors="surrogateescape").split("\0")
    if parts and parts[-1] == "":
        parts.pop()
    files: list[tuple[str, str, str]] = []
    index = 0
    while index < len(parts):
        status = parts[index]
        index += 1
        if status.startswith(("R", "C")):
            old_path, new_path = parts[index], parts[index + 1]
            index += 2
        else:
            old_path = new_path = parts[index]
            index += 1
        files.append((status, old_path, new_path))
    return files


def parse_patch(patch: str) -> tuple[bool, list[dict[str, Any]]]:
    if "GIT binary patch" in patch or "Binary files " in patch:
        return True, []
    hunks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    old_line = new_line = 0
    for raw_line in patch.splitlines():
        match = HUNK_RE.match(raw_line)
        if match:
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            current = {
                "header": raw_line,
                "old_start": old_line,
                "old_count": int(match.group(2) or "1"),
                "new_start": new_line,
                "new_count": int(match.group(4) or "1"),
                "section": match.group(5).strip(),
                "lines": [],
            }
            hunks.append(current)
            continue
        if current is None or not raw_line or raw_line[0] not in " +-\\":
            continue
        prefix, text = raw_line[0], raw_line[1:]
        if prefix == "+":
            current["lines"].append({"kind": "addition", "old_line": None, "new_line": new_line, "text": text})
            new_line += 1
        elif prefix == "-":
            current["lines"].append({"kind": "deletion", "old_line": old_line, "new_line": None, "text": text})
            old_line += 1
        elif prefix == " ":
            current["lines"].append({"kind": "context", "old_line": old_line, "new_line": new_line, "text": text})
            old_line += 1
            new_line += 1
        elif current["lines"]:
            current["lines"][-1]["no_newline"] = True
    return False, hunks


def untracked_file(repo: Path, relative: str) -> dict[str, Any]:
    path = repo / relative
    raw = path.read_bytes()
    binary = b"\0" in raw[:8192]
    hunks: list[dict[str, Any]] = []
    if not binary:
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if lines:
            hunks.append({
                "header": f"@@ -0,0 +1,{len(lines)} @@",
                "old_start": 0,
                "old_count": 0,
                "new_start": 1,
                "new_count": len(lines),
                "section": "",
                "lines": [
                    {"kind": "addition", "old_line": None, "new_line": number, "text": value}
                    for number, value in enumerate(lines, 1)
                ],
            })
    return {"status": "A", "old_path": None, "new_path": relative, "binary": binary, "hunks": hunks}


def collect(repo_path: Path, target: str, source: str) -> dict[str, Any]:
    repo = resolve_repo(repo_path)
    target_commit = resolve_commit(repo, target)
    mode = source.upper()
    if mode in {"WORKTREE", "STAGED"}:
        source_commit = resolve_commit(repo, "HEAD")
        source_label = mode
    else:
        source_commit = resolve_commit(repo, source)
        source_label = source
        mode = "COMMIT"
    merge_base = str(git(repo, "merge-base", target_commit, source_commit)).strip()

    if mode == "COMMIT":
        diff_args = ["diff", merge_base, source_commit]
    elif mode == "STAGED":
        diff_args = ["diff", "--cached", merge_base]
    else:
        diff_args = ["diff", merge_base]

    files: list[dict[str, Any]] = []
    for status, old_path, new_path in name_status(repo, diff_args):
        paths = [old_path] if old_path == new_path else [old_path, new_path]
        patch = str(git(repo, *diff_args, "--no-color", "--no-ext-diff", "--unified=3", "--", *paths))
        binary, hunks = parse_patch(patch)
        files.append({
            "status": status,
            "old_path": None if status.startswith("A") else old_path,
            "new_path": None if status.startswith("D") else new_path,
            "binary": binary,
            "hunks": hunks,
        })

    if mode == "WORKTREE":
        raw = bytes(git(repo, "ls-files", "--others", "--exclude-standard", "-z", binary=True))
        untracked = sorted(item for item in raw.decode("utf-8", errors="surrogateescape").split("\0") if item)
        files.extend(untracked_file(repo, path) for path in untracked)

    additions = sum(1 for file in files for hunk in file["hunks"] for line in hunk["lines"] if line["kind"] == "addition")
    deletions = sum(1 for file in files for hunk in file["hunks"] for line in hunk["lines"] if line["kind"] == "deletion")
    return {
        "schema_version": "1.0",
        "repository": repo.name,
        "target": target,
        "target_commit": target_commit,
        "source": source_label,
        "source_commit": source_commit,
        "mode": mode,
        "merge_base": merge_base,
        "summary": {"files_changed": len(files), "additions": additions, "deletions": deletions},
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--target", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"出力先が既に存在します: {args.output}")
    result = collect(args.repo, args.target, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
