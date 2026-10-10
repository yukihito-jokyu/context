#!/usr/bin/env python3
"""Validate the minimal approved directory produced by the candidate archiver."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


APPROVED_PATTERN = re.compile(r"^approved-(\d{3})-run-(\d{3})-([a-z0-9-]+)\.html$")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSONのルートがobjectではありません: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_expected(requirements_input: dict) -> str:
    project = requirements_input["project"]
    requirements = requirements_input["requirements"]
    lines = [
        f"# {project['title']} 承認済み要件",
        "",
        "## 目的",
        "",
        *(f"- {item}" for item in requirements["purpose"]),
        "",
        "## 対象ユーザー",
        "",
        *(f"- {item}" for item in requirements["target_users"]),
        "",
        "## 承認済み要件",
        "",
        *(f"- {item}" for item in requirements["confirmed"]),
        "",
    ]
    return "\n".join(lines)


def validate(approved_dir: Path, source_run: Path, requirements_input_path: Path) -> dict:
    children = sorted(item.name for item in approved_dir.iterdir())
    html_names = [name for name in children if APPROVED_PATTERN.fullmatch(name)]
    only_allowed_files = children == sorted([*html_names, "requirements.md"])
    if not html_names:
        raise ValueError("承認済みHTMLがありません")
    numbered_names = sorted((int(APPROVED_PATTERN.fullmatch(name).group(1)), name) for name in html_names)
    approval_numbers = [number for number, _ in numbered_names]
    sequential_approval_numbers = approval_numbers == list(range(1, len(numbered_names) + 1))
    approved_filename = numbered_names[-1][1]
    match = APPROVED_PATTERN.fullmatch(approved_filename)
    assert match is not None
    _, run_number, slug = match.groups()
    source_html = source_run / "mockups" / f"{run_number}-{slug}.html"
    archived_html = approved_dir / approved_filename
    html_bytes_identical = source_html.read_bytes() == archived_html.read_bytes()

    requirements_input = load_json(requirements_input_path)
    requirements_text = (approved_dir / "requirements.md").read_text(encoding="utf-8")
    requirements_exact = requirements_text == render_expected(requirements_input)
    excluded_sections_absent = all(
        heading not in requirements_text
        for heading in ("## 仮説", "## 未決事項", "## 見送った案", "## 次に確認すること")
    )
    valid = (
        only_allowed_files
        and sequential_approval_numbers
        and html_bytes_identical
        and requirements_exact
        and excluded_sections_absent
    )
    return {
        "valid": valid,
        "children": children,
        "html_count": len(html_names),
        "only_allowed_files": only_allowed_files,
        "sequential_approval_numbers": sequential_approval_numbers,
        "html_bytes_identical": html_bytes_identical,
        "html_sha256": sha256(archived_html),
        "requirements_exact": requirements_exact,
        "excluded_sections_absent": excluded_sections_absent,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--requirements-input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.approved_dir.resolve(), args.source_run.resolve(), args.requirements_input.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise SystemExit(f"Refusing to overwrite: {args.output}")
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
