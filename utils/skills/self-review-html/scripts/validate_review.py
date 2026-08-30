#!/usr/bin/env python3
"""Validate and normalize AI review JSON against collected changed lines."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERDICTS = {"rule_in", "rule_out", "unknown", "no_rule"}
CONFIDENCE = {"high", "medium", "low"}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSONのルートはobjectである必要があります: {path}")
    return value


def compact(numbers: list[int]) -> str:
    if not numbers:
        return ""
    result: list[str] = []
    start = end = numbers[0]
    for number in numbers[1:]:
        if number == end + 1:
            end = number
        else:
            result.append(str(start) if start == end else f"{start}-{end}")
            start = end = number
    result.append(str(start) if start == end else f"{start}-{end}")
    return ",".join(result)


def changed_lines(diff: dict[str, Any]) -> dict[tuple[str, str], set[int]]:
    result: dict[tuple[str, str], set[int]] = {}
    for file in diff.get("files", []):
        old_path, new_path = file.get("old_path"), file.get("new_path")
        if old_path:
            result[(old_path, "old")] = set()
        if new_path:
            result[(new_path, "new")] = set()
        for hunk in file.get("hunks", []):
            for line in hunk.get("lines", []):
                if line.get("kind") == "addition" and new_path:
                    result[(new_path, "new")].add(line["new_line"])
                elif line.get("kind") == "deletion" and old_path:
                    result[(old_path, "old")].add(line["old_line"])
    return result


def source_allowed(source: str, allowed: list[Path]) -> bool:
    if not allowed:
        return True
    resolved = Path(source).resolve()
    for item in allowed:
        root = item.resolve()
        if resolved == root or (root.is_dir() and resolved.is_relative_to(root)):
            return True
    return False


def normalize(diff: dict[str, Any], review: dict[str, Any], allowed: list[Path], require_complete: bool) -> dict[str, Any]:
    if review.get("schema_version") != "1.0":
        raise ValueError("review.schema_version は 1.0 である必要があります")
    available = changed_lines(diff)
    rules = review.get("rules")
    reviews = review.get("reviews")
    if not isinstance(rules, list) or not isinstance(reviews, list):
        raise ValueError("rules と reviews は配列である必要があります")

    rule_ids: set[str] = set()
    normalized_rules: list[dict[str, Any]] = []
    for rule in rules:
        required = {"rule_id", "skill", "source", "heading", "text"}
        if not isinstance(rule, dict) or not required.issubset(rule):
            raise ValueError("各ruleには rule_id, skill, source, heading, text が必要です")
        rule_id = str(rule["rule_id"])
        if not rule_id or rule_id in rule_ids:
            raise ValueError(f"rule_id が空または重複しています: {rule_id}")
        if not source_allowed(str(rule["source"]), allowed):
            raise ValueError(f"指定外のルール出典です: {rule['source']}")
        rule_ids.add(rule_id)
        normalized_rules.append({key: rule[key] for key in sorted(rule)})

    covered: set[tuple[str, str, int]] = set()
    normalized_reviews: list[dict[str, Any]] = []
    for item in reviews:
        required = {"verdict", "rule_ids", "locations", "reason", "suggestion", "confidence"}
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"reviewの必須キーが不足しています: {required}")
        verdict = item["verdict"]
        confidence = item["confidence"]
        refs = item["rule_ids"]
        if verdict not in VERDICTS or confidence not in CONFIDENCE:
            raise ValueError(f"verdictまたはconfidenceが不正です: {verdict}, {confidence}")
        if not isinstance(refs, list) or any(ref not in rule_ids for ref in refs):
            raise ValueError("review.rule_ids に未定義のIDがあります")
        if verdict in {"rule_in", "rule_out"} and not refs:
            raise ValueError(f"{verdict} にはrule_idsが必要です")
        if verdict == "no_rule" and refs:
            raise ValueError("no_rule のrule_idsは空にしてください")

        locations = item["locations"]
        if not isinstance(locations, list) or not locations:
            raise ValueError("review.locations は空でない配列である必要があります")
        normalized_locations = []
        for location in locations:
            if not isinstance(location, dict) or not {"file", "side", "lines"}.issubset(location):
                raise ValueError("locationには file, side, lines が必要です")
            key = (str(location["file"]), str(location["side"]))
            numbers = sorted(set(location["lines"])) if isinstance(location["lines"], list) else []
            if key not in available or not numbers or any(not isinstance(value, int) or value not in available[key] for value in numbers):
                raise ValueError(f"差分に存在しない行範囲です: {key} {numbers}")
            covered.update((key[0], key[1], number) for number in numbers)
            normalized_locations.append({"file": key[0], "side": key[1], "lines": numbers, "line_range": compact(numbers)})

        seed = json.dumps({"verdict": verdict, "rule_ids": refs, "locations": normalized_locations, "reason": item["reason"]}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        normalized_reviews.append({
            "review_id": f"review-{hashlib.sha256(seed.encode()).hexdigest()[:12]}",
            "verdict": verdict,
            "rule_ids": refs,
            "locations": normalized_locations,
            "reason": str(item["reason"]),
            "suggestion": str(item["suggestion"]),
            "confidence": confidence,
        })

    expected = {(file, side, number) for (file, side), numbers in available.items() for number in numbers}
    missing = sorted(expected - covered)
    if require_complete and missing:
        preview = ", ".join(f"{file}:{side}:{line}" for file, side, line in missing[:10])
        raise ValueError(f"評価されていない変更行があります: {preview}")
    return {"schema_version": "1.0", "rules": normalized_rules, "reviews": normalized_reviews}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--allowed-source", action="append", default=[], type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"出力先が既に存在します: {args.output}")
    result = normalize(read_json(args.diff), read_json(args.review), args.allowed_source, not args.allow_incomplete)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
