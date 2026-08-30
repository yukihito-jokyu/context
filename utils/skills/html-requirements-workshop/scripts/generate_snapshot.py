#!/usr/bin/env python3
"""Generate an immutable HTML mock snapshot from structured input."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PLACEHOLDERS = (
    "__DOCUMENT_TITLE__",
    "__PROJECT_TITLE__",
    "__PROJECT_SUBTITLE__",
    "__SNAPSHOT_LABEL__",
    "__SNAPSHOT_ID_JSON__",
    "__MOCK_CONTENT__",
    "__REVIEW_CARDS__",
    "__FIXED_ANNOTATIONS__",
    "__SCREEN_DETAIL_CARDS__",
    "__SCREEN_DETAIL_FRAMES__",
)
TARGET_KEY_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
GEOMETRY_KEYS = ("x_percent", "y_percent", "width_percent", "height_percent")
SCREEN_DETAIL_BEHAVIORS = {
    "screen_transition",
    "backend_request",
    "local_state_change",
    "external_navigation",
    "display_only",
}
SCREEN_DETAIL_BEHAVIOR_LABELS = {
    "screen_transition": "画面遷移",
    "backend_request": "バックエンド通信",
    "local_state_change": "画面内の状態変更",
    "external_navigation": "外部ページ表示",
    "display_only": "表示のみ",
}
SCREEN_DETAIL_FIELDS = (
    "region",
    "name",
    "type",
    "description",
    "capability",
    "trigger",
    "result",
    "failure",
)
REVIEW_POINT_STATUSES = {"pending", "approved", "reopened"}


class ReviewTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "data-review-target":
                self.targets.append(value or "")


class ScreenDetailTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "data-screen-detail-target":
                self.targets.append(value or "")


def extract_review_targets(source: str) -> list[str]:
    parser = ReviewTargetParser()
    parser.feed(source)
    parser.close()
    return parser.targets


def extract_screen_detail_targets(source: str) -> list[str]:
    parser = ScreenDetailTargetParser()
    parser.feed(source)
    parser.close()
    return parser.targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_input(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    snapshot = data.get("snapshot")
    project = data.get("project")
    if not isinstance(snapshot, dict) or not isinstance(project, dict):
        raise ValueError("snapshot and project objects are required")
    number = snapshot.get("number")
    slug = snapshot.get("slug")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("snapshot.number must be a positive integer")
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("snapshot.slug must be lowercase kebab-case")
    if not isinstance(data.get("review_points"), list):
        raise ValueError("review_points must be an array")
    if not isinstance(data.get("fixed_annotations"), list):
        raise ValueError("fixed_annotations must be an array")
    points = data["review_points"]
    annotations = data["fixed_annotations"]
    if any(
        not isinstance(point, dict)
        or isinstance(point.get("number"), bool)
        or not isinstance(point.get("number"), int)
        or point["number"] < 1
        for point in points
    ):
        raise ValueError("review point numbers must be positive integers")
    point_numbers = [point["number"] for point in points]
    if len(point_numbers) != len(set(point_numbers)):
        raise ValueError("review point numbers must be unique")
    for point in points:
        status = point.get("status", "pending")
        history = point.get("approval_history", [])
        if status not in REVIEW_POINT_STATUSES:
            raise ValueError("review point status must be pending, approved, or reopened")
        if not isinstance(history, list):
            raise ValueError("review point approval_history must be an array")
        if status in {"approved", "reopened"} and not history:
            raise ValueError("approved and reopened points must preserve approval_history")
        if status == "pending" and history:
            raise ValueError("points with approval_history must use approved or reopened status")
        if any(
            not isinstance(entry, dict)
            or not isinstance(entry.get("approved_in_snapshot"), str)
            or not entry["approved_in_snapshot"]
            or not isinstance(entry.get("title"), str)
            or not entry["title"]
            for entry in history
        ):
            raise ValueError("approval_history entries require approved_in_snapshot and title")
        if any(not isinstance(point.get(field), str) or not point[field].strip() for field in ("title", "description")):
            raise ValueError("review point title and description must be non-empty strings")
    if any(
        not isinstance(item, dict)
        or isinstance(item.get("number"), bool)
        or not isinstance(item.get("number"), int)
        or item["number"] < 1
        for item in annotations
    ):
        raise ValueError("annotation numbers must be positive integers")
    annotation_numbers = [item["number"] for item in annotations]
    if len(annotation_numbers) != len(set(annotation_numbers)):
        raise ValueError("annotation numbers must be unique")
    if not set(annotation_numbers).issubset(set(point_numbers)):
        raise ValueError("each fixed annotation number must match a review point")
    targets = extract_review_targets(str(data.get("mock_html") or ""))
    if any(not TARGET_KEY_PATTERN.fullmatch(target) for target in targets):
        raise ValueError("data-review-target values must be lowercase kebab-case")
    if len(targets) != len(set(targets)):
        raise ValueError("data-review-target values must be unique")
    for item in annotations:
        has_target = "target_key" in item
        geometry_fields = [key in item for key in GEOMETRY_KEYS]
        has_geometry = all(geometry_fields)
        if has_target == has_geometry or (any(geometry_fields) and not has_geometry):
            raise ValueError("each annotation must use either target_key or complete percentage geometry")
        if has_target:
            target_key = item.get("target_key")
            padding = item.get("padding_px", 8)
            if not isinstance(target_key, str) or not TARGET_KEY_PATTERN.fullmatch(target_key):
                raise ValueError("annotation target_key must be lowercase kebab-case")
            if isinstance(padding, bool) or not isinstance(padding, (int, float)) or not 0 <= padding <= 64:
                raise ValueError("annotation padding_px must be a number from 0 to 64")
            if targets.count(target_key) != 1:
                raise ValueError("each annotation target_key must match exactly one data-review-target")
        elif "padding_px" in item:
            raise ValueError("padding_px is only valid with target_key")
    return data


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def safe_mock_html(value: Any) -> str:
    source = str(value or "").strip()
    if not source:
        return (
            '<section class="empty-canvas" aria-label="AIが肉付けする領域">'
            '<div class="empty-icon" aria-hidden="true">◇</div>'
            '<h1>画面内容の入力待ち</h1>'
            '<p>ここへAIがユーザーとの会話に基づく画面モックを配置します。</p>'
            '<div class="placeholder-row"><span></span><span></span><span></span></div>'
            '</section>'
        )
    lowered = source.lower()
    forbidden = ("<script", "<iframe", "<object", "<embed", "javascript:")
    if any(token in lowered for token in forbidden) or re.search(r"\son[a-z]+\s*=", lowered):
        raise ValueError("mock_html contains forbidden active content")
    return source


def validate_screen_details(data: dict[str, Any], mock_html: str) -> list[dict[str, Any]]:
    details = data.get("screen_details", [])
    if not isinstance(details, list):
        raise ValueError("screen_details must be an array")
    targets = extract_screen_detail_targets(mock_html)
    if any(not TARGET_KEY_PATTERN.fullmatch(value) for value in targets):
        raise ValueError("data-screen-detail-target values must be lowercase kebab-case")
    if len(targets) != len(set(targets)):
        raise ValueError("data-screen-detail-target values must be unique")
    numbers: list[int] = []
    keys: list[str] = []
    linked_targets: list[str] = []
    for detail in details:
        if not isinstance(detail, dict):
            raise ValueError("each screen detail must be an object")
        number = detail.get("number")
        key = detail.get("key")
        target_key = detail.get("target_key")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValueError("screen detail numbers must be positive integers")
        if not isinstance(key, str) or not TARGET_KEY_PATTERN.fullmatch(key):
            raise ValueError("screen detail keys must be lowercase kebab-case")
        if not isinstance(target_key, str) or not TARGET_KEY_PATTERN.fullmatch(target_key):
            raise ValueError("screen detail target_key must be lowercase kebab-case")
        if targets.count(target_key) != 1:
            raise ValueError("each screen detail must match one data-screen-detail-target")
        if detail.get("behavior") not in SCREEN_DETAIL_BEHAVIORS:
            raise ValueError("screen detail behavior is invalid")
        if any(
            not isinstance(detail.get(field), str) or not detail[field].strip()
            for field in SCREEN_DETAIL_FIELDS
        ):
            raise ValueError("screen detail text fields must be non-empty strings")
        numbers.append(number)
        keys.append(key)
        linked_targets.append(target_key)
    if len(numbers) != len(set(numbers)) or sorted(numbers) != list(range(1, len(numbers) + 1)):
        raise ValueError("screen detail numbers must be consecutive from 1")
    if len(keys) != len(set(keys)):
        raise ValueError("screen detail keys must be unique")
    if len(linked_targets) != len(set(linked_targets)):
        raise ValueError("screen detail target_key values must be unique")
    return sorted(details, key=lambda item: item["number"])


def render_screen_detail_cards(details: list[dict[str, Any]]) -> str:
    if not details:
        return (
            '<section class="screen-detail-empty">'
            '<strong>画面の詳細設計は未入力です</strong>'
            '<p>意味のある画面項目を入力すると、件数制限なく表示されます。</p>'
            '</section>'
        )
    labels = (
        ("できること", "capability"),
        ("処理種別", "behavior"),
        ("きっかけ", "trigger"),
        ("結果", "result"),
        ("失敗時", "failure"),
    )
    cards: list[str] = []
    for index, detail in enumerate(details):
        number = detail["number"]
        expanded = index == 0
        rows = "".join(
            f'<dt>{escape(label)}</dt><dd>{escape(SCREEN_DETAIL_BEHAVIOR_LABELS[detail[field]] if field == "behavior" else detail[field])}</dd>'
            for label, field in labels
        )
        cards.append(
            f'<article class="screen-detail-card" data-screen-detail-number="{number}" '
            f'data-screen-detail-key="{escape(detail["key"])}" '
            f'data-screen-detail-target-key="{escape(detail["target_key"])}">'
            f'<button class="screen-detail-summary" type="button" aria-expanded="{str(expanded).lower()}">'
            f'<span class="detail-sequence">{number}</span><span class="detail-meta">'
            f'<span>{escape(detail["region"])}</span><span>{escape(detail["type"])}</span>'
            f'</span><strong>{escape(detail["name"])}</strong>'
            f'<small>{escape(detail["description"])}</small></button>'
            f'<div class="screen-detail-content"{"" if expanded else " hidden"}><dl>{rows}</dl>'
            f'<label for="screen-detail-feedback-{number}">この設計へのフィードバック</label>'
            f'<textarea id="screen-detail-feedback-{number}" data-screen-detail-comment="{escape(detail["key"])}"></textarea>'
            '</div></article>'
        )
    return "\n".join(cards)


def render_screen_detail_frames(details: list[dict[str, Any]]) -> str:
    return "\n".join(
        f'<div class="screen-detail-frame" data-screen-detail-frame="{escape(item["target_key"])}">'
        f'<span class="screen-detail-frame-number">{item["number"]}</span></div>'
        for item in details
    )


def render_review_cards(points: list[Any]) -> str:
    normalized: list[dict[str, Any]] = []
    used: set[int] = set()
    for point in sorted(points, key=lambda item: item["number"]):
        if not isinstance(point, dict):
            raise ValueError("each review point must be an object")
        number = point.get("number")
        if not isinstance(number, int) or number < 1 or number in used:
            raise ValueError("review point numbers must be unique positive integers")
        used.add(number)
        normalized.append(point)
    if normalized:
        history_points = [point for point in normalized if point.get("approval_history")]
        new_points = [point for point in normalized if not point.get("approval_history")]
        sections: list[str] = []
        groups = (
            (("確認ポイント", normalized, ""),)
            if history_points
            and new_points
            and max(point["number"] for point in history_points)
            > min(point["number"] for point in new_points)
            else (
                ("承認履歴あり", history_points, ""),
                ("新しい確認ポイント", new_points, " approved-title"),
            )
        )
        for label, group, extra_class in groups:
            if not group:
                continue
            sections.append(
                f'<h3 class="review-section-title{extra_class}">{label} '
                f'<span>{len(group)}件</span></h3>'
            )
            for point in group:
                number = point["number"]
                status = point.get("status", "pending")
                history = point.get("approval_history", [])
                title = escape(point["title"])
                description = escape(point["description"])
                latest_feedback = escape(point.get("latest_feedback", ""))
                history_attr = ' data-history-approved="true"' if history else ""
                heading = (
                    f'<div class="card-heading"><span class="number">{number}</span><div>'
                    f'<h3>{title}</h3><p>{description}</p></div></div>'
                )
                if status == "approved":
                    sections.append(
                        f'<section class="review-card history-card approved" data-note="{number}" '
                        f'data-status="approved"{history_attr}>{heading}'
                        '<div class="approval-history">✓ 承認済み</div>'
                        f'<label for="history-feedback-{number}">追加の指摘</label>'
                        f'<textarea id="history-feedback-{number}" data-history-feedback '
                        'placeholder="承認内容を見直したい場合に入力してください"></textarea></section>'
                    )
                elif status == "reopened":
                    sections.append(
                        f'<section class="review-card history-card reopened" data-note="{number}" '
                        f'data-status="reopened"{history_attr}>{heading}'
                        '<div class="approval-history">↻ 追加指摘あり・再確認中</div>'
                        f'<label for="history-feedback-{number}">追加の指摘</label>'
                        f'<textarea id="history-feedback-{number}" data-history-feedback>{latest_feedback}</textarea>'
                        '<div class="card-actions"><span></span><button class="approve" type="button" '
                        'aria-pressed="false">修正版を承認</button></div></section>'
                    )
                else:
                    sections.append(
                        f'<section class="review-card" data-note="{number}" data-status="pending">{heading}'
                        f'<label for="feedback-{number}">この項目へのフィードバック</label>'
                        f'<textarea id="feedback-{number}"></textarea>'
                        '<div class="card-actions"><span></span>'
                        '<button class="approve" type="button" aria-pressed="false">承認</button></div>'
                        '</section>'
                    )
        return "\n".join(sections)
    return (
        '<section class="review-empty">'
        '<strong>確認ポイントは未入力です</strong>'
        '<p>ユーザー判断が必要な項目がある場合、LLMが確認ポイントを追加します。</p>'
        '</section>'
    )


def render_annotations(annotations: list[Any]) -> str:
    rendered: list[str] = []
    for item in sorted(annotations, key=lambda annotation: annotation["number"]):
        if not isinstance(item, dict):
            raise ValueError("each annotation must be an object")
        number = int(item["number"])
        if "target_key" in item:
            target_key = escape(item["target_key"])
            padding = float(item.get("padding_px", 8))
            rendered.append(
                f'<button class="selection-box" type="button" data-target-key="{target_key}" '
                f'data-padding="{padding:.2f}" aria-label="注釈{number}の選択範囲">'
                f'<span class="selection-number">{number}</span></button>'
            )
            continue
        values = [float(item[key]) for key in GEOMETRY_KEYS]
        if number < 1 or any(value < 0 or value > 100 for value in values):
            raise ValueError("annotation number and geometry are invalid")
        x, y, width, height = values
        if width <= 0 or height <= 0 or x + width > 100 or y + height > 100:
            raise ValueError("annotation rectangle must fit inside the canvas")
        rendered.append(
            f'<button class="selection-box" type="button" '
            f'style="left:{x:.2f}%;top:{y:.2f}%;width:{width:.2f}%;height:{height:.2f}%" '
            f'aria-label="注釈{number}の選択範囲"><span class="selection-number">{number}</span></button>'
        )
    return "\n".join(rendered)


def markdown_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "- 未入力"
    return "\n".join(f"- {value}" for value in values)


def render_requirements(data: dict[str, Any], snapshot_id: str) -> str:
    req = data.get("requirements") or {}
    sections = (
        ("目的", "purpose"),
        ("対象ユーザー", "target_users"),
        ("確定した要件", "confirmed"),
        ("仮説", "hypotheses"),
        ("未決事項", "open_questions"),
        ("見送った案", "deferred"),
        ("次に確認すること", "next"),
    )
    chunks = [f"# {data['project']['title']} 要件メモ", "", f"最終更新: {snapshot_id}"]
    for title, key in sections:
        chunks.extend(("", f"## {title}", "", markdown_list(req.get(key))))
    return "\n".join(chunks) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve(strict=True)
    template_path = args.template.resolve(strict=True)
    output = args.output.resolve()
    data = load_input(input_path)
    mock_content = safe_mock_html(data.get("mock_html"))
    screen_details = validate_screen_details(data, mock_content)
    review_cards = render_review_cards(data["review_points"])
    fixed_annotations = render_annotations(data["fixed_annotations"])
    screen_detail_cards = render_screen_detail_cards(screen_details)
    screen_detail_frames = render_screen_detail_frames(screen_details)
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to write into non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    mockups = output / "mockups"
    mockups.mkdir()
    snapshot = data["snapshot"]
    snapshot_id = f"{snapshot['number']:03d}-{snapshot['slug']}"
    filename = f"{snapshot_id}.html"
    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "__DOCUMENT_TITLE__": escape(f"{data['project']['title']} {snapshot_id}"),
        "__PROJECT_TITLE__": escape(data["project"].get("title", "画面すり合わせモック")),
        "__PROJECT_SUBTITLE__": escape(data["project"].get("subtitle", "")),
        "__SNAPSHOT_LABEL__": escape(f"Snapshot {snapshot['number']:03d} · {snapshot.get('label', snapshot['slug'])}"),
        "__SNAPSHOT_ID_JSON__": json.dumps(snapshot_id, ensure_ascii=False),
        "__MOCK_CONTENT__": mock_content,
        "__REVIEW_CARDS__": review_cards,
        "__FIXED_ANNOTATIONS__": fixed_annotations,
        "__SCREEN_DETAIL_CARDS__": screen_detail_cards,
        "__SCREEN_DETAIL_FRAMES__": screen_detail_frames,
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    unresolved = [placeholder for placeholder in PLACEHOLDERS if placeholder in template]
    if unresolved:
        raise ValueError(f"unresolved placeholders: {unresolved}")

    mock_path = mockups / filename
    mock_path.write_text(template, encoding="utf-8")
    requirements_path = output / "requirements.md"
    requirements_path.write_text(render_requirements(data, snapshot_id), encoding="utf-8")
    index_path = output / "mock-index.html"
    index_path.write_text(
        '<!doctype html><html lang="ja"><meta charset="utf-8">'
        f'<title>{escape(data["project"]["title"])} モック一覧</title>'
        '<style>body{max-width:720px;margin:48px auto;padding:0 20px;color:#252e36;background:#d9dde1;font-family:sans-serif}'
        'main{padding:28px;border:1px solid #aab2b9;border-radius:12px;background:#fff}a{color:#356f9d;font-weight:700}</style>'
        f'<main><h1>{escape(data["project"]["title"])} モック一覧</h1>'
        f'<p><a href="./mockups/{filename}">{escape(snapshot_id)} · {escape(snapshot.get("label", ""))}</a></p></main></html>\n',
        encoding="utf-8",
    )
    artifact_map_path = output / "artifact-map.md"
    artifact_map_path.write_text(
        "# 成果物対応表\n\n"
        "| 成果物 | 入力 | 生成責務 |\n|---|---|---|\n"
        f"| `mockups/{filename}` | project、mock_html、review_points、fixed_annotations、screen_details | 2つの確認モードをテンプレートへ決定論的に配置 |\n"
        "| `requirements.md` | requirements | 固定見出しでMarkdown化 |\n"
        f"| `mock-index.html` | snapshot、project | `{filename}`へのリンクを生成 |\n"
        "| `validation.json` | 全生成物 | 必須構造とファイル存在を検証 |\n"
        "| `manifest.json` | 入力、テンプレート、全生成物 | SHA-256を記録 |\n",
        encoding="utf-8",
    )

    validation = {
        "valid": True,
        "checks": {
            "self_contained_html": "<script>" in template and "<style>" in template,
            "feedback_form": 'id="feedback-form"' in template,
            "area_annotations": "width_percent" in template and "height_percent" in template,
            "number_reuse": "nextAvailableNumber" in template,
            "review_points_not_capped": len(
                re.findall(r'class="review-card[^\"]*"[^>]*data-note="(\d+)"', template)
            )
            == len(data["review_points"]),
            "review_point_history": all(
                token in template
                for token in ("status_at_render", "previously_approved", "reopened", "data-history-feedback")
            ),
            "screen_details_not_capped": len(screen_details) == len(data.get("screen_details", [])),
            "screen_detail_numbers": [
                int(value) for value in re.findall(r'data-screen-detail-number="(\d+)"', template)
            ]
            == list(range(1, len(screen_details) + 1)),
            "screen_detail_targets_linked": all(
                template.count(f'data-screen-detail-target="{item["target_key"]}"') == 1
                for item in screen_details
            ),
            "review_modes": 'id="review-points-tab"' in template
            and 'id="screen-details-tab"' in template
            and "renderReviewMode" in template,
            "mode_specific_frames": "placeScreenDetailFrames" in template
            and "body[data-review-mode=details] .annotate-toggle" in template,
            "separate_screen_detail_feedback": "screen_detail_feedback" in template
            and "screen_details_approved" in template,
            "review_points_preserved": sorted(
                int(value)
                for value in re.findall(r'class="review-card[^\"]*"[^>]*data-note="(\d+)"', template)
            )
            == sorted(point["number"] for point in data["review_points"]),
            "fixed_annotations_linked": set(item["number"] for item in data["fixed_annotations"])
            .issubset(set(point["number"] for point in data["review_points"])),
            "anchored_annotations_linked": all(
                item.get("target_key") in extract_review_targets(mock_content)
                for item in data["fixed_annotations"]
                if "target_key" in item
            ),
            "anchored_annotation_runtime": "placeDomAnnotations" in template
            and "annotationAlignment" in template
            and "annotationErrors" in template,
            "dom_element_selection": all(
                key in template
                for key in ("selectableTarget", "addDomSelection", "selectorFor", 'kind:custom?"dom_annotation"')
            ),
            "dom_selection_boundary": all(
                key in template
                for key in (
                    "targetRect(target,padding=0)",
                    "alignmentDiagnostic(box,target,0",
                    "targetRect(target,0)",
                    "domSelectionPadding",
                )
            ),
            "semantic_dom_selection": all(
                key in template
                for key in ("textContentTags", "[data-review-target],article,li,tr,td,th,fieldset,details,summary")
            ),
            "focus_settled_alignment": "focusAndRealign" in template
            and "scheduleDomAnnotations" in template,
            "fixed_annotation_focus": 'querySelectorAll(".selection-box")' in template
            and '`#feedback-${number}`' in template,
            "requirements_created": requirements_path.exists(),
            "index_created": index_path.exists(),
        },
    }
    validation["valid"] = all(validation["checks"].values())
    validation_path = output / "validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not validation["valid"]:
        raise SystemExit("generated output failed validation")

    generated = [mock_path, requirements_path, index_path, artifact_map_path, validation_path]
    manifest = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "input": {"path": str(input_path), "sha256": sha256(input_path)},
        "template": {"path": str(template_path), "sha256": sha256(template_path)},
        "outputs": [
            {"path": str(path.relative_to(output)), "sha256": sha256(path)} for path in sorted(generated)
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot_id": snapshot_id, "output": str(output), "files": 6}, ensure_ascii=False))


if __name__ == "__main__":
    main()
