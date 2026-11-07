#!/usr/bin/env python3
"""作るスキルの hooks の方針（dev/hooks-plan.json）を決める（STEP-08）。SKILL.md の手順4で、Eval 作成の後、受付の前に実行する。

hooks は .claude/settings.json・.codex/hooks.json に書かれ、プロジェクトでの作業全体に効く。そこで登録する前に、次の4つを
ユーザーに聞いて決める。質問は assets/templates/hooks-plan.example.json から作り、Eval 作成と同じく、カタログの「hooks 設計」
タブの削って開くカードで答えてもらう。
  hooks     出力の検査に hooks を使うか（使わなければ、ほかの3つは聞かない）
  targets   どの製品に登録するか（作るスキルの targets から複数選ぶ。製品が1つなら聞かない）
  feedback  利用中の指摘を集めるか
  via       hooks をどこに登録するか（プロジェクトの設定か、プラグインで配るか）

--ask は質問を書く。既定の答え（「既定」の印）は入力 hooks の値（--default）から決める。既存のスキルを作り直すとき
（assets/contract.json がある）は、今の契約の control と置き場から決め、印を「今の設定」にする。
--answer には、カタログの「回答をコピー」でユーザーが写して貼った文を渡す。その文を言い換えずに dialog に足し、
方針（plan）を決めて questions を消す。
--decide は聞かずに決める。依頼で入力 hooks を指定されたとき（--by request）と、ユーザーに質問できないとき
（--by setting。start が設定か既定値から補った値）に使う。
引数が dir だけなら、方針が決まっているかを確かめる（skill_lint.py --phase 0 も同じ検査をする）。
決めた方針は、受付の後の init_skill.py が dev/spec.json の control（hooks、feedback、hook_targets、hook_via）に写す。

終了コード: 0 決まった・記録した、1 指摘あり（答えを待っている、回答の誤り）、2 引数の誤り

使い方:
  python3 hooks_plan.py <作るスキルのディレクトリ> --ask --targets claude,codex --default all|check|none
  python3 hooks_plan.py <作るスキルのディレクトリ> --answer - < 貼られた回答
  python3 hooks_plan.py <作るスキルのディレクトリ> --decide all|check|none --by request|setting --targets claude,codex
  python3 hooks_plan.py <作るスキルのディレクトリ>
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

PLAN_REL = "dev/hooks-plan.json"
TEMPLATE = _lib.TEMPLATES / "hooks-plan.example.json"
VALUES = {"all": (True, True), "check": (True, False), "none": (False, False)}  # 入力 hooks の値 → (検査に使う, 指摘を集める)
VIAS = ["project", "plugin"]
BY = {"user": "ユーザーが答えた", "request": "依頼の指定", "setting": "設定の値"}
MARKS = {"input": "既定", "current": "今の設定"}  # 既定の答えの印。current は作り直す前のスキルの状態
ANSWER_HEAD = re.compile(r"^hooks の方針の回答（(?P<name>[^、）]+)、(?P<talk>talk-\d+)）$")  # カタログの「回答をコピー」の1行目
ANSWER_LINE = re.compile(r"^Q(?P<n>\d+) [^:]*: ?(?P<value>.*)$")


def load(skill_dir: Path) -> tuple[dict | None, str]:
    path = skill_dir / PLAN_REL
    if not path.is_file():
        return None, "ありません"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, f"JSON として読めません（{exc}）"
    return (doc, "") if isinstance(doc, dict) else (None, "中身がオブジェクトではありません")


def questions(doc: dict | None) -> tuple[str, list[dict]]:
    """答えを待っている質問の (talk, 質問の一覧)。"""
    q = doc.get("questions") if isinstance(doc, dict) and isinstance(doc.get("questions"), dict) else {}
    items = q.get("items") if isinstance(q.get("items"), list) else []
    return str(q.get("talk") or ""), [x for x in items if isinstance(x, dict)]


def plan_problems(plan) -> list[str]:
    if not isinstance(plan, dict):
        return ["方針（plan）がありません。--ask で聞くか、--decide で決めてください"]
    errors = []
    if not isinstance(plan.get("hooks"), bool) or not isinstance(plan.get("feedback"), bool):
        errors.append("plan の hooks と feedback は true か false にしてください")
    targets = plan.get("targets")
    if not isinstance(targets, list) or any(t not in _lib.TARGETS for t in targets):
        errors.append(f"plan の targets は {'、'.join(_lib.TARGETS)} の一覧にしてください")
    elif plan.get("hooks") is True and not targets:
        errors.append("hooks を使うのに、登録する製品（plan の targets）がありません")
    if plan.get("via") not in VIAS:
        errors.append(f"plan の via は {' か '.join(VIAS)} にしてください")
    if plan.get("by") not in BY:
        errors.append(f"plan の by は {'、'.join(BY)} のどれかにしてください")
    return errors


def problems(skill_dir: Path) -> list[str]:
    """受付の前に方針が決まっているか（skill_lint.py --phase 0）。"""
    doc, problem = load(skill_dir)
    if doc is None:
        return [f"{PLAN_REL} が{problem}。SKILL.md の手順4（hooks の方針）を行ってください"]
    talk, items = questions(doc)
    if items:
        return [f"ユーザーの答えを待っている質問が {len(items)} 件あります（{talk}）。カタログの「hooks 設計」タブで答えてもらい、"
                "貼られた回答を hooks_plan.py --answer で記録してください"]
    return plan_problems(doc.get("plan"))


def control_of(plan: dict) -> dict:
    """方針を写した spec の control の項目。"""
    if not plan.get("hooks"):
        return {"hooks": False, "feedback": False}
    return {"hooks": True, "feedback": plan["feedback"], "hook_targets": list(plan["targets"]), "hook_via": plan["via"]}


def spec_gaps(doc: dict | None, spec: dict) -> list[str]:
    """方針と spec の control が合っていないところ。方針がまだ無ければ何も言わない。"""
    plan = doc.get("plan") if isinstance(doc, dict) else None
    if not isinstance(plan, dict) or plan_problems(plan):
        return []
    control, gaps = spec.get("control", {}), []
    for key, want in control_of(plan).items():
        have = control.get(key)
        if key == "hook_targets":
            have = control.get(key, spec.get("targets", []))
            same = sorted(have) == sorted(want) if isinstance(have, list) else False
        else:
            have = control.get(key, True if key in ("hooks", "feedback") else "project")
            same = have == want
        if not same:
            gaps.append(f"control.{key} が {json.dumps(have, ensure_ascii=False)} ですが、hooks の方針（{PLAN_REL}）は "
                        f"{json.dumps(want, ensure_ascii=False)} です")
    missing = [t for t in plan.get("targets", []) if t not in spec.get("targets", [])]
    if plan.get("hooks") and missing:
        gaps.append(f"hooks の方針の製品 {'、'.join(missing)} が、spec の targets にありません")
    return gaps


def apply_plan(skill_dir: Path, spec: dict) -> bool:
    """決めた方針を spec の control に写す（init_skill.py が受付の後に呼ぶ）。変えたら True。"""
    doc, _ = load(skill_dir)
    plan = doc.get("plan") if isinstance(doc, dict) else None
    if not isinstance(plan, dict) or plan_problems(plan) or questions(doc)[1]:
        return False
    control = spec.setdefault("control", {})
    before = dict(control)
    if not plan["hooks"]:
        control.pop("hook_targets", None)
        control.pop("hook_via", None)
    control.update(control_of(plan))
    return control != before


def describe(plan: dict) -> list[tuple[str, str, str]]:
    """カタログと報告に出す方針の (項目, 決めた値, 補足)。"""
    products = {"claude": "Claude Code", "codex": "Codex"}
    if not plan.get("hooks"):
        return [("出力の検査", "使わない", "hooks を1つも登録しない。検査は run.py check と finish だけで行う"),
                ("利用中の指摘", "集めない", "hooks を使わないので集めない")]
    names = "・".join(products[t] for t in plan.get("targets", []) if t in products)
    return [("出力の検査", "使う", "編集の直後と応答を終える前に自動で検査する"),
            ("登録する製品", names, "Codex は /hooks で信頼するまで動かない" if "codex" in plan.get("targets", []) else ""),
            ("利用中の指摘", "集める" if plan.get("feedback") else "集めない",
             "完了の後の発言と、直す前と後の成果物を記録する" if plan.get("feedback") else "収集の hooks は登録しない（control.feedback: false）"),
            ("登録先", "プラグインで配る" if plan.get("via") == "plugin" else "プロジェクトの設定",
             "プラグインの hooks に書く。install.py では登録しない" if plan.get("via") == "plugin" else
             "install.py が .claude/settings.json・.codex/hooks.json に書く")]


def current_defaults(skill_dir: Path, targets: list[str]) -> dict | None:
    """作り直す前のスキル（assets/contract.json がある）の今の状態。無ければ None。"""
    path = skill_dir / "assets/contract.json"
    if not path.is_file():
        return None
    contract = _lib.load_json(path)
    control = contract.get("control", {}) if isinstance(contract, dict) else {}
    hooks_on = control.get("hooks", True) is not False
    return {"hooks": hooks_on, "feedback": hooks_on and control.get("feedback", True) is not False,
            "targets": [t for t in control.get("hook_targets", contract.get("targets", targets)) if t in targets],
            "via": "plugin" if _lib.plugin_root(skill_dir) is not None else "project"}


def build_questions(skill_dir: Path, targets: list[str], default: str) -> tuple[list[dict], str]:
    """ひな形から質問を作る。(質問, 既定の答えの出どころ)。"""
    items = copy.deepcopy(_lib.load_json(TEMPLATE)["questions"]["items"])
    now = current_defaults(skill_dir, targets)
    hooks_on, feedback = VALUES[default]
    wants = now or {"hooks": hooks_on, "feedback": feedback, "targets": list(targets),
                    "via": "plugin" if _lib.plugin_root(skill_dir) is not None else "project"}
    out = []
    for q in items:
        if q["id"] == "targets":
            if len(targets) < 2:
                continue  # 製品が1つなら聞かない
            q["options"] = [o for o in q["options"] if o["value"] in targets]
            if "codex" in targets:
                q["why"] = q["why"] + q["why_codex"]
        q.pop("why_codex", None)
        for key in ("ask", "why"):
            q[key] = q[key].replace("{name}", skill_dir.name)
        for n, option in enumerate(q["options"]):
            option["key"] = "ABCDEFGH"[n]
            want = wants[q["id"]]
            option["default"] = option["value"] in want if isinstance(want, list) else option["value"] == want
        out.append(q)
    return out, "current" if now else "input"


def cmd_ask(skill_dir: Path, targets: list[str], default: str) -> int:
    doc, problem = load(skill_dir)
    if doc is None and problem != "ありません":
        print(f"ERROR {PLAN_REL}: {problem}")
        return 1
    doc = doc or {}
    talk = f"talk-{len(doc.get('dialog', [])) + 1}"
    items, source = build_questions(skill_dir, targets, default)
    doc.update({"questions": {"talk": talk, "items": items}, "targets": targets, "defaults_from": source})
    _lib.write_json(skill_dir / PLAN_REL, doc)
    print(f"[hooks] {skill_dir.name}: 質問 {len(items)} 件を {PLAN_REL} に書いた（{talk}。既定の答えは"
          f"{'今のスキルの状態' if source == 'current' else '入力 hooks の値 ' + default}）。catalog.py --project <ルート> を実行し、"
          "run.py wait --question の後に、カタログの「hooks 設計」タブで答えて回答の文を貼るようユーザーに伝える")
    return 0


def parse_answer(items: list[dict], lines: list[str]) -> tuple[dict, list[str]]:
    """貼られた回答から {質問の id: 選んだ値の一覧}。答えていない質問は入れない。"""
    chosen, errors = {}, []
    for line in lines[1:]:
        m = ANSWER_LINE.match(line.strip())
        if not m or not 1 <= int(m["n"]) <= len(items):
            continue
        q = items[int(m["n"]) - 1]
        value = m["value"].strip()
        if not value or value.startswith("（"):
            continue  # 答えていない・聞かなかった
        keys = [part.strip().split(".", 1)[0] for part in value.split("、")]
        by_key = {o["key"]: o["value"] for o in q["options"]}
        if any(k not in by_key for k in keys) or (not q.get("multi") and len(keys) != 1):
            errors.append(f"Q{m['n']} の答え「{value}」を選択肢と照らせません")
            continue
        chosen[q["id"]] = [by_key[k] for k in keys]
    return chosen, errors


def cmd_answer(skill_dir: Path, text: str) -> int:
    doc, problem = load(skill_dir)
    if doc is None:
        print(f"ERROR {PLAN_REL}: {problem}")
        return 1
    talk, items = questions(doc)
    if not items:
        print("ERROR --answer: 答えを待っている質問（questions）がありません")
        return 1
    lines = [line.rstrip() for line in text.strip().splitlines()]
    head = ANSWER_HEAD.match(lines[0].strip()) if lines else None
    if head is None:
        print("ERROR --answer: 1行目が「hooks の方針の回答（<スキルの名前>、talk-<番号>）」ではありません。カタログの「回答をコピー」で"
              "写した文をそのまま渡してください")
        return 1
    if (head["name"], head["talk"]) != (skill_dir.name, talk):
        print(f"ERROR --answer: {head['name']} の {head['talk']} への回答です。今の質問は {skill_dir.name} の {talk} です")
        return 1
    chosen, errors = parse_answer(items, lines)
    hooks_on = chosen.get("hooks", [None])[0]
    needed = [n for n, q in enumerate(items, 1) if q["id"] not in chosen and (q["id"] == "hooks" or hooks_on is True)]
    errors += [f"Q{n} に答えていません。カタログで答えてから、もう一度コピーして貼ってください" for n in needed]
    if errors:
        for error in errors:
            print(f"ERROR --answer: {error}")
        return 1
    doc.setdefault("dialog", []).append({"id": talk, "asked": "\n".join(f"Q{n} {q['title']}: {q['ask']}" for n, q in enumerate(items, 1)),
                                         "answer": "\n".join(lines)})
    targets = chosen.get("targets") or list(doc.get("targets") or [])  # 製品が1つなら聞かずに、その製品にする
    doc["plan"] = {"hooks": hooks_on, "feedback": hooks_on and chosen["feedback"][0], "targets": targets if hooks_on else [],
                   "via": chosen["via"][0] if hooks_on else "project", "by": "user", "talk": talk}
    del doc["questions"]
    _lib.write_json(skill_dir / PLAN_REL, doc)
    print(f"[hooks] {skill_dir.name}: {talk} の回答を dialog に記録し、方針を決めた（"
          + "、".join(f"{k} {v}" for k, v, _ in describe(doc["plan"])) + "）。受付の後に init_skill.py が spec の control に写す")
    return 0


def cmd_decide(skill_dir: Path, value: str, by: str, targets: list[str]) -> int:
    doc, problem = load(skill_dir)
    if doc is None and problem != "ありません":
        print(f"ERROR {PLAN_REL}: {problem}")
        return 1
    doc = doc or {}
    doc.pop("questions", None)
    hooks_on, feedback = VALUES[value]
    doc["plan"] = {"hooks": hooks_on, "feedback": feedback, "targets": list(targets) if hooks_on else [],
                   "via": "plugin" if hooks_on and _lib.plugin_root(skill_dir) is not None else "project", "by": by, "value": value}
    _lib.write_json(skill_dir / PLAN_REL, doc)
    print(f"[hooks] {skill_dir.name}: {BY[by]}（入力 hooks の値 {value}）で方針を決めた（"
          + "、".join(f"{k} {v}" for k, v, _ in describe(doc["plan"])) + "）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir", help="作るスキルのディレクトリ")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ask", action="store_true", help="質問を dev/hooks-plan.json に書く")
    mode.add_argument("--answer", metavar="TEXT", help="カタログの「hooks 設計」タブから貼られた回答（- なら標準入力から読む）")
    mode.add_argument("--decide", choices=sorted(VALUES), help="聞かずに、この値で決める")
    parser.add_argument("--targets", help="カンマ区切り（claude、codex）。run.py start が決めた入力 targets")
    parser.add_argument("--default", choices=sorted(VALUES), default="all", help="--ask の既定の答え（run.py start が決めた入力 hooks）")
    parser.add_argument("--by", choices=["request", "setting"], help="--decide の値の出どころ")
    args = parser.parse_args()
    skill_dir = Path(args.dir).resolve()
    if not skill_dir.is_dir():
        _lib.fail(f"{skill_dir} がありません")
    targets = [t.strip() for t in (args.targets or "").split(",") if t.strip()]
    if (args.ask or args.decide) and (not targets or any(t not in _lib.TARGETS for t in targets)):
        _lib.fail(f"--targets に {'、'.join(_lib.TARGETS)} から1つ以上を書いてください")
    if args.decide and not args.by:
        _lib.fail("--decide には --by（request か setting）を付けてください")
    if args.ask:
        return cmd_ask(skill_dir, targets, args.default)
    if args.answer is not None:
        return cmd_answer(skill_dir, sys.stdin.read() if args.answer == "-" else args.answer)
    if args.decide:
        return cmd_decide(skill_dir, args.decide, args.by, targets)
    errors = problems(skill_dir)
    for error in errors:
        print(f"ERROR {error}")
    if not errors:
        doc, _ = load(skill_dir)
        print(f"[hooks] {skill_dir.name}: 方針は決まっている（{BY[doc['plan']['by']]}。"
              + "、".join(f"{k} {v}" for k, v, _ in describe(doc["plan"])) + "）")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
