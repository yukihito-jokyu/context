#!/usr/bin/env python3
"""Render deterministic self-review HTML from validated diff and review JSON."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")
VERDICT_LABELS = {"rule_out": "ルール外", "rule_in": "ルール内", "unknown": "判断不能", "no_rule": "対象ルールなし", "rule_gap": "ルール不足候補"}
CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError(f"schema_version=1.0 のJSONが必要です: {path}")
    return value


def file_path(file: dict[str, Any]) -> str:
    return str(file.get("new_path") or file.get("old_path"))


def relative_source(source: str) -> str:
    path = Path(source)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def stats(file: dict[str, Any]) -> tuple[int, int]:
    additions = deletions = 0
    for hunk in file.get("hunks", []):
        for line in hunk.get("lines", []):
            additions += line.get("kind") == "addition"
            deletions += line.get("kind") == "deletion"
    return additions, deletions


def stat_markup(additions: int, deletions: int) -> str:
    values = []
    if additions:
        values.append(f'<span class="add">+{additions}</span>')
    if deletions:
        values.append(f'<span class="del">−{deletions}</span>')
    return " ".join(values)


def tree_html(files: list[dict[str, Any]]) -> str:
    if not files:
        return '<div class="empty-tree">変更ファイルは<br>ありません</div>'
    root: dict[str, Any] = {}
    for file in files:
        path = file_path(file)
        node = root
        parts = path.split("/")
        for folder in parts[:-1]:
            node = node.setdefault(folder, {})
        node.setdefault("__files__", []).append((parts[-1], file))

    def render_node(node: dict[str, Any]) -> str:
        items = []
        for folder in sorted(key for key in node if key != "__files__"):
            items.append(
                '<li class="tree-folder">'
                '<button class="tree-row tree-folder-toggle" type="button" aria-expanded="true">'
                f'<span class="tree-chevron">▾</span><span>▰</span><span class="tree-label">{esc(folder)}</span>'
                f'</button><ul>{render_node(node[folder])}</ul></li>'
            )
        for name, file in sorted(node.get("__files__", []), key=lambda item: item[0]):
            path = file_path(file)
            additions, deletions = stats(file)
            file_id = f"file-{stable_id(path)}"
            items.append(
                f'<li><button class="tree-row tree-file" type="button" data-target="{file_id}">'
                f'<span class="tree-file-icon">◇</span><span class="tree-label">{esc(name)}</span>'
                f'<span class="tree-stat">{stat_markup(additions, deletions)}</span></button></li>'
            )
        return "".join(items)

    return f'<ul class="tree">{render_node(root)}</ul>'


def line_review_map(
    review: dict[str, Any],
) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    result: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for item in review.get("reviews", []):
        for location in item["locations"]:
            for number in location["lines"]:
                result.setdefault(
                    (location["file"], location["side"], number), []
                ).append(
                    {
                        "review_id": item["review_id"],
                        "verdict": item["verdict"],
                    }
                )
    return result


def diff_html(
    files: list[dict[str, Any]],
    mapping: dict[tuple[str, str, int], list[dict[str, Any]]],
) -> str:
    if not files:
        return '<div class="empty-main"><div class="empty-content"><h1>変更はありません</h1></div></div>'
    rendered = []
    for file in files:
        path = file_path(file)
        additions, deletions = stats(file)
        file_id = f"file-{stable_id(path)}"
        body = []
        if file.get("binary"):
            body.append('<div class="empty-main"><div class="empty-content"><p>バイナリファイルのため行差分は表示できません。</p></div></div>')
        for hunk in file.get("hunks", []):
            body.append(f'<div class="hunk">{esc(hunk["header"])}</div>')
            lines = hunk.get("lines", [])

            def line_location(line: dict[str, Any]) -> tuple[str, int | None]:
                if line["kind"] == "addition":
                    return "new", line.get("new_line")
                if line["kind"] == "deletion":
                    return "old", line.get("old_line")
                return "new", line.get("new_line")

            for index, line in enumerate(lines):
                kind = line["kind"]
                old_number, new_number = line.get("old_line"), line.get("new_line")
                if kind == "addition":
                    side, number, sign = "new", new_number, "+"
                elif kind == "deletion":
                    side, number, sign = "old", old_number, "−"
                else:
                    side, number, sign = "new", new_number, ""
                references = mapping.get((path, side, number), []) if number is not None else []
                review_ids = [reference["review_id"] for reference in references]
                previous_ids: set[str] = set()
                next_ids: set[str] = set()
                if index > 0:
                    previous_side, previous_number = line_location(lines[index - 1])
                    if previous_side == side and previous_number is not None:
                        previous_ids = {
                            reference["review_id"]
                            for reference in mapping.get(
                                (path, previous_side, previous_number), []
                            )
                        }
                if index + 1 < len(lines):
                    next_side, next_number = line_location(lines[index + 1])
                    if next_side == side and next_number is not None:
                        next_ids = {
                            reference["review_id"]
                            for reference in mapping.get(
                                (path, next_side, next_number), []
                            )
                        }
                markers = []
                for reference in references:
                    review_id = reference["review_id"]
                    verdict = reference["verdict"]
                    classes = ["line-review-marker", verdict]
                    if review_id not in previous_ids:
                        classes.append("marker-start")
                    if review_id not in next_ids:
                        classes.append("marker-end")
                    label = f'{VERDICT_LABELS[verdict]}の評価を表示'
                    markers.append(
                        f'<button class="{" ".join(classes)}" type="button" '
                        f'data-review-target="{esc(review_id)}" title="{esc(label)}" '
                        f'aria-label="{esc(label)}"></button>'
                    )
                marker_lane = (
                    '<span class="line-review-markers" aria-label="この行の評価">'
                    f'{"".join(markers)}</span>'
                )
                attrs = f' data-file="{esc(path)}" data-side="{side}" data-number="{number}"'
                if review_ids:
                    attrs += f' data-reviews="{esc(",".join(review_ids))}"'
                body.append(f'<div class="line {kind}"{attrs}>{marker_lane}<span class="ln">{old_number or ""}</span><span class="ln">{new_number or ""}</span><span class="sign">{sign}</span><span class="code">{esc(line.get("text", ""))}</span></div>')
        rendered.append(
            f'<article id="{file_id}" class="file"><button class="file-header" type="button" aria-expanded="true">'
            f'<span class="file-icon">▾</span>{esc(path)}'
            f'<span class="file-stats">{stat_markup(additions, deletions)}</span>'
            f'</button><div class="file-content">{"".join(body)}</div></article>'
        )
    return "".join(rendered)


def review_html(review: dict[str, Any]) -> str:
    rules = {rule["rule_id"]: rule for rule in review.get("rules", [])}
    cards = []
    for item in review.get("reviews", []):
        locations = ", ".join(f'{location["file"]}:{location["line_range"]}' for location in item["locations"])
        selected_rules = [rules[rule_id] for rule_id in item["rule_ids"]]
        title = " / ".join(rule["heading"] for rule in selected_rules) or VERDICT_LABELS[item["verdict"]]
        if selected_rules:
            source_paths = list(
                dict.fromkeys(relative_source(str(rule["source"])) for rule in selected_rules)
            )
            sources = "".join(
                f'<span class="source-item" title="{esc(path)}">{esc(path)}</span>'
                for path in source_paths
            )
            source_search = " ".join(source_paths)
            quotes = "".join(
                f'<blockquote class="quote">{esc(rule["text"])}</blockquote>'
                for rule in selected_rules
            )
        else:
            source_label = (
                "指定ルールに根拠なし"
                if item["verdict"] == "rule_gap"
                else "指定ルールを照合済み"
            )
            sources = f'<span class="source-item">{source_label}</span>'
            source_search = source_label
            quotes = '<blockquote class="quote">該当する承認済みルールなし</blockquote>'
        proposal = '<span class="rule-gap-heading">提案・未承認</span>' if item["verdict"] == "rule_gap" else ""
        suggestion = item["suggestion"] or "なし。"
        search = " ".join([locations, title, source_search, item["reason"], item["suggestion"]])
        cards.append(
            f'<article class="card" data-review-id="{esc(item["review_id"])}" data-verdict="{item["verdict"]}" data-search="{esc(search)}">'
            '<div class="card-top">'
            '<button class="card-toggle" type="button" aria-expanded="true">'
            '<span class="card-chevron">▾</span>'
            f'<span class="badge {item["verdict"]}">{VERDICT_LABELS[item["verdict"]]}</span>'
            f'<span class="range">{esc(locations)}</span>'
            f'<span class="confidence {item["confidence"]}">{CONFIDENCE_LABELS[item["confidence"]]}</span>'
            '</button>'
            '<span class="approved-icon" title="承認済み" aria-label="承認済み">✓</span>'
            '<button class="approve-button" type="button" aria-pressed="false">承認</button>'
            '</div>'
            '<div class="card-body">'
            '<h3 class="section-title">ルールの相対パス</h3>'
            f'<div class="source">{sources}</div>'
            '<h3 class="section-title">ルールの原文</h3>'
            f'{quotes}'
            '<h3 class="section-title">指摘理由</h3>'
            f'{proposal}<p class="reason">{esc(item["reason"])}</p>'
            '<h3 class="section-title">推奨修正方法</h3>'
            f'<p class="suggestion">{esc(suggestion)}</p>'
            '<div class="feedback"><label>この評価への指摘</label><textarea placeholder="補足や修正方針を入力"></textarea></div>'
            '</div></article>'
        )
    if not cards:
        return '<div class="empty-review"><div class="empty-content"><h1>評価はありません</h1></div></div>'
    return "".join(cards)


def render(template: str, diff: dict[str, Any], review: dict[str, Any], shell: bool = False) -> str:
    counts = {key: 0 for key in VERDICT_LABELS}
    for item in review.get("reviews", []):
        counts[item["verdict"]] += 1
    summary = diff["summary"]
    replacements = {
        "__TARGET_HTML__": esc(diff["target"]), "__SOURCE_HTML__": esc(diff["source"]),
        "__TARGET_ATTR__": esc(diff["target"]), "__SOURCE_ATTR__": esc(diff["source"]),
        "__FILES_CHANGED__": str(summary["files_changed"]),
        "__ADDITIONS_STAT_HTML__": f'<span><strong class="add">+{summary["additions"]}</strong></span>' if summary["additions"] else "",
        "__DELETIONS_STAT_HTML__": f'<span><strong class="del">−{summary["deletions"]}</strong></span>' if summary["deletions"] else "",
        "__REVIEW_COUNT__": str(len(review.get("reviews", []))), "__RULE_OUT_COUNT__": str(counts["rule_out"]), "__RULE_IN_COUNT__": str(counts["rule_in"]), "__UNKNOWN_COUNT__": str(counts["unknown"]), "__NO_RULE_COUNT__": str(counts["no_rule"]), "__RULE_GAP_COUNT__": str(counts["rule_gap"]),
        "__FILE_TREE_HTML__": tree_html(diff["files"]),
        "__DIFF_HTML__": diff_html(diff["files"], line_review_map(review)),
        "__REVIEW_HTML__": review_html(review),
        "__DISABLED__": "disabled" if shell else "",
    }
    output = template
    for token in sorted(replacements):
        if output.count(token) == 0:
            raise ValueError(f"テンプレートに必須トークンがありません: {token}")
        output = output.replace(token, replacements[token])
    unresolved = sorted(set(TOKEN_RE.findall(output)))
    if unresolved:
        raise ValueError(f"未置換トークンがあります: {unresolved}")
    return output.replace("\r\n", "\n").replace("\r", "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--shell", action="store_true", help="JSON入力なしの骨組みHTMLを生成する")
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="同じ入力を二度描画してSHA-256が一致することを確認する",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"出力先が既に存在します: {args.output}")
    if args.shell:
        if args.diff or args.review:
            parser.error("--shell と --diff/--review は同時に指定できません")
        diff = {"schema_version": "1.0", "target": "未指定", "source": "未指定", "summary": {"files_changed": 0, "additions": 0, "deletions": 0}, "files": []}
        review = {"schema_version": "1.0", "rules": [], "reviews": []}
    else:
        if not args.diff or not args.review:
            parser.error("通常生成では --diff と --review が必要です")
        diff, review = read_json(args.diff), read_json(args.review)
    template = args.template.read_text(encoding="utf-8")
    output = render(template, diff, review, args.shell)
    if args.verify_determinism:
        reproduced = render(template, diff, review, args.shell)
        output_digest = hashlib.sha256(output.encode()).digest()
        reproduced_digest = hashlib.sha256(reproduced.encode()).digest()
        if output_digest != reproduced_digest:
            raise ValueError("同じ入力から生成したHTMLのSHA-256が一致しません")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
