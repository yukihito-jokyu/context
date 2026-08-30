#!/usr/bin/env python3
"""Validate an immutable generated mock run and its checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_REQUIREMENT_HEADINGS = (
    "## 目的",
    "## 対象ユーザー",
    "## 確定した要件",
    "## 仮説",
    "## 未決事項",
    "## 見送った案",
    "## 次に確認すること",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(run: Path, manifest: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    outputs = manifest.get("outputs")
    checks["manifest_outputs_array"] = isinstance(outputs, list) and bool(outputs)
    if not isinstance(outputs, list):
        return checks
    for item in outputs:
        relative = item.get("path", "") if isinstance(item, dict) else ""
        expected = item.get("sha256", "") if isinstance(item, dict) else ""
        path = run / relative
        key = f"checksum:{relative}"
        checks[key] = path.is_file() and sha256(path) == expected
    return checks


def main() -> None:
    args = parse_args()
    run = args.run.resolve(strict=True)
    manifest_path = run / "manifest.json"
    checks: dict[str, bool] = {
        "manifest_exists": manifest_path.is_file(),
        "requirements_exists": (run / "requirements.md").is_file(),
        "index_exists": (run / "mock-index.html").is_file(),
        "artifact_map_exists": (run / "artifact-map.md").is_file(),
        "generation_validation_exists": (run / "validation.json").is_file(),
    }
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checks["manifest_json"] = False
        else:
            checks["manifest_json"] = True
            checks.update(check_manifest(run, manifest))

    mockups = sorted((run / "mockups").glob("*.html")) if (run / "mockups").is_dir() else []
    checks["one_mock_html"] = len(mockups) == 1
    if mockups:
        source = mockups[0].read_text(encoding="utf-8")
        review_numbers = [
            int(value)
            for value in re.findall(r'class="review-card[^\"]*"[^>]*data-note="(\d+)"', source)
        ]
        fixed_annotation_numbers = [
            int(value) for value in re.findall(r'aria-label="注釈(\d+)の選択範囲"', source)
        ]
        anchored_target_keys = re.findall(r'data-target-key="([a-z0-9-]+)"', source)
        mock_target_keys = re.findall(r'data-review-target="([a-z0-9-]+)"', source)
        screen_detail_numbers = [
            int(value) for value in re.findall(r'data-screen-detail-number="(\d+)"', source)
        ]
        screen_detail_target_keys = re.findall(
            r'data-screen-detail-target-key="([a-z0-9-]+)"', source
        )
        mock_screen_detail_targets = re.findall(
            r'data-screen-detail-target="([a-z0-9-]+)"', source
        )
        checks.update(
            {
                "html5_doctype": source.lower().startswith("<!doctype html>"),
                "feedback_form": 'id="feedback-form"' in source,
                "review_items": 'id="review-items"' in source,
                "area_geometry": all(key in source for key in ("x_percent", "y_percent", "width_percent", "height_percent")),
                "dom_element_selection": all(
                    key in source
                    for key in ("selectableTarget", "addDomSelection", "selectorFor", 'kind:custom?"dom_annotation"')
                ),
                "dom_selection_boundary": all(
                    key in source
                    for key in (
                        "targetRect(target,padding=0)",
                        "alignmentDiagnostic(box,target,0",
                        "targetRect(target,0)",
                        "domSelectionPadding",
                    )
                ),
                "semantic_dom_selection": all(
                    key in source
                    for key in ("textContentTags", "[data-review-target],article,li,tr,td,th,fieldset,details,summary")
                ),
                "focus_settled_alignment": "focusAndRealign" in source
                and "scheduleDomAnnotations" in source,
                "number_reuse": "nextAvailableNumber" in source,
                "number_order": "insertCardInNumberOrder" in source,
                "review_points_not_capped": "最大3件" not in source
                and "今回の確認ポイント" not in source,
                "initial_review_points_sorted": review_numbers == sorted(review_numbers),
                "initial_review_points_unique": len(review_numbers) == len(set(review_numbers)),
                "review_point_history": all(
                    token in source
                    for token in (
                        "status_at_render",
                        "previously_approved",
                        "reopened",
                        "data-history-feedback",
                    )
                ),
                "fixed_annotations_linked": set(fixed_annotation_numbers).issubset(set(review_numbers)),
                "anchored_targets_exist": set(anchored_target_keys).issubset(set(mock_target_keys)),
                "anchored_targets_unique": all(mock_target_keys.count(key) == 1 for key in anchored_target_keys),
                "anchored_runtime_alignment": "placeDomAnnotations" in source
                and "annotationAlignment" in source
                and "annotationErrors" in source,
                "fixed_annotation_focus": 'querySelectorAll(".selection-box")' in source
                and '`#feedback-${number}`' in source
                and '`#history-feedback-${number}`' in source,
                "screen_detail_numbers_consecutive": not screen_detail_numbers
                or screen_detail_numbers == list(range(1, len(screen_detail_numbers) + 1)),
                "screen_detail_keys_unique": len(screen_detail_target_keys)
                == len(set(screen_detail_target_keys)),
                "screen_detail_targets_linked": all(
                    mock_screen_detail_targets.count(key) == 1
                    for key in screen_detail_target_keys
                ),
                "review_mode_tabs": 'id="review-points-tab"' in source
                and 'id="screen-details-tab"' in source,
                "review_mode_isolation": all(
                    token in source
                    for token in (
                        "body[data-review-mode=details] .annotate-toggle",
                        "body[data-review-mode=details] .selection-box",
                        "body[data-review-mode=points] .screen-detail-frame",
                    )
                ),
                "review_mode_colors": "selection-box[data-target-key]" in source
                and "screen-detail-frame" in source,
                "screen_detail_feedback": "screen_detail_feedback" in source
                and "screen_details_approved" in source,
                "legacy_screen_detail_empty_state": bool(screen_detail_numbers)
                or "画面の詳細設計は未入力です" in source,
                "no_external_assets": "https://" not in source and "http://" not in source,
            }
        )

    requirements_path = run / "requirements.md"
    if requirements_path.is_file():
        requirements = requirements_path.read_text(encoding="utf-8")
        checks["requirements_headings"] = all(heading in requirements for heading in REQUIRED_REQUIREMENT_HEADINGS)

    result = {"valid": all(checks.values()), "run": str(run), "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
