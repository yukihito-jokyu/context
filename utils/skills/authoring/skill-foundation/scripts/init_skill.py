#!/usr/bin/env python3
"""dev/spec.json から、スキルの骨組みを作る。既にあるファイルは上書きしない。

  1. spec の受付の項目（name、kind、mode、language、targets、title、purpose、triggers）を検査する。
     mode が retrofit（既存のスキルへの後付け）なら、元の SKILL.md を dev/original/SKILL.md に移す
  2. spec に標準の決定（CTL-01〜05、RPT-01）が無ければ足し、種類（kind）の追加の軸を extra_axes の先頭に入れる
  3. ひな形から SKILL.md と dev/ の文書を作る
  4. 実行時ランタイム（scripts/_skillrt.py、run.py、hook.py、install.py）を写す
  5. render_skill.py で生成部分を埋める

同じ spec からは常に同じ骨組みができる。

使い方:
  python3 init_skill.py --dir <スキルのディレクトリ> [--dry-run] [--update-runtime]
  先に <スキルのディレクトリ>/dev/spec.json を assets/templates/spec.example.json から作っておく。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import render_skill  # noqa: E402

PLACEHOLDER = re.compile(r"<[^<>]*[^\x00-\x7f][^<>]*>")


def find_placeholders(value) -> list[str]:
    if isinstance(value, str):
        return PLACEHOLDER.findall(re.sub(r"`[^`]*`", "", value))  # コマンド例の <…> は例のプレースホルダではない
    if isinstance(value, dict):
        return [p for v in value.values() for p in find_placeholders(v)]
    if isinstance(value, list):
        return [p for v in value for p in find_placeholders(v)]
    return []


def intake_errors(spec: dict, skill_dir: Path) -> list[str]:
    """受付（フェーズ0）で埋める項目の検査。skill_lint.py もこれを使う。"""
    errors = []
    name = spec.get("name", "")
    if not _lib.NAME_RE.match(name) or len(name) > 64:
        errors.append("name は 64 文字以内の kebab-case（英小文字・数字・ハイフン）にしてください")
    elif name != skill_dir.name:
        errors.append(f"name（{name}）とディレクトリ名（{skill_dir.name}）を一致させてください")
    if spec.get("spec_version") != 1:
        errors.append("spec_version は 1 にしてください")
    mode = spec.get("mode", "new")
    if mode not in _lib.MODES:
        errors.append(f"mode は {_lib.MODES} のどれかにしてください（retrofit は既存のスキルへの後付け）")
    if not _lib.is_foundation(skill_dir):
        kinds = list(_lib.load_profiles())
        if spec.get("kind") not in kinds:
            errors.append(f"kind（スキルの種類）は {kinds} のどれかにしてください（references/intake.md の2章）")
        elif mode == "new" and _lib.NAME_RE.match(name) and not name.startswith(spec["kind"] + "-"):
            errors.append(f"name は種類の動詞で始めてください（{spec['kind']}-<目的語>。references/intake.md の2章）")
    if spec.get("status") not in ("building", "ready"):
        errors.append("status は building（作成中）か ready（完成）にしてください")
    if spec.get("language") not in _lib.LANGS:
        errors.append(f"language は {_lib.LANGS} のどれかにしてください")
    targets = spec.get("targets")
    if not isinstance(targets, list) or not targets or any(t not in _lib.TARGETS for t in targets):
        errors.append(f"targets は {_lib.TARGETS} から1つ以上を選んだ配列にしてください")
    for key in ("title", "purpose"):
        if not str(spec.get(key, "")).strip():
            errors.append(f"{key} が空です")
    trig = spec.get("triggers", {})
    if len(trig.get("use_when", [])) < 5:
        errors.append("triggers.use_when に、実際のユーザーの言い方を5つ以上書いてください")
    if len(set(trig.get("use_when", []))) != len(trig.get("use_when", [])):
        errors.append("triggers.use_when に重複があります")
    not_for = trig.get("not_for", [])
    if not not_for or not all(isinstance(i, dict) and i.get("when") and i.get("instead") for i in not_for):
        errors.append("triggers.not_for に {\"when\", \"instead\"} を1つ以上書いてください")
    if not isinstance(trig.get("implicit"), bool):
        errors.append("triggers.implicit は true（自動で選ばれる）か false（明示したときだけ）にしてください")
    intake = {k: spec.get(k) for k in ("name", "language", "title", "purpose", "triggers")}
    leftovers = sorted(set(find_placeholders(intake)))
    if leftovers:
        errors.append(f"例のプレースホルダが残っています: {', '.join(leftovers[:5])}")
    return errors


def standard_decisions(language: str) -> list[dict]:
    return json.loads((_lib.TEMPLATES / f"standard-decisions.{language}.json").read_text(encoding="utf-8"))


def merge_standard(spec: dict) -> bool:
    present = {d.get("id") for d in spec.get("decisions", [])}
    added = [d for d in standard_decisions(_lib.labels(spec)) if d["id"] not in present]
    spec.setdefault("decisions", []).extend(added)
    return bool(added)


def merge_profile(spec: dict) -> bool:
    """種類の追加の軸を extra_axes の先頭（X1 から）に入れる。自分で足した軸は後ろに送って番号を振り直す。"""
    wanted = _lib.profile_axes(spec)
    current = spec.get("extra_axes", [])
    if current[:len(wanted)] == wanted:
        return False
    names = {a["name"] for a in wanted}
    own = [a for a in current if a.get("name") not in names]
    renamed = {a.get("axis"): f"X{i}" for i, a in enumerate(own, len(wanted) + 1) if a.get("axis") != f"X{i}"}
    used = {x for d in spec.get("decisions", []) for x in d.get("axes", [])} | {e.get("axis") for e in spec.get("excluded_axes", [])}
    if set(renamed) & used:
        _lib.fail(f"種類 {spec.get('kind')} の追加の軸を X1 から入れると、使用中の軸 {sorted(set(renamed) & used)} の番号が変わります。"
                  "extra_axes と、その軸を使う決定・excluded_axes を手で直してください")
    spec["extra_axes"] = wanted + [{**a, "axis": f"X{i}"} for i, a in enumerate(own, len(wanted) + 1)]
    return True


RETROFIT_RESEARCH = f"""
## 既存のスキル

{_lib.TODO_MARKER}: 元の SKILL.md（{_lib.ORIGINAL_REL}）の手順、入力、出力、使っていたスクリプトを書く。新しい決定のうち、元のやり方を残したもの（basis: existing）の ID を「使った決定」に書く。

- 確認方法：{_lib.ORIGINAL_REL} を読んだ
- 確認の状態：未確認
- 分かったこと：
- 使った決定：
"""


def fill(template: str, spec: dict) -> str:
    return template.replace("{{name}}", spec["name"]).replace("{{title}}", spec.get("title", spec["name"]))


def move_original(skill_dir: Path, spec: dict, dry: bool) -> str | None:
    """skill-foundation の形でない SKILL.md を、後付けなら dev/original/ に移す。後付けでなければ止める（OUT-06）。"""
    skill_md, original = skill_dir / "SKILL.md", skill_dir / _lib.ORIGINAL_REL
    if not skill_md.is_file() or _lib.blocks(skill_md.read_text(encoding="utf-8")):
        return None
    if spec.get("mode") != "retrofit":
        _lib.fail("SKILL.md が既にあり、skill-foundation の形ではありません。既存のスキルに後付けするなら、"
                  "spec の mode を retrofit にしてください（SKILL.md の OUT-06 の表）")
    if original.exists():
        _lib.fail(f"{_lib.ORIGINAL_REL} が既にあります。SKILL.md と見比べ、どちらを残すかを決めてから実行してください")
    if not dry:
        original.parent.mkdir(parents=True, exist_ok=True)
        skill_md.rename(original)
    return f"{_lib.ORIGINAL_REL}（元の SKILL.md を移した）"


def plan(spec: dict) -> list[tuple[str, str]]:
    lang = _lib.labels(spec)
    return [
        ("SKILL.md", f"SKILL.{lang}.md.tmpl"),
        ("dev/research.md", "research.md.tmpl"),
        ("dev/convergence-report.md", "convergence-report.md.tmpl"),
        ("dev/evals.json", "evals.example.json"),
        ("dev/probes.json", "probes.example.json"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", required=True, help="作るスキルのディレクトリ")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update-runtime", action="store_true", help="scripts/ のランタイムを最新版で上書きする")
    args = parser.parse_args()

    skill_dir = Path(args.dir).resolve()
    spec_path = skill_dir / _lib.SPEC_REL
    if not spec_path.is_file():
        _lib.fail(f"{spec_path} がありません。assets/templates/spec.example.json を写して受付の項目を埋めてから実行してください")
    spec = _lib.load_json(spec_path)
    errors = intake_errors(spec, skill_dir)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    created, kept, differs = [], [], []
    moved = move_original(skill_dir, spec, args.dry_run)
    if moved:
        created.append(moved)
    added_standard = merge_standard(spec)
    added_axes = not _lib.is_foundation(skill_dir) and merge_profile(spec)
    if added_standard or added_axes:
        created.append(f"{_lib.SPEC_REL}（" + "、".join(x for x, on in (("標準の決定を追加", added_standard),
                                                                     ("種類の追加の軸を extra_axes に追加", added_axes)) if on) + "）")
        if not args.dry_run:
            _lib.write_json(spec_path, spec)
    for rel, template in plan(spec):
        target = skill_dir / rel
        if target.exists():
            kept.append(rel)
            continue
        created.append(rel)
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            text = fill((_lib.TEMPLATES / template).read_text(encoding="utf-8"), spec)
            if rel == "dev/research.md" and spec.get("mode") == "retrofit":
                text += RETROFIT_RESEARCH
            target.write_text(text, encoding="utf-8")
    for script in _lib.RUNTIME_FILES:
        source = _lib.FOUNDATION_DIR / "scripts" / script
        target = skill_dir / "scripts" / script
        if target.exists() and target.read_bytes() == source.read_bytes():
            kept.append(f"scripts/{script}")
            continue
        if target.exists() and not args.update_runtime:
            differs.append(f"scripts/{script}")
            continue
        created.append(f"scripts/{script}")
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    for rel in ("references", "assets", _lib.EXAMPLES_DIR, "dev/fixtures"):
        if not args.dry_run:
            (skill_dir / rel).mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        for rel, content in render_skill.render_all(skill_dir, spec).items():
            target = skill_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        created.append("生成部分（SKILL.md の frontmatter と GENERATED、references/decisions.md、assets/contract.json）")

    verb = "作る予定" if args.dry_run else "作成"
    for rel in created:
        print(f"{verb}  {rel}")
    for rel in kept:
        print(f"既存    {rel}")
    for rel in differs:
        print(f"差分あり {rel}（--update-runtime で最新版に置き換える）")
    print(f"\n{len(created)} 件{verb}、{len(kept)} 件は既存のため変更なし、{len(differs)} 件は差分あり")
    print("次: フェーズ2（調査）。dev/research.md に出典付きで書く。"
          f"各フェーズで {_lib.TODO_MARKER} を埋め、最後に skill_lint.py --final で残りが無いことを確かめる")
    return 0


if __name__ == "__main__":
    sys.exit(main())
