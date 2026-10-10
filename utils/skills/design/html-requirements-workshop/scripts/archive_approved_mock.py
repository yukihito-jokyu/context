#!/usr/bin/env python3
"""Archive one fully approved HTML mock and refresh the single approved requirements file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


SNAPSHOT_PATTERN = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
APPROVED_PATTERN = re.compile(r"^approved-(\d{3})-run-(\d{3})-([a-z0-9-]+)\.html$")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSONを読み込めません: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSONのルートはobjectである必要があります: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label}は空でない文字列の配列である必要があります")
    return value


def render_requirements(requirements_input: dict) -> str:
    project = requirements_input.get("project")
    requirements = requirements_input.get("requirements")
    if not isinstance(project, dict) or not isinstance(project.get("title"), str) or not project["title"]:
        raise ValueError("requirements inputのproject.titleが不正です")
    if not isinstance(requirements, dict):
        raise ValueError("requirements inputのrequirementsが不正です")

    purpose = require_string_list(requirements.get("purpose"), "requirements.purpose")
    target_users = require_string_list(requirements.get("target_users"), "requirements.target_users")
    confirmed = require_string_list(requirements.get("confirmed"), "requirements.confirmed")

    lines = [
        f"# {project['title']} 承認済み要件",
        "",
        "## 目的",
        "",
        *(f"- {item}" for item in purpose),
        "",
        "## 対象ユーザー",
        "",
        *(f"- {item}" for item in target_users),
        "",
        "## 承認済み要件",
        "",
        *(f"- {item}" for item in confirmed),
        "",
    ]
    return "\n".join(lines)


def validate_inputs(run: Path, feedback_path: Path, requirements_input_path: Path) -> tuple[Path, str, str, str]:
    manifest = load_json(run / "manifest.json")
    feedback = load_json(feedback_path)
    requirements_input = load_json(requirements_input_path)

    snapshot_id = manifest.get("snapshot_id")
    match = SNAPSHOT_PATTERN.fullmatch(snapshot_id) if isinstance(snapshot_id, str) else None
    if match is None:
        raise ValueError("manifestのsnapshot_idが不正です")
    run_number, slug = match.groups()
    if feedback.get("snapshot_id") != snapshot_id:
        raise ValueError("feedbackとrunのsnapshot_idが一致しません")

    items = feedback.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("feedback.itemsが空です")
    if any(not isinstance(item, dict) or item.get("approved") is not True for item in items):
        raise ValueError("未承認の確認項目または指摘が残っています")

    screen_details = requirements_input.get("screen_details", [])
    if not isinstance(screen_details, list):
        raise ValueError("requirements inputのscreen_detailsが不正です")
    if screen_details and feedback.get("screen_details_approved") is not True:
        raise ValueError("画面の詳細設計が一括承認されていません")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError("manifest.outputsが不正です")
    html_outputs = [item for item in outputs if isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"].startswith("mockups/") and item["path"].endswith(".html")]
    if len(html_outputs) != 1:
        raise ValueError("manifestにはmockups配下のHTMLが1件必要です")
    html_record = html_outputs[0]
    relative_html = Path(html_record["path"])
    if relative_html.is_absolute() or ".." in relative_html.parts:
        raise ValueError("manifestのHTMLパスが不正です")
    source_html = run / relative_html
    if not source_html.is_file():
        raise ValueError("承認元HTMLが存在しません")
    if not isinstance(html_record.get("sha256"), str) or sha256(source_html) != html_record["sha256"]:
        raise ValueError("承認元HTMLのチェックサムがmanifestと一致しません")

    input_snapshot = requirements_input.get("snapshot")
    if not isinstance(input_snapshot, dict) or not isinstance(input_snapshot.get("number"), int):
        raise ValueError("requirements inputのsnapshotが不正です")
    return source_html, run_number, slug, snapshot_id


def archive(run: Path, feedback: Path, requirements_input: Path, approved_dir: Path) -> dict:
    source_html, run_number, slug, snapshot_id = validate_inputs(run, feedback, requirements_input)

    existing_numbers: list[int] = []
    if approved_dir.exists():
        if not approved_dir.is_dir():
            raise ValueError("approved-dirはディレクトリである必要があります")
        for child in approved_dir.iterdir():
            if child.name == "requirements.md" and child.is_file():
                continue
            match = APPROVED_PATTERN.fullmatch(child.name) if child.is_file() else None
            if match is None:
                raise ValueError(f"approved-dirに許可されていない項目があります: {child.name}")
            approval_number, archived_run_number, _ = match.groups()
            existing_numbers.append(int(approval_number))
            if archived_run_number == run_number:
                raise ValueError(f"run-{run_number}はすでに承認済みです")

    approval_number = max(existing_numbers, default=0) + 1
    approved_filename = f"approved-{approval_number:03d}-run-{run_number}-{slug}.html"
    destination_html = approved_dir / approved_filename
    requirements_text = render_requirements(load_json(requirements_input))

    approved_dir.parent.mkdir(parents=True, exist_ok=True)
    staged_html: Path | None = None
    staged_requirements: Path | None = None
    html_committed = False
    try:
        with tempfile.NamedTemporaryFile(dir=approved_dir.parent, prefix="approved-html-", delete=False) as handle:
            staged_html = Path(handle.name)
        shutil.copyfile(source_html, staged_html)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=approved_dir.parent, prefix="approved-requirements-", delete=False
        ) as handle:
            handle.write(requirements_text)
            staged_requirements = Path(handle.name)

        approved_dir.mkdir(exist_ok=True)
        os.replace(staged_html, destination_html)
        staged_html = None
        html_committed = True
        os.replace(staged_requirements, approved_dir / "requirements.md")
        staged_requirements = None
    except Exception:
        if html_committed and destination_html.exists():
            destination_html.unlink()
        raise
    finally:
        for staged in (staged_html, staged_requirements):
            if staged is not None and staged.exists():
                staged.unlink()

    return {
        "valid": True,
        "snapshot_id": snapshot_id,
        "approved_filename": approved_filename,
        "html_sha256": sha256(destination_html),
        "requirements_filename": "requirements.md",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--feedback", type=Path, required=True)
    parser.add_argument("--requirements-input", type=Path, required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = archive(
            args.run.resolve(),
            args.feedback.resolve(),
            args.requirements_input.resolve(),
            args.approved_dir.resolve(),
        )
    except ValueError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
