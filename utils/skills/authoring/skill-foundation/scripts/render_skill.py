#!/usr/bin/env python3
"""dev/spec.json から、スキルのうち機械で決まる部分を生成する。手で書く部分には触れない。

生成するもの:
  SKILL.md の frontmatter と、<!-- BEGIN GENERATED:<id> --> 〜 <!-- END GENERATED:<id> --> の8か所
  references/decisions.md（ルールの全文。理由・場合分け・良い例・悪い例）
  assets/contract.json（run.py と hook.py が読む契約）
  references/skill-profiles.md（skill-foundation 自身のときだけ。assets/skill-profiles.json から）

同じ spec からは常に同じ内容を生成する。AI ごとに書き方が分かれる余地を残さないため、表の列・並び順・
文言はすべてここで固定する。

使い方:
  python3 render_skill.py --dir <スキルのディレクトリ> [--check]
  --check: 書き込まずに、生成物が最新かどうかだけを調べる（最新でなければ終了コード1）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

TEXT = {
    "ja": {
        "use": "次のような依頼で使う。", "not": "次の場合は使わない。", "instead": "代わりに",
        "implicit_yes": "依頼の内容から自動で選ばれる。明示して呼ぶときは {how} と書く。",
        "implicit_no": "自動では選ばれない。{how} と書いて呼ぶ。",
        "call": {"claude": "Claude Code では `/{name}`", "codex": "Codex では `${name}`"}, "call_sep": "、",
        "inputs_head": "| 項目 | キー | 受け付ける書き方 | 無いとき |",
        "inputs_none": "入力の項目は無い。依頼文だけを `run.py start` に渡す。",
        "inputs_note": "入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。",
        "ask": "start の前に聞く: {q}", "default": "既定値 `{v}`", "none": "空のまま",
        "aliases": "別名", "types": {"string": "文字列", "int": "整数（全角も可）", "bool": "はい・いいえ（true/false、する/しない も可）",
                                    "list": "一覧（`,`・`、`・改行で区切る）", "enum": "{choices} のどれか",
                                    "path": "パス", "slug": "英小文字・数字・`-` に変換"},
        "dec_head": "| ID | ルール | 守らせ方 |", "dec_more": "理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。",
        "table_of": "#### {id} の場合分け",
        "con_head": "| 出力 | 置き場 | 件数 | 検査（ルールID） |",
        "con_note": "`{run}` は実行記録の置き場 `.skill-runs/{name}` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。",
        "count": "{low}〜{high} 件", "count_open": "{low} 件以上",
        "name_pattern": "ファイル名が `{p}` に一致", "tamper": "保護ファイルが実行中に変わっていない（{rule}）",
        "scope": "上の出力{allow}のほかに、start の後に変わったファイルが無い（{rule}。git の作業ツリーで判定し、git が無いときは検査しない）",
        "scope_allow": "と、変えてよいファイル {globs}",
        "checks": {
            "headings_equals": "見出し（レベル {level}）が {items} の順で過不足なく並ぶ",
            "headings_includes": "見出し（レベル {level}）に {items} がこの順で含まれる",
            "require": "`{pattern}` に一致する行がある", "forbid": "`{pattern}` に一致する行が無い",
            "require_lines": "{lines} 行目が `{pattern}` に一致する", "forbid_lines": "{lines} 行目が `{pattern}` に一致しない",
            "max_lines": "{value} 行以下", "min_lines": "{value} 行以上",
            "line_length_first": "1行目は {max} 文字以下", "line_length": "各行 {max} 文字以下",
            "json_schema": "JSON スキーマに合う", "front_matter": "front matter に {keys} がある",
            "command": "`{run}` が通る",
        },
        "check_item_finish": "`python3 <skill>/scripts/run.py finish` が終了コード0で終わった",
        "report_intro": "最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。"
                        "決めきれなかったことは、finish の前に `.skill-runs/{name}/notes.md` に「- 」で始まる箇条書きで書く"
                        "（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、"
                        "abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。",
        "report_section": "<`{run}` の出力>",
        "report_output": "<出力 {id} の本文>",
        "report_body": ["## 結果", "", "{name}: 完了（検証に合格）", "", "## 出力", "", "- `<パス>`（<出力ID> <出力の名前>）", "",
                        "## 既定値で決めた値", "", "- <項目>（<キー>）: <値>（無ければ「- なし」）", "",
                        "## 入力で読めなかった値", "", "- <内容>（無ければ「- なし」）", "", "## 検証", "",
                        "- `run.py finish`: 指摘 0 件", "", "## 補足", "", "- <notes.md の箇条書き。無ければ「- なし」>"],
        "ctl_head": "| 仕組み | いつ働くか | 何をするか |",
        "ctl_rows": [
            ["`scripts/run.py start`", "手順の始め", "入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補い、保護ファイルのハッシュと git の作業ツリーの状態を記録する。保護ファイルが合格時の指紋（`assets/seal.json`）と違えば始めない（終了コード1）"],
            ["`scripts/run.py check` と `finish`", "出力を書いた後と最後", "契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える"],
            ["hooks の pre-tool", "ファイルを編集する前", "保護ファイルと実行記録の編集を止める（Claude Code は確認を求め、Codex は拒否する）。実行していないときも、合格時の指紋があるスキルの保護ファイルの編集に Claude Code で確認を求める"],
            ["hooks の post-tool", "ファイルを編集した後", "出力に当たるファイルを format で直し、検査し、指摘を返す。出力でも変えてよいファイルでもなければ CTL-05 の指摘を返す"],
            ["hooks の stop", "応答を終える前", "出力全体を検査し、通るまで応答を終えさせない（最大 {limit} 回。超えると status: failed）"],
            ["hooks の prompt", "ユーザーが発言したとき", "質問待ち（wait）を解くだけ。発言を止めたり書き換えたりしない"],
        ],
        "ctl_note": "hooks は、このスキルの実行中（`.skill-runs/{name}/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。",
        "ctl_change": ["このスキル（ルール、契約、手順、スクリプト）を変えるときは、次の順にする。保護ファイルだけを直接書き換えると、合格時の指紋と違うため次の `run.py start` が止まる（CTL-02）。`<skill-foundation>` は skill-foundation のディレクトリを指す。", "",
                       "1. 実行中なら `python3 <skill>/scripts/run.py abort --reason <理由>` で止める",
                       "2. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す",
                       "3. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す",
                       "4. ルールや契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す",
                       "5. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal` を通す。通ると指紋を記録し直す"],
        "ctl_protected": "保護ファイル（スキルのディレクトリからの相対パス）: {globs}",
        "ctl_install": "hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（{where} に追記する{trust}）",
        "ctl_where": {"claude": "Claude Code は `.claude/settings.json`", "codex": "Codex は `.codex/hooks.json`"}, "ctl_where_sep": "、",
        "ctl_trust": "。Codex では、追記した hooks を `/hooks` で信頼するまで動かない",
        "ctl_nohooks": "このスキルは hooks を使わない（spec の control.hooks が false）。検査は `run.py check` と `finish` で行う。",
        "fmt_head": "自動で直す", "fmt": {"trailing_space": "行末の空白を消す", "final_newline": "末尾の改行を1つにする",
                                       "replace": "`{pattern}` を「{with}」に置き換える", "command": "`{run}` で整える"},
        "together": "- 出力 {ids} は一緒に変える。一部だけを変えると {rule} の指摘になる{message}",
        "decisions_title": "# {title} のルール", "generated": "<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->",
        "fields": {"axes": "軸", "decision": "ルール", "reason": "理由", "control": "守らせ方", "why": "機械化しない理由",
                   "good": "良い例", "bad": "悪い例", "table": "場合分け", "basis": "決め方", "split": "分けた理由",
                   "retired": "廃止（ID は再利用しない）"},
        "purpose_note": "",
    },
    "en": {
        "use": "Use for requests like these.", "not": "Do not use in these cases.", "instead": "use instead",
        "implicit_yes": "Selected automatically from the request. To call it explicitly, write {how}.",
        "implicit_no": "Never selected automatically. Call it with {how}.",
        "call": {"claude": "`/{name}` in Claude Code", "codex": "`${name}` in Codex"}, "call_sep": " or ",
        "inputs_head": "| Item | Key | Accepted forms | When missing |",
        "inputs_none": "There are no input items. Pass only the request text to `run.py start`.",
        "inputs_note": "Pass inputs as `run.py start --set <key>=<value>`. The key may be the key, the item name, or an alias; full-width/half-width, case, and `-`/`_`/space differences are absorbed. Keys not in the contract are ignored and recorded. Pass the request text as the last argument; `key: value` lines in it are also read.",
        "ask": "ask before start: {q}", "default": "default `{v}`", "none": "left empty",
        "aliases": "aliases", "types": {"string": "text", "int": "integer", "bool": "yes/no (true/false, on/off)",
                                     "list": "list (separated by `,` or newlines)", "enum": "one of {choices}",
                                     "path": "path", "slug": "converted to lowercase letters, digits and `-`"},
        "dec_head": "| ID | Rule | Enforced by |", "dec_more": "Reasons and good/bad examples are in [references/decisions.md](references/decisions.md).",
        "table_of": "#### Cases for {id}",
        "con_head": "| Output | Location | Count | Checks (rule ID) |",
        "con_note": "`{run}` is the run record directory `.skill-runs/{name}`. Files that existed before `run.py start` and are unchanged are not checked.",
        "count": "{low}-{high}", "count_open": "{low} or more",
        "name_pattern": "file name matches `{p}`", "tamper": "protected files unchanged during the run ({rule})",
        "scope": "no file other than the outputs above{allow} changed after start ({rule}; judged from the git work tree, not checked without git)",
        "scope_allow": " and the allowed files {globs}",
        "checks": {
            "headings_equals": "level-{level} headings are exactly {items} in this order",
            "headings_includes": "level-{level} headings include {items} in this order",
            "require": "a line matches `{pattern}`", "forbid": "no line matches `{pattern}`",
            "require_lines": "line {lines} matches `{pattern}`", "forbid_lines": "line {lines} does not match `{pattern}`",
            "max_lines": "at most {value} lines", "min_lines": "at least {value} lines",
            "line_length_first": "first line at most {max} characters", "line_length": "each line at most {max} characters",
            "json_schema": "valid against the JSON schema", "front_matter": "front matter has {keys}",
            "command": "`{run}` passes",
        },
        "check_item_finish": "`python3 <skill>/scripts/run.py finish` exited with code 0",
        "report_intro": "Reply with the text printed by `run.py finish` unchanged; do not add text before or after it and do not "
                        "summarize it (RPT-01). Before finish, write anything that could not be decided to "
                        "`.skill-runs/{name}/notes.md` as \"- \" bullets (up to 10); finish puts them under \"## Notes\". "
                        "To stop, run `run.py abort --reason <reason>` and reply with the text it prints in the same way. "
                        "The text has this form.",
        "report_section": "<output of `{run}`>",
        "report_output": "<body of output {id}>",
        "report_body": ["## Result", "", "{name}: done (checks passed)", "", "## Outputs", "", "- `<path>` (<output ID> <output name>)", "",
                        "## Values decided by default", "", "- <item> (<key>): <value> (or \"- None\")", "",
                        "## Inputs that could not be read", "", "- <detail> (or \"- None\")", "", "## Checks", "",
                        "- `run.py finish`: 0 findings", "", "## Notes", "", "- <bullets from notes.md, or \"- None\">"],
        "ctl_head": "| Mechanism | When | What it does |",
        "ctl_rows": [
            ["`scripts/run.py start`", "start of the procedure", "normalizes inputs (accepts variant spellings, full-width text and unknown keys), fills defaults, records hashes of protected files and the git work tree state; does not start when the protected files differ from the seal (`assets/seal.json`) (exit code 1)"],
            ["`scripts/run.py check` and `finish`", "after writing outputs and at the end", "fixes the outputs with the contract's format, then checks them against the contract (`assets/contract.json`); finish ends the run only when they pass"],
            ["pre-tool hook", "before a file edit", "stops edits to protected files and the run record (Claude Code asks the user, Codex denies); when not running, still asks in Claude Code before an edit to a protected file of a sealed skill"],
            ["post-tool hook", "after a file edit", "fixes the edited output file with format, checks it and returns findings; reports CTL-05 for a file that is neither an output nor allowed"],
            ["stop hook", "before the turn ends", "checks all outputs and keeps the turn going until they pass (at most {limit} times, then status: failed)"],
            ["prompt hook", "when the user speaks", "only clears the waiting state; never blocks or rewrites the user's message"],
        ],
        "ctl_note": "Hooks check outputs only while this skill is running (status active in `.skill-runs/{name}/state.json`). Without hooks, `run.py check` and `finish` perform the same checks.",
        "ctl_change": ["To change this skill (rules, contract, procedure, scripts), follow these steps. If only the protected files are edited directly, the next `run.py start` stops because they differ from the seal (CTL-02). `<skill-foundation>` is the directory of skill-foundation.", "",
                       "1. If a run is in progress, stop it with `python3 <skill>/scripts/run.py abort --reason <reason>`",
                       "2. Edit `dev/spec.json`. Edit the hand-written parts (\"2. Procedure\" of this SKILL.md, the skill's own scripts in `scripts/`, `references/`, `assets/examples/`) directly",
                       "3. Regenerate the generated parts with `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>`",
                       "4. If rules or the contract changed, update the probes in `dev/probes.json` and pass `python3 <skill-foundation>/scripts/probe.py <skill>`",
                       "5. Pass `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal`; it seals the skill again"],
        "ctl_protected": "Protected files (relative to the skill directory): {globs}",
        "ctl_install": "Register hooks: `python3 <skill>/scripts/install.py --project <project root>` (adds entries to {where}{trust})",
        "ctl_where": {"claude": "`.claude/settings.json` for Claude Code", "codex": "`.codex/hooks.json` for Codex"}, "ctl_where_sep": " and ",
        "ctl_trust": "; Codex runs them only after you trust them in `/hooks`",
        "ctl_nohooks": "This skill does not use hooks (control.hooks is false in the spec). Checks run through `run.py check` and `finish`.",
        "fmt_head": "fixed automatically", "fmt": {"trailing_space": "remove trailing spaces", "final_newline": "end with exactly one newline",
                                                 "replace": "replace `{pattern}` with \"{with}\"", "command": "format with `{run}`"},
        "together": "- Outputs {ids} change together; changing only some of them is reported as {rule}{message}",
        "decisions_title": "# Rules of {title}", "generated": "<!-- Generated by render_skill.py from dev/spec.json. Do not edit by hand. -->",
        "fields": {"axes": "Axes", "decision": "Rule", "reason": "Reason", "control": "Enforced by", "why": "Why not machine-checked",
                   "good": "Good", "bad": "Bad", "table": "Cases", "basis": "Chosen by", "split": "Why split",
                   "retired": "Retired (the ID is never reused)"},
        "purpose_note": "",
    },
}


def text_of(spec: dict) -> dict:
    return TEXT[_lib.labels(spec)]


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def sort_key(decision: dict):
    rid = decision.get("id", "")
    prefix, _, number = rid.partition("-")
    order = _lib.PREFIXES.index(prefix) if prefix in _lib.PREFIXES else len(_lib.PREFIXES)
    return (order, prefix, int(number) if number.isdigit() else 0)


def decisions_sorted(spec: dict, include_retired: bool = False) -> list[dict]:
    return sorted((d for d in spec.get("decisions", []) if include_retired or not str(d.get("retired", "")).strip()),
                  key=sort_key)


def description(spec: dict) -> str:
    """description の組み立て方を固定する: 目的 → 使う依頼の例 → 使わない場面。"""
    trig = spec.get("triggers", {})
    phrases = trig.get("use_when", [])
    if _lib.labels(spec) == "ja":
        parts = [spec.get("purpose", "").rstrip("。") + "。"]
        if phrases:
            parts.append("、".join(f"「{p}」" for p in phrases) + "と頼まれたときに使う。")
        for item in trig.get("not_for", []):
            parts.append(f"{item.get('when', '')}には使わない（代わりに{item.get('instead', '')}を使う）。")
        return "".join(parts)
    parts = [spec.get("purpose", "").rstrip(".") + "."]
    if phrases:
        parts.append("Use when asked " + ", ".join(f"\"{p}\"" for p in phrases) + ".")
    for item in trig.get("not_for", []):
        parts.append(f"Do not use for {item.get('when', '')} (use {item.get('instead', '')} instead).")
    return " ".join(parts)


def frontmatter(spec: dict) -> str:
    lines = ["---", f"name: {spec['name']}", f"description: {_lib.yaml_quote(description(spec))}"]
    if "claude" in spec.get("targets", []) and spec.get("triggers", {}).get("implicit") is False:
        lines.append("disable-model-invocation: true")
    lines.append("---")
    return "\n".join(lines) + "\n"


def block_purpose(spec: dict) -> str:
    return spec.get("purpose", "") + "\n"


def targets(spec: dict) -> list[str]:
    """対象の製品を claude、codex の順で返す。生成する文に、対象でない製品の呼び方や設定ファイルを書かないため。"""
    return [p for p in ("claude", "codex") if p in spec.get("targets", ["claude", "codex"])]


def ctl_install(spec: dict, t: dict) -> str:
    where = t["ctl_where_sep"].join(t["ctl_where"][p] for p in targets(spec))
    return t["ctl_install"].replace("{where}", where).replace("{trust}", t["ctl_trust"] if "codex" in targets(spec) else "")


def block_triggers(spec: dict) -> str:
    t = text_of(spec)
    trig = spec.get("triggers", {})
    lines = [t["use"], ""] + [f"- 「{p}」" if _lib.labels(spec) == "ja" else f"- \"{p}\"" for p in trig.get("use_when", [])]
    if trig.get("not_for"):
        lines += ["", t["not"], ""]
        lines += [f"- {i.get('when', '')} → {t['instead']}: {i.get('instead', '')}" for i in trig["not_for"]]
    key = "implicit_no" if trig.get("implicit") is False else "implicit_yes"
    how = t["call_sep"].join(t["call"][p] for p in targets(spec))
    lines += ["", t[key].replace("{how}", how).replace("{name}", spec["name"])]
    return "\n".join(lines) + "\n"


def accepted(spec: dict, item: dict) -> str:
    t = text_of(spec)
    kind = item.get("type", "string")
    form = t["types"].get(kind, kind)
    if kind == "enum":
        choices = "、".join(f"`{c}`" for c in item.get("enum", [])) if _lib.labels(spec) == "ja" else \
            ", ".join(f"`{c}`" for c in item.get("enum", []))
        form = form.replace("{choices}", choices)
        if item.get("enum_aliases"):
            form += "（" + "、".join(f"{k}→`{v}`" for k, v in item["enum_aliases"].items()) + "）"
    if item.get("case"):
        form += {"ja": {"upper": "（大文字に揃える）", "lower": "（小文字に揃える）"},
                 "en": {"upper": " (uppercased)", "lower": " (lowercased)"}}[_lib.labels(spec)][item["case"]]
    if item.get("aliases"):
        form += f"。{t['aliases']}: " + "、".join(item["aliases"])
    return form


def block_inputs(spec: dict) -> str:
    t = text_of(spec)
    items = spec.get("inputs", [])
    if not items:
        return t["inputs_none"] + "\n"
    lines = [t["inputs_head"], "|---|---|---|---|"]
    for item in items:
        if item.get("default") is not None:
            missing = t["default"].replace("{v}", json.dumps(item["default"], ensure_ascii=False).strip('"'))
        elif item.get("ask"):
            missing = t["ask"].replace("{q}", item.get("question", ""))
        else:
            missing = t["none"]
        lines.append(f"| {cell(item.get('label', item['key']))} | `{item['key']}` | {cell(accepted(spec, item))} | {cell(missing)} |")
    lines += ["", t["inputs_note"]]
    return "\n".join(lines) + "\n"


def control_text(decision: dict) -> str:
    levels = ", ".join(decision.get("control", []))
    how = decision.get("how", "")
    return f"{levels}: {how}" if how else levels


def block_decisions(spec: dict) -> str:
    t = text_of(spec)
    lines = [t["dec_head"], "|---|---|---|"]
    for d in decisions_sorted(spec):
        lines.append(f"| {d['id']} | {cell(d.get('decision', ''))} | {cell(control_text(d))} |")
    for d in decisions_sorted(spec):
        table = d.get("table")
        if table:
            lines += ["", t["table_of"].replace("{id}", d["id"]), ""]
            lines.append("| " + " | ".join(cell(c) for c in table[0]) + " |")
            lines.append("|" + "---|" * len(table[0]))
            lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in table[1:]]
    lines += ["", t["dec_more"]]
    return "\n".join(lines) + "\n"


def describe_check(spec: dict, check: dict) -> str:
    c = text_of(spec)["checks"]
    kind = check.get("type")
    sep = "、" if _lib.labels(spec) == "ja" else ", "
    if kind == "headings":
        key = "headings_equals" if "equals" in check else "headings_includes"
        items = sep.join(f"「{h}」" if _lib.labels(spec) == "ja" else f"\"{h}\"" for h in check.get("equals", check.get("includes", [])))
        text = c[key].replace("{level}", str(check.get("level", "*"))).replace("{items}", items)
    elif kind in ("require", "forbid"):
        scope = check.get("lines")
        if scope in (None, "all"):
            text = c[kind].replace("{pattern}", check.get("pattern", ""))
        else:
            numbers = "1" if scope == "first" else sep.join(str(n) for n in scope)
            text = c[kind + "_lines"].replace("{pattern}", check.get("pattern", "")).replace("{lines}", numbers)
    elif kind in ("max_lines", "min_lines"):
        text = c[kind].replace("{value}", str(check.get("value")))
    elif kind == "line_length":
        text = c["line_length_first" if check.get("lines") == "first" else "line_length"].replace("{max}", str(check.get("max")))
    elif kind == "front_matter":
        text = c["front_matter"].replace("{keys}", sep.join(f"`{k}`" for k in check.get("required_keys", [])))
    elif kind == "command":
        text = c["command"].replace("{run}", check.get("run", ""))
        if check.get("rules"):
            ids = ("、" if _lib.labels(spec) == "ja" else ", ").join(check["rules"])
            text += f"。{ids} の指摘も出す" if _lib.labels(spec) == "ja" else f"; also reports {ids}"
    else:
        text = c.get(kind, kind)
    if check.get("message"):
        text += f"（{check['message']}）" if _lib.labels(spec) == "ja" else f" ({check['message']})"
    if check.get("stage") == "finish":
        text += "（check・finish・応答を終える前だけ。編集の直後は検査しない）" if _lib.labels(spec) == "ja" else \
            " (check, finish and before ending the turn only; not after each edit)"
    return f"{text}（{check.get('rule')}）" if _lib.labels(spec) == "ja" else f"{text} ({check.get('rule')})"


def describe_format(spec: dict, fix: dict) -> str:
    t = text_of(spec)
    text = (t["fmt"].get(fix.get("type"), str(fix.get("type"))).replace("{pattern}", fix.get("pattern", ""))
            .replace("{with}", fix.get("with", "")).replace("{run}", fix.get("run", "")))
    if _lib.labels(spec) == "ja":
        return f"{t['fmt_head']}: {text}（{fix.get('rule')}）"
    return f"{t['fmt_head']}: {text} ({fix.get('rule')})"


def block_contract(spec: dict) -> str:
    t = text_of(spec)
    lines = [t["con_head"], "|---|---|---|---|"]
    for out in spec.get("outputs", []):
        count = out.get("count", {})
        low = count.get("min", 1 if out.get("required", True) else 0)
        high = count.get("max")
        span = t["count"].replace("{low}", str(low)).replace("{high}", str(high)) if high is not None else \
            t["count_open"].replace("{low}", str(low))
        checks = []
        if out.get("name_pattern"):
            checks.append(t["name_pattern"].replace("{p}", out["name_pattern"]) + f"（{out.get('rule')}）")
        checks += [describe_format(spec, fx) for fx in out.get("format", [])]
        checks += [describe_check(spec, ch) for ch in out.get("checks", [])]
        sep = "。" if _lib.labels(spec) == "ja" else "; "
        lines.append(f"| {cell(out['id'] + ' ' + out.get('label', ''))} | `{out['path']}` | {span}（{out.get('rule')}） | {cell(sep.join(checks)) or '—'} |")
    allow = spec.get("control", {}).get("allow_changes", [])
    globs = ("、" if _lib.labels(spec) == "ja" else ", ").join(f"`{g}`" for g in allow)
    lines += ["", t["con_note"].replace("{name}", spec["name"]), ""]
    for group in spec.get("together", []):
        ids = ("、" if _lib.labels(spec) == "ja" else ", ").join(group.get("outputs", []))
        message = (f"（{group['message']}）" if _lib.labels(spec) == "ja" else f" ({group['message']})") if group.get("message") else ""
        lines.append(t["together"].replace("{ids}", ids).replace("{rule}", group.get("rule", "")).replace("{message}", message))
    lines += ["- " + t["tamper"].replace("{rule}", "CTL-02"),
              "- " + t["scope"].replace("{rule}", "CTL-05").replace(
                  "{allow}", t["scope_allow"].replace("{globs}", globs) if allow else "")]
    return "\n".join(lines) + "\n"


def block_checklist(spec: dict) -> str:
    t = text_of(spec)
    lines = [f"- [ ] {d['id']} {d.get('decision', '')}" for d in decisions_sorted(spec) if "review" in d.get("control", [])]
    lines.append(f"- [ ] {t['check_item_finish']}")
    return "\n".join(lines) + "\n"


def block_report(spec: dict) -> str:
    t = text_of(spec)
    body = []
    include = spec.get("report", {}).get("include_output")
    if include:
        body += [t["report_output"].replace("{id}", include), "", "---", ""]
    lines = [line.replace("{name}", spec["name"]) for line in t["report_body"]]
    sections = [t["report_section"].replace("{run}", s["run"]) for s in spec.get("report", {}).get("sections", [])]
    for text in reversed(sections):
        lines[4:4] = [text, ""]  # 「## 結果」の行と完了の行の後に入れる
    body += lines
    intro = t["report_intro"].replace("{name}", spec["name"])
    return "\n".join([intro, "", "```text", *body, "```"]) + "\n"


def block_control(spec: dict) -> str:
    t = text_of(spec)
    control = spec.get("control", {})
    globs = ("、" if _lib.labels(spec) == "ja" else ", ").join(f"`{g}`" for g in control.get("protected", []))
    if control.get("hooks", True) is False:
        lines = [t["ctl_head"], "|---|---|---|", *["| " + " | ".join(r) + " |" for r in t["ctl_rows"][:2]], "",
                 t["ctl_nohooks"]]
    else:
        rows = [[c.replace("{limit}", str(control.get("max_stop_blocks", 3))) for c in r] for r in t["ctl_rows"]]
        lines = [t["ctl_head"], "|---|---|---|", *["| " + " | ".join(r) + " |" for r in rows], "",
                 t["ctl_note"].replace("{name}", spec["name"]), "", ctl_install(spec, t)]
    lines += ["", t["ctl_protected"].replace("{globs}", globs), "", *t["ctl_change"]]
    return "\n".join(lines) + "\n"


RENDERERS = {"purpose": block_purpose, "triggers": block_triggers, "inputs": block_inputs, "decisions": block_decisions,
             "contract": block_contract, "checklist": block_checklist, "report": block_report, "control": block_control}


def decisions_md(spec: dict) -> str:
    t = text_of(spec)
    f = t["fields"]
    lines = [t["generated"], "", t["decisions_title"].replace("{title}", spec.get("title", spec["name"]))]
    lang = 0 if _lib.labels(spec) == "ja" else 1
    for d in decisions_sorted(spec, include_retired=True):
        lines += ["", f"## {d['id']} {d.get('title', '')}", "", f"- {f['axes']}: {', '.join(d.get('axes', []))}"]
        if str(d.get("retired", "")).strip():
            lines.append(f"- {f['retired']}: {d['retired']}")
            continue
        lines += [f"- {f['decision']}: {d.get('decision', '')}",
                  f"- {f['reason']}: {d.get('reason', '')}",
                  f"- {f['basis']}: {_lib.BASES.get(d.get('basis'), (d.get('basis'),) * 2)[lang]}",
                  f"- {f['control']}: {control_text(d)}"]
        if d.get("split_reason"):
            lines.append(f"- {f['split']}: {d['split_reason']}")
        if d.get("why_not_machine"):
            lines.append(f"- {f['why']}: {d['why_not_machine']}")
        if d.get("table"):
            table = d["table"]
            lines += ["", f"{f['table']}:", "", "| " + " | ".join(cell(c) for c in table[0]) + " |",
                      "|" + "---|" * len(table[0])]
            lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in table[1:]]
            lines.append("")
        lines += [f"- {f['good']}:", "", "  ```text", *["  " + l for l in str(d.get("good", "")).splitlines()], "  ```",
                  f"- {f['bad']}:", "", "  ```text", *["  " + l for l in str(d.get("bad", "")).splitlines()], "  ```"]
    return "\n".join(lines) + "\n"


def contract(spec: dict) -> dict:
    control = spec.get("control", {})
    return {
        "contract_version": 1,
        "generated_by": "render_skill.py（dev/spec.json から生成。手で編集しない）",
        "skill": spec["name"],
        "language": _lib.labels(spec),
        "targets": targets(spec),
        "inputs": spec.get("inputs", []),
        "outputs": spec.get("outputs", []),
        "together": spec.get("together", []),
        "control": {"hooks": control.get("hooks", True), "protected": control.get("protected", []),
                    "tamper_rule": "CTL-02", "scope_rule": "CTL-05", "allow_changes": control.get("allow_changes", []),
                    "max_stop_blocks": control.get("max_stop_blocks", 3)},
        "report": {"include_output": spec.get("report", {}).get("include_output"), "rule": "RPT-01",
                   "sections": spec.get("report", {}).get("sections", [])},
    }


def profiles_md() -> str:
    """skill-foundation 自身の references/skill-profiles.md。正本は assets/skill-profiles.json。"""
    axes = {code: name for code, (_, name, _) in _lib.AXES.items()}
    lines = ["<!-- このファイルは render_skill.py が assets/skill-profiles.json から生成する。手で編集しない。 -->", "",
             "# スキルの種類ごとの観点", "",
             "作るスキルの種類（spec の `kind`）は、名前の動詞と同じである（[intake.md](intake.md) の2章）。種類ごとに、"
             "ばらつきやすい点がおおむね決まっている。そこで、種類ごとに次の6つを固定する。同じ種類のスキルを別々の AI が作っても、"
             "ルールの構成と ID、入力のキーが揃うようにするためである。", "",
             "- 軸の読み替え：その種類で、軸を具体的に何と読むか（フェーズ3）",
             "- 追加の軸：`init_skill.py` が `extra_axes` の先頭（X1 から）に入れる。ルールを書くか、`excluded_axes` に理由を書く（フェーズ1・3）",
             "- 重点軸：特にばらつきやすい軸。`excluded_axes` にできない（`skill_lint.py`）",
             "- 入力の候補：その種類で依頼に無いことが多い入力。`inputs` に同じ `key` で入れるか、`excluded_inputs` に `key` と理由を書く（フェーズ3。`skill_lint.py`）",
             "- 調べる先：フェーズ2で事実を確かめる当たり先（[research.md](research.md) の2章）",
             "- 検査の候補と課題の例：契約の `checks`（フェーズ4）と `dev/evals.json`（フェーズ6）を作るときの当たり先", ""]
    for kind, p in _lib.load_profiles().items():
        lines += [f"## {kind}", "", f"出力: {p['label']}", "", "| 軸 | この種類での読み方 |", "|---|---|"]
        lines += [f"| {code} {axes.get(code, '')} | {cell(text)} |" for code, text in p.get("readings", {}).items()]
        lines += ["", "| 追加の軸 | 接頭辞 | 名前 |", "|---|---|---|"]
        lines += [f"| X{i} | {a['prefix']} | {cell(a['name']['ja'])} |" for i, a in enumerate(p.get("extra_axes", []), 1)]
        lines += ["", "重点軸: " + "、".join(f"{c} {axes.get(c, '')}" for c in p.get("focus", [])), "",
                  "| 入力の候補（key） | 名前 | impact |", "|---|---|---|"]
        lines += [f"| `{i['key']}` | {cell(i['label']['ja'])} | `{i['impact']}` |" for i in p.get("inputs", [])]
        lines += ["", f"調べる先: {p.get('research', {}).get('ja', '')}", "", "検査の候補:", ""] + [f"- {c}" for c in p.get("checks", [])]
        lines += ["", "課題の例:", ""] + [f"- `{k}`: {v}" for k, v in p.get("evals", {}).items()] + [""]
    return "\n".join(lines).rstrip() + "\n"


def render_all(skill_dir: Path, spec: dict) -> dict[str, str]:
    """生成物の一覧（相対パス → 内容）。SKILL.md は既存の内容の生成部分だけを置き換える。"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        _lib.fail(f"{skill_md} がありません。先に init_skill.py を実行してください")
    current = skill_md.read_text(encoding="utf-8")
    _, body = _lib.parse_frontmatter(current)
    text = frontmatter(spec) + body
    for block_id in _lib.BLOCKS:
        try:
            text = _lib.replace_block(text, block_id, RENDERERS[block_id](spec))
        except KeyError:
            _lib.fail(f"SKILL.md に生成部分 {block_id} の目印がありません（<!-- BEGIN GENERATED:{block_id} --> と END）。"
                      "ひな形から目印を戻してください")
    files = {
        "SKILL.md": text,
        "references/decisions.md": decisions_md(spec),
        "assets/contract.json": json.dumps(contract(spec), ensure_ascii=False, indent=2) + "\n",
    }
    if _lib.is_foundation(skill_dir):
        files["references/skill-profiles.md"] = profiles_md()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", required=True, help="スキルのディレクトリ（dev/spec.json がある場所）")
    parser.add_argument("--check", action="store_true", help="書き込まずに、生成物が最新かだけを調べる")
    args = parser.parse_args()
    skill_dir = Path(args.dir).resolve()
    spec = _lib.load_spec(skill_dir)
    stale = []
    for rel, content in render_all(skill_dir, spec).items():
        target = skill_dir / rel
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current == content:
            continue
        stale.append(rel)
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    if args.check:
        for rel in stale:
            print(f"ERROR {rel} が dev/spec.json と合っていません。render_skill.py --dir {args.dir} を実行してください")
        print(f"render --check: 古い生成物 {len(stale)} 件")
        return 1 if stale else 0
    print(f"render: {len(stale)} 件を書き換えました" + (f"（{', '.join(stale)}）" if stale else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
