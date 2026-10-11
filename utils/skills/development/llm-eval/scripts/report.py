#!/usr/bin/env python3
"""Provider-neutral, offline report for this package's proposed JSONL eval format.

Usage:
  python3 report.py --flow ./eval-runs/example --metric correct

Reads baseline/results.jsonl and vN/results.jsonl; separate errors.jsonl files are
counted, never assigned grade zero. No remote calls and no third-party packages.
"""

import argparse
from collections import defaultdict
from html import escape
import json
import math
from pathlib import Path
import re
import statistics
import sys


def rows(path: Path):
    if path.is_symlink():
        raise ValueError(f"refusing symlink input: {path}")
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for number, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                val = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON ({exc.msg})") from exc
            if not isinstance(val, dict):
                raise ValueError(f"{path}:{number}: expected an object")
            out.append(val)
    return out


def number(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def mean(values):
    return statistics.mean(values) if values else None


def fmt(v, decimals=3):
    return "—" if v is None else f"{v:.{decimals}f}"


def analyze(path, metric):
    samples = rows(path / "results.jsonl")
    failures = rows(path / "errors.jsonl")
    by_case = defaultdict(list)
    excluded = defaultdict(int)
    costs = []
    latency = []
    successful_rows = 0
    for row in samples:
        status = str(row.get("status", "unknown"))
        grade = row.get("grade")
        metric_value = number(grade.get(metric)) if isinstance(grade, dict) else None
        case = str(row.get("case_id", ""))
        if status not in {"ok", "refusal"} or not case or metric_value is None:
            excluded[status if status != "ok" else "invalid_grade_or_case"] += 1
            continue
        by_case[case].append(metric_value)
        successful_rows += 1
        cost = number(row.get("cost_usd"))
        if cost is not None:
            costs.append(cost)
        duration = number(row.get("latency_s"))
        if duration is not None:
            latency.append(duration)
    case_scores = {case: mean(vals) for case, vals in sorted(by_case.items())}
    return {
        "name": path.name, "case_scores": case_scores,
        "mean": mean(list(case_scores.values())),
        "scored_rows": successful_rows, "cases": len(case_scores),
        "errors": len(failures), "excluded": dict(excluded),
        "cost_per_scored_row": mean(costs), "cost_rows": len(costs),
        "mean_latency_s": mean(latency), "latency_rows": len(latency),
        "status_counts": {str(k): sum(1 for r in failures if r.get("type", r.get("failure_class")) == k) for k in {r.get("type", r.get("failure_class")) for r in failures}},
    }


def build(flow, metric):
    if flow.is_symlink():
        raise ValueError(f"refusing symlink flow directory: {flow}")
    variants = [p for p in flow.iterdir() if p.is_dir() and (p.name == "baseline" or re.fullmatch(r"v[0-9]+", p.name))]
    if any(p.is_symlink() for p in variants):
        raise ValueError("refusing symlink variant directory")
    variants.sort(key=lambda p: (p.name != "baseline", int(p.name[1:]) if p.name.startswith("v") else -1))
    if not variants:
        raise ValueError(f"no baseline/ or vN/ directories under {flow}")
    stats = [analyze(p, metric) for p in variants]
    baseline = next((s for s in stats if s["name"] == "baseline"), None)
    html_rows = []
    for s in stats:
        common = set(s["case_scores"]) & set(baseline["case_scores"]) if baseline else set()
        paired = mean([s["case_scores"][c] - baseline["case_scores"][c] for c in common]) if common else None
        excluded = ", ".join(f"{name}: {count}" for name, count in sorted(s["excluded"].items())) or "0"
        cells = [s["name"], str(s["cases"]), str(s["scored_rows"]), fmt(s["mean"]),
                 fmt(paired), str(len(common)), str(s["errors"]), excluded,
                 fmt(s["cost_per_scored_row"], 5), fmt(s["mean_latency_s"])]
        html_rows.append("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in cells) + "</tr>")
    title = f"LLM評価結果 – {flow.name}"
    notes = [
        "評価値は、まず同一ケース内の反復を平均し、ケース間を等重みで平均しています。",
        "差分はbaselineと両方に存在するcase_idのケース別平均差です。比較対象のケース数も表示します。",
        "errors.jsonlおよび未完了の結果は0点にせず、独立に集計しています。refusalは採点済みの場合のみ対象です。",
        "費用は結果行にcost_usdが記録されている場合に限る実測相当の平均です。金額不明のケースは除外されます。",
        "少数の観測値だけで統計的な優位差を断定しないでください。独立holdout、対応比較と区間推定を別途実施してください。",
        "このツールは保存済みJSONLを表示するのみで、LLM APIの呼出、graderの実行、秘密情報の除去は行いません。",
    ]
    headers = ["変種", "ケース数", "採点済み反復", metric, "baselineとの差", "対応ケース", "API/実行失敗", "未採点・除外", "費用/採点済み反復(USD)", "平均レイテンシー(秒)"]
    table_headers = "".join(f"<th scope='col'>{escape(h)}</th>" for h in headers)
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>body{{font:15px/1.65 system-ui,-apple-system,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#243042;background:#fafbfc}}h1{{letter-spacing:-.02em}}p{{color:#576477}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;background:white}}th,td{{border-bottom:1px solid #e5e8ee;padding:11px 10px;text-align:left;vertical-align:top}}th{{font-size:12px;background:#edf1f6;white-space:nowrap}}.scroll{{overflow-x:auto;border-radius:10px;border:1px solid #e5e8ee}}li{{margin:6px 0}}footer{{margin:32px 0;color:#657186;font-size:13px}}</style></head>
<body><h1>{escape(title)}</h1><p>指標: <strong>{escape(metric)}</strong> ／ データ取得元: <code>{escape(flow.name)}</code></p>
<div class="scroll"><table><thead><tr>{table_headers}</tr></thead><tbody>{''.join(html_rows)}</tbody></table></div>
<h2>読み方・制約</h2><ul>{''.join('<li>'+escape(n)+'</li>' for n in notes)}</ul>
<footer>Provider-neutral local eval report. 元のAnthropic report/SCHEMA.mdとの互換性は保証しません。</footer></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="ローカルLLM評価JSONLからHTMLを作成する")
    parser.add_argument("--flow", required=True, type=Path, help="baseline/とvN/を含むディレクトリ")
    parser.add_argument("--metric", default="correct", help="grade内の数値項目（例: correct）")
    parser.add_argument("--output", type=Path, help="出力先。既定値: FLOW/report.html")
    args = parser.parse_args()
    if not args.flow.is_dir():
        parser.error(f"flow directory does not exist: {args.flow}")
    try:
        content = build(args.flow, args.metric)
        target = args.output or (args.flow / "report.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            raise ValueError(f"refusing symlink output: {target}")
        target.write_text(content, encoding="utf-8")
    except (OSError, ValueError) as e:
        parser.exit(2, f"error: {e}\n")
    print(target)


if __name__ == "__main__":
    main()
