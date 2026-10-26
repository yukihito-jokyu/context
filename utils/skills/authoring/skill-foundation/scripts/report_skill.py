#!/usr/bin/env python3
"""作ったスキルの要約を、skill-foundation の最終報告の節（Markdown）として標準出力に出す（RPT-02）。

run.py finish が契約の report.sections から呼び、出力をそのまま報告の本文に入れる。AI が要約を書く余地を
残さないため、内容はすべて作ったスキルのファイルとプロジェクトの状態から集計する。

  ## 作ったスキル          dev/spec.json（名前、目的、置き場、起動、入力、出力）
  ## 決定と守らせ方        dev/spec.json の decisions と excluded_axes
  ## 作ったスキルの検証    skill_lint.py --final の結果、dev/results/probe-results.json
  ## 収束テスト            dev/results/convergence/round-*/report.json と dev/convergence-report.md の「結論」
  ## 確かめていないこと    上の結果と設定から決まる注意
  ## プロジェクトに置いたもの  スキルの本体、リンク、hooks の登録（ファイルを読んで確かめる）

--seal を付けると、上の節の代わりに、作ったスキルを封印して（assets/seal.json）「## 封印」の節だけを出す。
契約の report.sections に stage: finish で置き、finish が検査に通った後にだけ実行する（STEP-05）。

終了コード: 0 出力した、1 skill_lint.py --final にエラーがあり封印しなかった、2 スキルのディレクトリか dev/spec.json が無い

使い方:
  python3 report_skill.py <作ったスキルのディレクトリ> --project <プロジェクトのルート> [--seal]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402

CONFIGS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
PRODUCTS = {"claude": "Claude Code", "codex": "Codex"}
LANGUAGES = {"ja": "日本語（ja）", "en": "英語（en）"}


def ids_text(ids: list[str]) -> str:
    return "、".join(ids) if ids else "—"


def fmt(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def section_skill(spec: dict, skill_dir: Path, project: Path) -> list[str]:
    name = spec["name"]
    lines = ["## 作ったスキル", "",
             f"- 名前: `{name}`（{spec.get('title', '')}）",
             f"- 目的: {spec.get('purpose', '')}",
             f"- 本体の置き場: `{skill_dir.relative_to(project).as_posix()}`"]
    link = project / ".agents/skills" / name
    if link.is_symlink():
        lines.append(f"- Codex の置き場: `.agents/skills/{name}`（本体へのリンク）")
    products = "、".join(PRODUCTS[t] for t in spec.get("targets", []) if t in PRODUCTS)
    lines.append(f"- 対象の製品: {products}")
    lines.append(f"- 言語: {LANGUAGES.get(spec.get('language'), spec.get('language'))}")
    invoke = []
    if "claude" in spec.get("targets", []):
        invoke.append(f"`/{name}`（Claude Code）")
    if "codex" in spec.get("targets", []):
        invoke.append(f"`${name}`（Codex）")
    how = "依頼の内容から自動で選ばれる" if spec.get("triggers", {}).get("implicit") is not False else "明示したときだけ使われる"
    lines.append(f"- 起動: {how}。明示は {'、'.join(invoke)}")
    inputs = [f"`{i['key']}`（{i.get('label', '')}。{'start の前に聞く' if i.get('ask') else '既定値 ' + json.dumps(i.get('default'), ensure_ascii=False) if i.get('default') is not None else '無ければ空'}）"
              for i in spec.get("inputs", [])]
    lines.append(f"- 入力: {'、'.join(inputs) if inputs else 'なし'}")
    outputs = [f"`{o['id']}`（{o.get('label', '')}。`{o['path'].replace('{run}', f'.skill-runs/{name}')}`）"
               for o in spec.get("outputs", [])]
    lines.append(f"- 出力: {'、'.join(outputs) if outputs else 'なし'}")
    return lines


def section_decisions(spec: dict) -> list[str]:
    machine, other, standard, retired = [], [], [], []
    live = []
    for d in spec.get("decisions", []):
        rid = d.get("id", "")
        if d.get("retired"):
            retired.append(rid)
            continue
        live.append(d)
        if rid in _lib.STANDARD_IDS:
            standard.append(rid)
        elif any(level in _lib.MACHINE for level in d.get("control", [])):
            machine.append(rid)
        else:
            other.append(rid)
    excluded = [f"{e.get('axis')}（{e.get('reason', '')}）" for e in spec.get("excluded_axes", [])]
    lines = ["## 決定と守らせ方", "",
             "| 区分 | 決定の数 | ID |", "|---|---|---|",
             f"| スキル固有・機械が守ったかを確かめる（runtime・format・validate のどれかを含む） | {len(machine)} | {ids_text(machine)} |",
             f"| スキル固有・機械で確かめない（review か doc で確かめる） | {len(other)} | {ids_text(other)} |",
             f"| 標準（全スキル共通） | {len(standard)} | {ids_text(standard)} |",
             f"| 対象外にした軸 | {len(excluded)} | {ids_text(excluded)} |"]
    if retired:
        lines.append(f"| 廃止した決定（ID は再利用しない） | {len(retired)} | {ids_text(retired)} |")
    # 段と答えの決め方の内訳。1つの決定が複数の段を持つので、段の合計は決定の数と一致しない
    levels = ["段（control）: " + "、".join(f"{lv} {sum(lv in d.get('control', []) for d in live)}" for lv in _lib.LEVELS)]
    custom = [d for d in live if d.get("id") not in _lib.STANDARD_IDS]
    bases = Counter(d.get("basis") for d in custom)
    levels.append("答えの決め方（スキル固有）: " + ("、".join(f"{_lib.BASES[b][0]} {bases[b]}" for b in _lib.BASES if bases[b]) or "—"))
    lines += [""] + [f"- {text}" for text in levels]
    if other:
        lines += ["", "機械で守らせない決定と理由（spec の why_not_machine）:"]
        lines += [f"- {d['id']}: {d.get('why_not_machine') or '理由が書かれていない'}" for d in custom if d["id"] in other]
    return lines


def run_lint(skill_dir: Path, project: Path) -> tuple[str, list[str], int]:
    code, output = _lib.run([sys.executable, str(Path(__file__).resolve().parent / "skill_lint.py"), str(skill_dir),
                             "--final", "--project", str(project)], project, timeout=600)
    summary = re.search(r"エラー (\d+) 件、警告 (\d+) 件", output)
    text = f"エラー {summary.group(1)} 件、警告 {summary.group(2)} 件" if summary else f"終了コード {code}（結果を読めない）"
    warnings = [line[len("WARN "):] for line in output.splitlines() if line.startswith("WARN ")]
    return text, warnings, code


def section_seal(spec: dict, skill_dir: Path, project: Path) -> tuple[list[str], int]:
    """作ったスキルを封印する。検査に通った状態だけを封印するので、skill_lint.py --final をもう一度通す。"""
    lint_text, _, code = run_lint(skill_dir, project)
    if code != 0:
        return ["## 封印", "", f"- 封印しなかった（`skill_lint.py --final`: {lint_text}）"], 1
    count = rt.write_seal(skill_dir, rt.load_contract(skill_dir))
    rel = (skill_dir / rt.SEAL_REL).relative_to(project).as_posix()
    return ["## 封印", "",
            f"- `{rel}` に保護ファイル {count} 件のハッシュを書いた",
            f"- これより後に保護ファイルを変えると、封印し直すまで `{spec['name']}` の `run.py start` が止まる。"
            "変え方は、作ったスキルの SKILL.md の「8. 制御の仕組み」にある"], 0


def section_checks(skill_dir: Path, lint_text: str) -> list[str]:
    lines = ["## 作ったスキルの検証", "", "| 検証 | 結果 |", "|---|---|", f"| `skill_lint.py --final` | {lint_text} |"]
    path = skill_dir / "dev/results/probe-results.json"
    if path.is_file():
        data = _lib.load_json(path)
        results, wiring = data.get("results", []), data.get("wiring", [])
        platforms = "、".join(PRODUCTS.get(p, p) for p in sorted({w.get("platform") for w in wiring}))
        lines.append(f"| `probe.py` | 違反例 {len(results)} 件中 失敗 {sum(not r.get('passed') for r in results)} 件／"
                     f"配線 {len(wiring)} 件中 失敗 {sum(not w.get('passed') for w in wiring)} 件"
                     + (f"（{platforms}）" if platforms else "") + " |")
    else:
        lines.append("| `probe.py` | 結果が無い |")
    return lines


def rounds(skill_dir: Path) -> list[dict]:
    found = []
    for path in (skill_dir / "dev/results/convergence").glob("round-*/report.json"):
        data = _lib.load_json(path)
        data.setdefault("round", int(path.parent.name.split("-")[1]))
        if (path.parent / "review.json").is_file():
            data["review"] = _lib.load_json(path.parent / "review.json")
        found.append(data)
    return sorted(found, key=lambda d: d["round"])


def agents_text(names: list[str]) -> str:
    counts = Counter(n.rsplit("-", 1)[0] for n in names)
    return "、".join(f"{runner}×{count}" for runner, count in sorted(counts.items()))


def section_convergence(spec: dict, skill_dir: Path) -> tuple[list[str], list[str]]:
    """（節の行, 確かめていないことに足す行）"""
    skip = str(spec.get("convergence", {}).get("skip_reason") or "").strip()
    lines = ["## 収束テスト", ""]
    if skip:
        lines.append(f"実施していない（理由: {skip}）。")
        return lines, ["収束テストを実施していないため、別の AI で結果が揃うかは測っていない"]
    data = rounds(skill_dir)
    if not data:
        lines.append("結果が無い。")
        return lines, ["収束テストの結果が無い"]
    lines += ["| ラウンド | 課題 | エージェント | status | files | structure | names | check | 基準 |", "|---|---|---|---|---|---|---|---|---|"]
    for report in data:
        for task in report.get("tasks", []):
            status = "、".join(sorted(set(task.get("status", {}).values()))) or "—"
            checks = task.get("check", {})
            check = "—" if not checks else ("全員通過" if all(v == 0 for v in checks.values()) else "失敗あり")
            verdict = "満たす" if task.get("converged") else "満たさない"
            if task.get("tampered"):
                verdict += f"（スキル自身や hooks の登録を変えた: {'、'.join(task['tampered'])}）"
            lines.append(f"| {report['round']} | {task.get('id')} | {agents_text(task.get('agents', []))} | {status} | "
                         f"{fmt(task.get('files'))} | {fmt(task.get('structure'))} | {fmt(task.get('names'))} | {check} | {verdict} |")
    last = data[-1]
    tasks = last.get("tasks", [])
    left = [t.get("id") for t in tasks if not t.get("converged")]
    lines += ["", f"最後のラウンド（{last['round']}）: 課題 {len(tasks)} 件中 基準を満たす {len(tasks) - len(left)} 件"]
    unchecked = []
    samples = last.get("review", {}).get("samples", [])
    if samples:
        missed = [x["id"] for x in samples if x.get("rate", 0) < 1]
        lines.append(f"レビューの検出率（完了前チェックリスト）: 見本 {len(samples)} 件中 全員が見つけた {len(samples) - len(missed)} 件"
                     + (f"（見逃しあり: {'、'.join(missed)}）" if missed else ""))
        left += missed
    elif any(d.get("review") is None for d in data[-1:]) and Path(skill_dir / "dev/probes.json").is_file() \
            and _lib.load_json(skill_dir / "dev/probes.json").get("reviews"):
        unchecked.append("レビューの検出率（完了前チェックリストで違反を見つけられるか）を測っていない")
    if any("subagent" in r.get("runners", []) for r in data):
        unchecked.append("収束テストの runner subagent（Agent ツール）では、一時プロジェクトの hooks が働かず、自動の起動は説明文を渡した近似で、"
                         "Claude Code と Codex の違いは測っていない（convergence-test.md の3章）")
    if not left:
        lines.append("残った揺れ: なし")
        return lines, unchecked
    report_md = skill_dir / "dev/convergence-report.md"
    text = report_md.read_text(encoding="utf-8") if report_md.is_file() else ""
    conclusion = _lib.section(text, "結論") + _lib.section(text, "Conclusion")
    lines.append("残った揺れ（dev/convergence-report.md の「結論」から）:")
    for tid in left:
        mentions = [l.strip().lstrip("-* ").strip() for l in conclusion.splitlines() if tid in l]
        if not mentions:
            lines.append(f"- {tid}: 結論に記載が無い")
        lines += [f"- {m}" if m.startswith(tid) else f"- {tid}: {m}" for m in mentions]
    return lines, unchecked + [f"基準を満たさない課題が残っている（{'、'.join(left)}）"]


def under_git(project: Path) -> bool:
    return any((p / ".git").exists() for p in [project, *project.parents])


def hook_events(project: Path, platform: str, name: str) -> list[str]:
    config = project / CONFIGS[platform]
    if not config.is_file():
        return []
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return sorted(event for event, groups in data.get("hooks", {}).items()
                  if any(f"/{name}/scripts/hook.py" in h.get("command", "") for g in groups for h in g.get("hooks", [])))


def unverifiable(skill_dir: Path) -> list[str]:
    """dev/research.md で「確かめられない」とした項目の見出し（references/research.md の3章）。"""
    path = skill_dir / "dev/research.md"
    found, heading = [], ""
    for line in (path.read_text(encoding="utf-8") if path.is_file() else "").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
        elif re.search(r"(確認の状態|Status)\s*[:：]\s*(確かめられない|unverifiable)", line, re.I):
            found.append(heading)
    return found


def section_unverified(spec: dict, skill_dir: Path, project: Path, warnings: list[str], extra: list[str]) -> list[str]:
    items = list(extra)
    items += [f"調査で確かめられなかった事実: {h}（dev/research.md）" for h in unverifiable(skill_dir)]
    hooks_on = spec.get("control", {}).get("hooks", True)
    if hooks_on and "codex" in spec.get("targets", []):
        items.append("Codex の hooks は、Codex の `/hooks` で信頼するまで動かない（それまでは `run.py check` と `finish` だけで検査される）")
    if not hooks_on:
        items.append("hooks を使わない設定のため、編集の直後と応答を終える前の検査は働かない")
    if not under_git(project):
        items.append("このプロジェクトは git の管理下に無いため、作ったスキルの実行時に契約の外の変更（CTL-05）を検査しない")
    items += [f"skill_lint.py の警告: {w}" for w in warnings if "convergence.skip_reason" not in w]
    return ["## 確かめていないこと", ""] + ([f"- {i}" for i in items] or ["- なし"])


def section_placed(spec: dict, skill_dir: Path, project: Path) -> list[str]:
    name = spec["name"]
    files = [f for f in _lib.iter_files(skill_dir) if not f.endswith(".DS_Store")]
    lines = ["## プロジェクトに置いたもの", "", f"- `{skill_dir.relative_to(project).as_posix()}/`: スキルの本体（ファイル {len(files)} 個）"]
    link = project / ".agents/skills" / name
    if link.is_symlink():
        lines.append(f"- `.agents/skills/{name}`: 本体へのリンク")
    for platform in ("claude", "codex"):
        events = hook_events(project, platform, name)
        if events:
            lines.append(f"- `{CONFIGS[platform]}`: `{name}` の hooks を {len(events)} つ登録（{'、'.join(events)}）")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir", help="作ったスキルのディレクトリ")
    parser.add_argument("--project", required=True, help="プロジェクトのルート")
    parser.add_argument("--seal", action="store_true", help="作ったスキルを封印し、「## 封印」の節だけを出す")
    args = parser.parse_args()
    skill_dir, project = Path(args.dir).resolve(), Path(args.project).resolve()
    if not (skill_dir / _lib.SPEC_REL).is_file():
        print(f"{skill_dir / _lib.SPEC_REL} がありません", file=sys.stderr)
        return 2
    spec = _lib.load_spec(skill_dir)
    if args.seal:
        lines, code = section_seal(spec, skill_dir, project)
        print("\n".join(lines))
        return code
    lint_text, warnings, _ = run_lint(skill_dir, project)
    convergence, extra = section_convergence(spec, skill_dir)
    parts = [section_skill(spec, skill_dir, project), section_decisions(spec), section_checks(skill_dir, lint_text),
             convergence, section_unverified(spec, skill_dir, project, warnings, extra), section_placed(spec, skill_dir, project)]
    print("\n\n".join("\n".join(p) for p in parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
