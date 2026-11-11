#!/usr/bin/env python3
"""hooks の登録とユーザーの設定（settings/user-setting.yaml）を、選ぶだけで行う。skill-foundation の共通ランタイム。

利用者が自分で行う準備なので、SKILL.md の手順からは呼ばない。ターミナル（TTY）で実行すると対話の画面が開く。
矢印キーとスペースで選び（curses）、curses が使えない環境（Windows など）や --plain では番号で選ぶ。
どの画面でも「戻る」と「中止（何も書かない）」を選べ、書く前に、変わるファイルごとの差分を見せて確かめる。
  hooks           : 製品・機能・登録先を選ぶ。書き込みは install.py の処理（plan_hooks、apply_hooks、place）を使う
  ユーザーの設定 : 項目ごとに今効いている値と出どころを見せ、値は定義から作った選択肢で選ぶ。定義は、inputs が
                    契約（assets/contract.json）の inputs、ほかの欄が assets/settings.schema.json。上書きの前に .bak を残し、
                    書いた後に load_settings で読み直して検査する
TTY が無いとき（AI のツール実行、CI など）は画面を開かず、終了コード2で、同じことを行う引数を示す。

登録先は install.py と同じ規則で決める。--project がホーム（~）か --scope user ならユーザー単位（~/.claude/settings.json、
~/.codex/hooks.json に登録し、どのプロジェクトのセッションでも動く）。本体を ~/.claude/skills か ~/.agents/skills に
置いたときは、--project を省くとユーザー単位になる。

使い方:
  python3 <skill>/scripts/setup.py [--project <ルート> | --scope user|project] [--plain]
  python3 <skill>/scripts/setup.py [--project <ルート>] --status
  python3 <skill>/scripts/setup.py [--project <ルート>] [--hooks claude,codex|none] [--features check,feedback]
                                   [--set inputs.measure=run ...] [--yes]     # 非対話。--yes が無ければ差分を見せるだけ
終了コード: 0 書いた・変更なし・中止、1 書いた後の検査で問題がある、2 引数の誤り・TTY が無い
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import locale
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402
import install  # noqa: E402

USER_REL = dict(rt.SETTINGS_FILES)["user"]
SKILL_REL = dict(rt.SETTINGS_FILES)["skill"]
PRODUCTS = ["claude", "codex"]

TEXT = {
    "ja": {
        "title": "{name} の setup",
        "intro": ["hooks の登録と、ユーザーの設定（{user}）を、選ぶだけで行います。",
                  "書く前に、変わるファイルごとの差分を見せて確かめます。"],
        "menu": ["hooks を設定する", "ユーザーの設定を作る", "両方", "今の状態を見る", "終わる"],
        "back": "戻る", "cancel": "中止（何も書かない）", "done": "決める",
        "keys": "↑↓ 移動  Space 選ぶ  Enter 決める  b 戻る  q 中止",
        "keys_scroll": "  PgUp/PgDn 上の文 {at}/{total}",
        "keys_text": "Enter 決める（空なら戻る）  Esc 中止",
        "small": "端末が小さすぎます。広げてください（q 中止）",
        "plain_pick": "番号を入力して Enter（b 戻る、q 中止）: ",
        "plain_many": "番号で選ぶ・外す。「{done}」の番号で決める（b 戻る、q 中止）: ",
        "plain_text": "値を入力して Enter（空なら戻る、:q で中止）: ",
        "plain_bad": "一覧の番号を入力してください",
        "need_one": "1つ以上選んでください",
        "products": "hooks を登録する製品を選んでください",
        "products_info": "選ばなかった製品からは、このスキルの hooks を外します。",
        "product": "{name}（{where}）",
        "product_name": {"claude": "Claude Code", "codex": "Codex"},
        "unhooked": "hooks の方針で登録しない製品: {products}",
        "features": "有効にする機能を選んでください",
        "feature": {"check": "出力の検査（編集の後と応答を終える前に、出力を検査する）",
                    "feedback": "利用中の指摘の収集（完了の後の指摘と、直す前と後の成果物を記録する）"},
        "feature_name": {"check": "出力の検査", "feedback": "利用中の指摘の収集"},
        "dest": "hooks をどこに登録しますか",
        "dest_items": ["プロジェクトの設定ファイル", "登録しない（今の登録を外す）"],
        "dest_user": "ユーザーの設定ファイル（{where}。どのプロジェクトのセッションでも動く）",
        "chosen": "選んだもの: {products}（{features}）",
        "plugin_on": "注意: プラグインの hooks が有効です（{where}）。ここにも登録すると、hooks が二重に動きます",
        "nohooks": "このスキルは hooks を使わない方針です（契約の control.hooks が false）。登録を外すことだけができます。",
        "nofeedback": "このスキルは利用中の指摘を集めない方針です（契約の control.feedback が false）。",
        "now": "今: {state}",
        "reg_none": "登録なし", "reg_some": "登録あり（{features}）", "sep": "・", "list_sep": "、",
        "settings": "ユーザーの設定（{user}）",
        "settings_info": ["項目を選ぶと値を変えられます。各行は、今効いている値と出どころです。＊は変えた項目です。",
                          "null の項目は、スキルの設定（{skill}）の値を使います。"],
        "settings_next": "書く前の確認へ進む",
        "source": {"user": "ユーザーの設定", "skill": "スキルの設定"},
        "unset_input": "設定なし。依頼で決め、無ければ既定値 {value}",
        "unset_input_none": "設定なし。依頼で決める",
        "unset": "設定なし",
        "item": "{path} の値を選んでください",
        "item_now": "今: {value}（{source}）",
        "keep": "変えない（null。スキルの設定の {value} を使う）",
        "keep_none": "変えない（null）",
        "other": "値を入力する",
        "current": "（今）",
        "ask": "{path} の値を入力してください（{range}）",
        "range": {"count": "1 以上の整数", "rate": "0 から 1 の数", "text": "空でない文字列", "int": "整数",
                  "list": "`,` で区切った一覧", "string": "文字列", "path": "パス", "slug": "英小文字・数字・-", "bool": "true か false"},
        "choices": "{choices} のどれか", "choices_many": "{choices} から1つ以上", "suggest": "例 {choices}",
        "confirm": "書く前の確認",
        "confirm_info": "次のとおり書きます。よければ「書く」を選んでください。",
        "write": "書く", "finish": "終わる",
        "nothing": "変わるところはありません。",
        "file_new": "== {rel}（新しく作る） ==", "file_change": "== {rel}（変える） ==",
        "whole": "-- 書いた後の全体 --", "diff": "-- 今のファイルとの差分 --",
        "now_file": "今", "after_file": "書いた後",
        "place": "置き場所: {change}",
        "written": "書きました: {rel}", "backup": "前の内容を {rel} に残しました", "placed": "置きました: {change}",
        "no_write": "変わるところが無いので、何も書いていません",
        "check": "hooks の登録の検査（install --check）: 問題 {n} 件",
        "left": "{rel} に、このスキルの hooks が残っています",
        "settings_check": "ユーザーの設定の検査（load_settings）: 問題 {n} 件",
        "trust": "Codex は、足した hooks を Codex の `/hooks` で信頼するまで動きません。それまでは run.py の check と finish だけで検査されます",
        "restart": "Claude Code は、起動し直すと登録を読み込みます",
        "git": "{rel} は Git の管理から外れていません。人ごとの設定なので、.gitignore に足すことを勧めます",
        "cancelled": "中止しました。どのファイルも変えていません",
        "finished": "終わりました。何も書いていません",
        "no_tty": "setup.py は、対話の画面をターミナル（TTY）で開きます。今は TTY が無いので開きません。",
        "no_tty_args": "AI のツールや CI からは、同じことを引数で行えます（--yes が無ければ、書く前の差分を見せるだけ）:",
        "status": "今の状態",
        "status_skill": "スキル: {name}（{where}）",
        "status_hooks": "hooks の登録:",
        "status_scope_user": "登録先: ユーザー単位（{root}）。作ったスキルと実行記録（.skill-runs/、.skill-feedback/）は、使ったセッションのプロジェクトに置かれる",
        "status_scope_project": "登録先: プロジェクト（{root}）。どのプロジェクトからでも使うときは、本体を ~/.claude/skills に置いて --scope user を付ける",
        "status_plugins_none": "プラグインの hooks: 有効なものは無い",
        "status_plugins": "プラグインの hooks: 有効（{where}）",
        "status_settings": "ユーザーの設定: {user}（{state}）",
        "exists": "あり", "missing": "まだ無い",
        "status_problems": "設定の問題:",
        "args_error": "引数の誤り: {why}",
        "unknown_path": "{path} は選べる設定の項目にありません（{paths}）",
        "no_eq": "--set は <項目>=<値> の形にしてください: {item}",
        "features_alone": "--features は --hooks と一緒に指定してください",
        "unknown_products": "{bad} は hooks を登録できる製品にありません（{ok}）",
        "unknown_features": "{bad} は使える機能にありません（{ok}）",
        "yes_hint": "書くには --yes を付けて実行し直してください",
        "unreadable": "注意: {rel} を読めないので、空の設定から作ります（{why}）",
        "header": "# ユーザーの設定。setup.py で作った。依頼に指定の無い値をここから補う（依頼文や作業の途中の指示がいつも優先される）",
        "header2": "# null の項目は {skill}（スキルの設定）の値を使う。# から行末まではコメント",
        "inputs_label": "入力の既定値",
    },
    "en": {
        "title": "{name} setup",
        "intro": ["Register hooks and create the user setting ({user}) by choosing options.",
                  "Before writing, the changes to each file are shown as a diff."],
        "menu": ["Set up hooks", "Create the user setting", "Both", "Show the current state", "Quit"],
        "back": "Back", "cancel": "Cancel (write nothing)", "done": "Done",
        "keys": "Up/Down move  Space select  Enter choose  b back  q cancel",
        "keys_scroll": "  PgUp/PgDn text {at}/{total}",
        "keys_text": "Enter choose (empty goes back)  Esc cancel",
        "small": "The terminal is too small. Enlarge it (q cancel)",
        "plain_pick": "Enter a number (b back, q cancel): ",
        "plain_many": "Enter numbers to select or clear; the number of \"{done}\" to finish (b back, q cancel): ",
        "plain_text": "Enter a value (empty goes back, :q cancels): ",
        "plain_bad": "Enter a number from the list",
        "need_one": "Select at least one",
        "products": "Choose the products to register hooks for",
        "products_info": "This skill's hooks are removed from products you do not choose.",
        "product": "{name} ({where})",
        "product_name": {"claude": "Claude Code", "codex": "Codex"},
        "unhooked": "Products the hooks plan leaves out: {products}",
        "features": "Choose the features to enable",
        "feature": {"check": "Output checks (after edits and before ending a reply)",
                    "feedback": "Feedback collection (feedback after completion, outputs before and after fixes)"},
        "feature_name": {"check": "output checks", "feedback": "feedback collection"},
        "dest": "Where should the hooks be registered?",
        "dest_items": ["The project's settings files", "Do not register (remove the current entries)"],
        "dest_user": "The user's settings files ({where}; runs in every project's sessions)",
        "chosen": "Chosen: {products} ({features})",
        "plugin_on": "Note: plugin hooks are enabled ({where}). Registering them here too runs the hooks twice",
        "nohooks": "This skill does not use hooks (control.hooks is false in the contract). You can only remove entries.",
        "nofeedback": "This skill does not collect feedback (control.feedback is false in the contract).",
        "now": "Now: {state}",
        "reg_none": "not registered", "reg_some": "registered ({features})", "sep": ", ", "list_sep": ", ",
        "settings": "User setting ({user})",
        "settings_info": ["Choose an item to change its value. Each row shows the value in effect and where it comes from. * marks changed items.",
                          "Items left null use the skill setting ({skill})."],
        "settings_next": "Review before writing",
        "source": {"user": "user setting", "skill": "skill setting"},
        "unset_input": "not set; decided by the request, else the default {value}",
        "unset_input_none": "not set; decided by the request",
        "unset": "not set",
        "item": "Choose the value of {path}",
        "item_now": "Now: {value} ({source})",
        "keep": "Leave unset (null; use the skill setting {value})",
        "keep_none": "Leave unset (null)",
        "other": "Enter a value",
        "current": " (now)",
        "ask": "Enter the value of {path} ({range})",
        "range": {"count": "an integer of 1 or more", "rate": "a number from 0 to 1", "text": "a non-empty string",
                  "int": "an integer", "list": "a list separated by `,`", "string": "a string", "path": "a path",
                  "slug": "lowercase letters, digits and -", "bool": "true or false"},
        "choices": "one of {choices}", "choices_many": "one or more of {choices}", "suggest": "e.g. {choices}",
        "confirm": "Review before writing",
        "confirm_info": "The following will be written. Choose \"Write\" to go ahead.",
        "write": "Write", "finish": "Quit",
        "nothing": "Nothing changes.",
        "file_new": "== {rel} (new) ==", "file_change": "== {rel} (changed) ==",
        "whole": "-- Whole file after writing --", "diff": "-- Diff from the current file --",
        "now_file": "now", "after_file": "after",
        "place": "Placement: {change}",
        "written": "Wrote: {rel}", "backup": "Kept the previous content in {rel}", "placed": "Placed: {change}",
        "no_write": "Nothing changes, so nothing was written",
        "check": "Hook registration check (install --check): {n} problem(s)",
        "left": "This skill's hooks remain in {rel}",
        "settings_check": "User setting check (load_settings): {n} problem(s)",
        "trust": "Codex runs the added hooks only after you trust them in Codex's `/hooks`. Until then, only run.py check and finish check outputs",
        "restart": "Claude Code reads the registration after a restart",
        "git": "{rel} is not ignored by Git. It holds personal settings, so consider adding it to .gitignore",
        "cancelled": "Cancelled. No file was changed",
        "finished": "Done. Nothing was written",
        "no_tty": "setup.py opens its screens in a terminal (TTY). There is no TTY now, so it does not open them.",
        "no_tty_args": "From AI tools or CI, do the same with arguments (without --yes, only the diff is shown):",
        "status": "Current state",
        "status_skill": "Skill: {name} ({where})",
        "status_hooks": "Hook registration:",
        "status_scope_user": "Scope: user ({root}). Skills you create and run records (.skill-runs/, .skill-feedback/) go to the project of the session that uses it",
        "status_scope_project": "Scope: project ({root}). To use it from any project, put the skill in ~/.claude/skills and pass --scope user",
        "status_plugins_none": "Plugin hooks: none enabled",
        "status_plugins": "Plugin hooks: enabled ({where})",
        "status_settings": "User setting: {user} ({state})",
        "exists": "exists", "missing": "not yet created",
        "status_problems": "Setting problems:",
        "args_error": "Invalid arguments: {why}",
        "unknown_path": "{path} is not a setting you can choose ({paths})",
        "no_eq": "--set takes <item>=<value>: {item}",
        "features_alone": "Use --features together with --hooks",
        "unknown_products": "{bad} cannot have hooks ({ok})",
        "unknown_features": "{bad} is not an available feature ({ok})",
        "yes_hint": "Run again with --yes to write",
        "unreadable": "Note: {rel} cannot be read, so the setting starts empty ({why})",
        "header": "# User setting, created by setup.py. Fills values the request does not give (the request and later instructions always win)",
        "header2": "# Items left null use {skill} (the skill setting). Text from # to the end of a line is a comment",
        "inputs_label": "defaults for inputs",
    },
}


class Back(Exception):
    """画面の「戻る」。"""


class Cancel(Exception):
    """画面の「中止」。何も書かずに終える。"""


class UsageError(Exception):
    """非対話モードの引数の誤り。"""


# ---------------------------------------------------------------- スキルと設定

class Context:
    """setup の対象（このスキルとプロジェクト）。"""

    def __init__(self, root: Path):
        self.root = root
        self.user = install.is_user_root(root)  # ユーザー単位（ホームに登録し、どのプロジェクトでも動く）
        self.skill_dir = rt.SKILL_DIR
        self.contract = rt.load_contract()
        self.name = self.contract.get("skill") or self.skill_dir.name
        self.t = TEXT["en" if self.contract.get("language") == "en" else "ja"]
        control = self.contract.get("control", {})
        self.targets = [p for p in PRODUCTS if p in (self.contract.get("targets") or PRODUCTS)]
        self.hook_products = [p for p in self.targets if p in control.get("hook_targets", self.targets)]
        self.hooks_allowed = control.get("hooks", True) is not False
        self.features = [f for f in install.FEATURES if f != "feedback" or control.get("feedback", True) is not False]
        self.sections = rt.settings_schema()
        self.notes: list[str] = []
        self.user_data = self.read(USER_REL)
        self.skill_data = self.read(SKILL_REL)

    def read(self, rel: str) -> dict:
        path = self.skill_dir / rel
        if not path.is_file():
            return {}
        try:
            data = rt.load_yaml(path)
        except (OSError, ValueError) as exc:
            self.notes.append(self.t["unreadable"].format(rel=rel, why=exc))
            return {}
        return data if isinstance(data, dict) else {}

    def config(self, platform: str) -> str:
        """画面に出す、hooks の設定ファイルの場所。"""
        return self.shown(self.root / install.CONFIGS[platform])

    def dest_items(self) -> list[str]:
        items = list(self.t["dest_items"])
        if self.user:
            items[0] = self.t["dest_user"].format(where=self.t["list_sep"].join(self.config(p) for p in self.hook_products))
        return items

    def shown(self, path: Path) -> str:
        """画面に出すパス（プロジェクトの中は相対、ホームの中は ~/）。"""
        path = path.resolve() if path.exists() else path
        bases = ((Path.home(), "~/"), (self.root, "")) if self.user else ((self.root, ""), (Path.home(), "~/"))
        for base, head in bases:
            try:
                rel = path.relative_to(base).as_posix()
                return (head + rel) if rel != "." else (head.rstrip("/") or ".")
            except ValueError:
                continue
        return path.as_posix()


def dig(data, path: tuple):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def put(data: dict, path: tuple, value) -> None:
    for key in path[:-1]:
        if not isinstance(data.get(key), dict):
            data[key] = {}
        data = data[key]
    data[path[-1]] = value


def show(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(show(v) for v in value)
    return str(value)


def setting_items(ctx: Context) -> list[dict]:
    """選べる設定の項目。inputs は契約の入力のうち、毎回聞くもの（ask）とほかの入力から決まるもの（default_by）を除く。"""
    items = [{"path": ("inputs", spec["key"]), "label": spec.get("label") or spec["key"], "input": spec}
             for spec in ctx.contract.get("inputs", []) if not spec.get("ask") and not spec.get("default_by")]

    def walk(defs: dict, path: tuple) -> None:
        for key, item in defs.items():
            if "items" in item:
                walk(item["items"], path + (key,))
            else:
                items.append({"path": path + (key,), "label": item.get("label") or key, "def": item})

    for name, section in ctx.sections.items():
        walk(section.get("items", {}), (name,))
    return items


def how_to_pick(item: dict) -> tuple[str, list]:
    """画面での選び方（one: 1つ選ぶ、many: 複数選ぶ、type: 入力する）と候補。"""
    spec = item.get("input")
    if spec:
        kind = spec.get("type", "string")
        if kind == "enum":
            return "one", list(spec.get("enum", []))
        if kind == "list" and spec.get("enum"):
            return "many", list(spec["enum"])
        return ("one", [True, False]) if kind == "bool" else ("type", [])
    d = item["def"]
    if d.get("type") in ("choice", "choices"):
        return ("one" if d["type"] == "choice" else "many"), list(d.get("choices", []))
    return ("one", list(d["suggest"])) if d.get("type") == "text" and d.get("suggest") else ("type", [])


def parse_value(item: dict, text: str):
    """入力された文字列を項目の値にする。`null` は値なし。使えなければ ValueError（理由の文）。"""
    text = text.strip()
    if text == "null":
        return None
    if item.get("input"):
        return rt.convert(text, item["input"])
    d = item["def"]
    value: object = text
    if d.get("type") == "choices":
        value = [v for v in re.split(r"[,、，\s]+", text) if v]
    elif d.get("type") == "count" and re.fullmatch(r"[-+]?\d+", text):
        value = int(text)
    elif d.get("type") == "rate":
        try:
            value = float(text)
        except ValueError:
            pass
    problem = rt.setting_problem(d, value)
    if problem:
        raise ValueError(problem)
    return value


def effective(ctx: Context, values: dict, item: dict) -> tuple[object, str]:
    """今効いている値と出どころ（ユーザーの設定 → スキルの設定）。"""
    t = ctx.t
    for source, data in (("user", values), ("skill", ctx.skill_data)):
        value = dig(data, item["path"])
        if value is not None:
            return value, t["source"][source]
    default = (item.get("input") or {}).get("default")
    if item.get("input"):
        return None, t["unset_input"].format(value=show(default)) if default is not None else t["unset_input_none"]
    return None, t["unset"]


def item_help(t: dict, item: dict) -> str:
    """設定ファイルのコメントに書く、項目の説明と書ける値。"""
    how, choices = how_to_pick(item)
    kind = (item.get("input") or item["def"]).get("type", "string")
    if how in ("one", "many") and choices:
        words = t["list_sep"].join(show(c) for c in choices)
        if kind == "text":
            more = t["suggest"].format(choices=words)
        else:
            more = t["choices_many" if how == "many" else "choices"].format(choices=words)
    else:
        more = t["range"].get(kind, kind)
    return f"{item['label']}。{more}" if t is TEXT["ja"] else f"{item['label']}. {more}"


def yaml_value(value) -> str:
    """load_yaml が同じ値に読み戻せる1行の書き方。"""
    if value is None or isinstance(value, (bool, int, float)):
        return show(value) if not isinstance(value, float) else repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(yaml_value(v) for v in value) + "]"
    text = str(value)
    plain = re.fullmatch(r"[A-Za-z_./~][\w./@~+-]*", text) and rt._yaml_scalar(text, 0) == text
    return text if plain else json.dumps(text, ensure_ascii=False)


def settings_text(ctx: Context, values: dict) -> str:
    """ユーザーの設定ファイルの中身。項目は定義の順に、値（無ければ null）と説明のコメントを書く。"""
    t, by_path = ctx.t, {item["path"]: item for item in setting_items(ctx)}
    lines = [t["header"], t["header2"].format(skill=SKILL_REL), f"inputs: # {t['inputs_label']}"]
    for spec in ctx.contract.get("inputs", []):
        path = ("inputs", spec["key"])
        if path in by_path or dig(values, path) is not None:  # 選べない入力も、書いてあれば残す
            item = by_path.get(path) or {"path": path, "label": spec.get("label") or spec["key"], "input": spec}
            lines.append(f"  {spec['key']}: {yaml_value(dig(values, path))} # {item_help(t, item)}")

    def walk(defs: dict, path: tuple, depth: int) -> None:
        for key, item in defs.items():
            pad = "  " * depth
            if "items" in item:
                lines.append(f"{pad}{key}: # {item.get('label', '')}")
                walk(item["items"], path + (key,), depth + 1)
            else:
                lines.append(f"{pad}{key}: {yaml_value(dig(values, path + (key,)))} # {item_help(t, by_path[path + (key,)])}")

    for name, section in ctx.sections.items():
        lines.append(f"{name}: # {section.get('label', '')}")
        walk(section.get("items", {}), (name,), 1)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- hooks の状態

def plugin_names(ctx: Context) -> set[str]:
    """このスキルを配るプラグインの名前の候補（スキルの名前と、プラグインの中にあればその plugin.json の name）。"""
    names = {ctx.name}
    if ctx.skill_dir.parent.name == "skills":
        for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            try:
                names.add(json.loads((ctx.skill_dir.parent.parent / rel).read_text(encoding="utf-8")).get("name") or "")
            except (OSError, ValueError, AttributeError):
                continue
    return names - {""}


def plugins_on(ctx: Context) -> list[str]:
    """有効になっている、このスキルのプラグイン（Claude Code の enabledPlugins、Codex の config.toml の [plugins."..."]）。"""
    names, found, home = plugin_names(ctx), [], Path.home()
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or home / ".claude")
    for path in (claude_home / "settings.json", ctx.root / ".claude/settings.json", ctx.root / ".claude/settings.local.json"):
        try:
            enabled = json.loads(path.read_text(encoding="utf-8")).get("enabledPlugins") or {}
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(enabled, dict):
            found += [f"Claude Code {key}（{ctx.shown(path)}）" for key, on in enabled.items()
                      if on is True and key.split("@")[0] in names]
    codex_home = Path(os.environ.get("CODEX_HOME") or home / ".codex")
    for path in (codex_home / "config.toml", ctx.root / ".codex/config.toml"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in re.finditer(r'^\[plugins\."([^"]+)"\][^\n]*\n((?:(?!\[).*\n?)*)', text, re.M):
            if match.group(1).split("@")[0] in names and re.search(r"^\s*enabled\s*=\s*true\b", match.group(2), re.M):
                found.append(f"Codex {match.group(1)}（{ctx.shown(path)}）")
    return found


def registered_text(t: dict, features: set[str] | None) -> str:
    if features is None:
        return t["reg_none"]
    return t["reg_some"].format(features=t["sep"].join(t["feature_name"][f] for f in install.FEATURES if f in features))


def status_lines(ctx: Context) -> list[str]:
    t = ctx.t
    lines = [t["status_skill"].format(name=ctx.name, where=ctx.shown(ctx.skill_dir)),
             t["status_scope_user" if ctx.user else "status_scope_project"].format(root=ctx.shown(ctx.root) if ctx.user else ctx.root),
             t["status_hooks"]]
    if not ctx.hooks_allowed:
        lines.append("  " + t["nohooks"])
    for p in ctx.hook_products:
        lines.append(f"  {t['product_name'][p]}: {registered_text(t, install.registered(ctx.root, p, ctx.name))}"
                     f"（{ctx.config(p)}）")
    plugins = plugins_on(ctx)
    lines.append(t["status_plugins"].format(where=t["list_sep"].join(plugins)) if plugins else t["status_plugins_none"])
    user = ctx.skill_dir / USER_REL
    lines.append(t["status_settings"].format(user=ctx.shown(user), state=t["exists" if user.is_file() else "missing"]))
    for item in setting_items(ctx):
        value, source = effective(ctx, ctx.user_data, item)
        lines.append(f"  {'.'.join(item['path'])} = {show(value)}（{source}）")
    problems = ctx.notes + rt.check_settings(ctx.skill_dir)
    return lines + ([t["status_problems"], *[f"  {p}" for p in problems]] if problems else [])


# ---------------------------------------------------------------- 書くもの

def planned(ctx: Context, state: dict) -> tuple[list[dict], list[str]]:
    """書くファイル（rel、before、after、lines、whole）と、置き場所の変更。state は画面か引数で選んだもの。"""
    files, places = [], []
    if state.get("hooks"):
        register = state.get("register", False) and ctx.hooks_allowed
        features = set(state.get("features") or ctx.features)
        for p in ctx.hook_products:
            on = register and p in state.get("products", [])
            data, changes = install.plan_hooks(ctx.root, p, ctx.name, not on, features if on else None)
            if changes:
                path = ctx.root / install.CONFIGS[p]
                files.append({"rel": install.CONFIGS[p], "label": ctx.config(p),
                              "before": path.read_text(encoding="utf-8") if path.is_file() else None,
                              "after": install.config_text(data), "lines": changes})
        if register and state.get("products"):
            for p in ctx.targets:
                places += install.place(ctx.root, p, ctx.name, "link", False, True)
    if state.get("settings"):
        path = ctx.skill_dir / USER_REL
        before = path.read_text(encoding="utf-8") if path.is_file() else None
        after = settings_text(ctx, state.get("values", ctx.user_data))
        if after != before:
            files.append({"rel": ctx.shown(path), "before": before, "after": after, "whole": True, "settings": True})
    return files, places


def preview(ctx: Context, files: list[dict], places: list[str]) -> list[str]:
    t = ctx.t
    lines = [t["place"].format(change=c) for c in places]
    for f in files:
        lines += ["", t["file_new" if f["before"] is None else "file_change"].format(rel=f.get("label", f["rel"])), *f.get("lines", [])]
        if f.get("whole"):
            lines += [t["whole"], *f["after"].splitlines()]
            if f["before"] is None:
                continue
            lines.append(t["diff"])
        lines += difflib.unified_diff((f["before"] or "").splitlines(), f["after"].splitlines(),
                                      t["now_file"], t["after_file"], lineterm="", n=2)
    return lines or [t["nothing"]]


def git_ignored(root: Path, path: Path) -> bool | None:
    try:
        done = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(path)], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return {0: True, 1: False}.get(done.returncode)


def apply(ctx: Context, state: dict, files: list[dict], places: list[str]) -> int:
    """選んだものを書き、書いた後に検査する。問題があれば 1。"""
    t, problems = ctx.t, []
    if not files and not places:
        rt.emit(t["no_write"])
    if state.get("hooks"):
        register = state.get("register", False) and ctx.hooks_allowed and bool(state.get("products"))
        features = set(state.get("features") or ctx.features)
        for p in ctx.hook_products:
            on = register and p in state["products"]
            install.apply_hooks(ctx.root, p, ctx.name, not on, False, features if on else None)
        for p in ctx.targets if register else []:
            for change in install.place(ctx.root, p, ctx.name, "link", False, False):
                rt.emit(t["placed"].format(change=change))
        for f in files:
            if not f.get("settings"):
                rt.emit(t["written"].format(rel=f.get("label", f["rel"])))
        if register:
            found = install.check(ctx.root, ctx.targets, ctx.name, True, "link", features, state["products"])
        else:
            found = [t["left"].format(rel=ctx.config(p)) for p in ctx.hook_products
                     if install.registered(ctx.root, p, ctx.name) is not None]
        rt.emit(t["check"].format(n=len(found)))
        for problem in found:
            rt.emit(f"  {problem}")
        problems += found
        if register and any(f["rel"] == install.CONFIGS["claude"] for f in files):
            rt.emit(t["restart"])
        if register and "codex" in state["products"] and any(f["rel"] == install.CONFIGS["codex"] for f in files):
            rt.emit(t["trust"])
    for f in files:
        if not f.get("settings"):
            continue
        path = ctx.skill_dir / USER_REL
        if path.is_file():
            (ctx.skill_dir / rt.SETTINGS_BACKUP_REL).write_bytes(path.read_bytes())
            rt.emit(t["backup"].format(rel=ctx.shown(ctx.skill_dir / rt.SETTINGS_BACKUP_REL)))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f["after"], encoding="utf-8")
        rt.emit(t["written"].format(rel=f["rel"]))
        found = rt.check_settings(ctx.skill_dir)
        rt.emit(t["settings_check"].format(n=len(found)))
        for p in found:
            rt.emit(f"  {p}")
        problems += found
        if git_ignored(ctx.root, path) is False:
            rt.emit(t["git"].format(rel=f["rel"]))
    return 1 if problems else 0


# ---------------------------------------------------------------- 画面

def char_width(ch: str) -> int:
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def clip(text: str, width: int) -> str:
    out, used = [], 0
    for ch in text:
        used += char_width(ch)
        if used > width:
            break
        out.append(ch)
    return "".join(out)


def wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return [text]
    out, line, used = [], [], 0
    for ch in text:
        if used + char_width(ch) > width:
            out.append("".join(line))
            line, used = [], 0
        line.append(ch)
        used += char_width(ch)
    return out + ["".join(line)]


class PlainUI:
    """番号で選ぶ画面（curses が使えないとき、--plain のとき）。"""

    def __init__(self, t: dict):
        self.t = t

    def read(self, prompt: str) -> str:
        try:
            return input(prompt).strip()
        except EOFError:
            raise Cancel from None

    def head(self, title: str, lines: list[str]) -> None:
        print(f"\n== {title} ==")
        for line in lines:
            print(line)
        print()

    def pick(self, title: str, lines: list[str], options: list[str], cursor: int = 0, top: bool = False) -> int:
        rows = options if top else [*options, self.t["back"], self.t["cancel"]]
        while True:
            self.head(title, lines)
            for i, row in enumerate(rows, 1):
                print(f"  {i}. {row}")
            answer = self.read(self.t["plain_pick"])
            index = int(answer) - 1 if answer.isdigit() else -1
            if answer == "b" or (not top and index == len(options)):
                raise Back
            if answer == "q" or (not top and index == len(options) + 1):
                raise Cancel
            if 0 <= index < len(options):
                return index
            print(self.t["plain_bad"])

    def pick_many(self, title: str, lines: list[str], options: list[str], chosen: set[int],
                  extras: list[str] | None = None) -> tuple[str, object]:
        extras, chosen = extras or [], set(chosen)
        rows = [*options, self.t["done"], *extras, self.t["back"], self.t["cancel"]]
        while True:
            self.head(title, lines)
            for i, row in enumerate(rows, 1):
                mark = ("[x] " if i - 1 in chosen else "[ ] ") if i <= len(options) else ""
                print(f"  {i}. {mark}{row}")
            answer = self.read(self.t["plain_many"].format(done=self.t["done"]))
            index = int(answer) - 1 if answer.isdigit() else -1
            if answer == "b" or index == len(rows) - 2:
                raise Back
            if answer == "q" or index == len(rows) - 1:
                raise Cancel
            if 0 <= index < len(options):
                chosen ^= {index}
            elif index == len(options):
                if chosen:
                    return "done", chosen
                print(self.t["need_one"])
            elif len(options) < index < len(options) + 1 + len(extras):
                return "extra", index - len(options) - 1
            else:
                print(self.t["plain_bad"])

    def ask(self, title: str, lines: list[str], prompt: str, check) -> str:
        self.head(title, lines)
        print(prompt)
        while True:
            answer = self.read(self.t["plain_text"])
            if not answer:
                raise Back
            if answer == ":q":
                raise Cancel
            why = check(answer)
            if not why:
                return answer
            print(why)


class CursesUI:
    """矢印キーとスペースで選ぶ画面。"""

    def __init__(self, scr, t: dict):
        import curses
        self.c, self.scr, self.t, self.note, self.shown = curses, scr, t, "", None
        scr.keypad(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.colors = False
        if curses.has_colors():
            try:
                curses.use_default_colors()
                for pair, color in enumerate((curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_CYAN, curses.COLOR_YELLOW), 1):
                    curses.init_pair(pair, color, -1)
                self.colors = True
            except curses.error:
                pass

    def put(self, y: int, x: int, text: str, attr: int = 0) -> None:
        h, w = self.scr.getmaxyx()
        if 0 <= y < h and x < w:
            try:
                self.scr.addstr(y, x, clip(text, w - x - (1 if y == h - 1 else 0)), attr)
            except self.c.error:
                pass

    def tone(self, line: str) -> int:
        """差分と注意の行の色。"""
        if not self.colors:
            return 0
        for head, pair in (("+++", 0), ("---", 0), ("-- ", 0), ("+", 1), ("-", 2), ("@@", 3), ("==", 3), ("注意", 4), ("Note:", 4)):
            if line.startswith(head):
                return self.c.color_pair(pair) if pair else self.c.A_BOLD
        return 0

    def frame(self, title: str, lines: list[str], top: int, room: int) -> tuple[list[str], int, int]:
        """題と説明を描き、説明の折り返した行の数、描いた先頭の位置、描いた行の数を返す。"""
        h, w = self.scr.getmaxyx()
        body = [(part, self.tone(line)) for line in lines for part in wrap(line, w - 2)]  # 折り返しても元の行の色
        top = max(0, min(top, len(body) - room))
        if (title, lines) != self.shown:  # 別の画面に移るときは、差分の更新に頼らず全体を描き直す
            self.scr.clear()
            self.shown = (title, list(lines))
        else:
            self.scr.erase()
        self.put(0, 0, title, self.c.A_BOLD)
        shown = body[top:top + room]
        for i, (line, attr) in enumerate(shown):
            self.put(1 + i, 1, line, attr)
        return body, top, len(shown)

    def choose(self, title: str, lines: list[str], rows: list[str], cursor: int = 0, toggles: int = 0,
               chosen: set[int] | None = None, quiet: int = 0) -> int:
        """rows の1つを Enter で選ぶ。先頭の toggles 個は Space か Enter で chosen に入れ外しする。後ろの quiet 個は薄く出す。"""
        c, top, cursor = self.c, 0, max(0, min(cursor, len(rows) - 1))
        while True:
            h, w = self.scr.getmaxyx()
            if h < 8 or w < 30:
                self.scr.erase()
                self.put(0, 0, self.t["small"])
                key = self.scr.getch()
                if key in (ord("q"), 27):
                    raise Cancel
                continue
            avail = h - 3
            body_len = sum(len(wrap(line, w - 2)) for line in lines)
            rows_h = min(len(rows), avail, max(min(len(rows), 6), avail - body_len))
            room = max(0, avail - rows_h)
            body, top, drawn = self.frame(title, lines, top, room)
            first = max(0, min(cursor - rows_h + 1, len(rows) - rows_h)) if cursor >= rows_h else 0
            for i, row in enumerate(rows[first:first + rows_h]):
                index = first + i
                mark = ("[x] " if index in (chosen or set()) else "[ ] ") if index < toggles else ""
                attr = c.A_REVERSE if index == cursor else (c.A_DIM if index >= len(rows) - quiet else 0)
                self.put(drawn + 2 + i, 1, f"{'>' if index == cursor else ' '} {mark}{row}", attr)
            help_line = self.note or self.t["keys"] + (self.t["keys_scroll"].format(at=top + 1, total=len(body))
                                                        if len(body) > room else "")
            self.put(h - 1, 0, help_line, c.A_BOLD if self.note else c.A_DIM)
            self.note = ""
            key = self.scr.getch()
            if key in (c.KEY_UP, ord("k")):
                cursor = max(0, cursor - 1)
            elif key in (c.KEY_DOWN, ord("j")):
                cursor = min(len(rows) - 1, cursor + 1)
            elif key == c.KEY_NPAGE:
                top += max(1, room - 1)
            elif key == c.KEY_PPAGE:
                top = max(0, top - max(1, room - 1))
            elif key == ord(" ") and cursor < toggles:
                chosen ^= {cursor}
            elif key in (10, 13, c.KEY_ENTER):
                if cursor < toggles:
                    chosen ^= {cursor}
                else:
                    return cursor
            elif key in (ord("b"), c.KEY_LEFT, c.KEY_BACKSPACE, 127, 8):
                raise Back
            elif key in (ord("q"), 27):
                raise Cancel

    def pick(self, title: str, lines: list[str], options: list[str], cursor: int = 0, top: bool = False) -> int:
        if top:
            return self.choose(title, lines, options, cursor)
        index = self.choose(title, lines, [*options, self.t["back"], self.t["cancel"]], cursor, quiet=2)
        if index == len(options):
            raise Back
        if index == len(options) + 1:
            raise Cancel
        return index

    def pick_many(self, title: str, lines: list[str], options: list[str], chosen: set[int],
                  extras: list[str] | None = None) -> tuple[str, object]:
        extras, chosen = extras or [], set(chosen)
        rows = [*options, self.t["done"], *extras, self.t["back"], self.t["cancel"]]
        cursor = len(options)
        while True:
            cursor = self.choose(title, lines, rows, cursor, len(options), chosen, quiet=2)
            if cursor == len(rows) - 2:
                raise Back
            if cursor == len(rows) - 1:
                raise Cancel
            if cursor > len(options):
                return "extra", cursor - len(options) - 1
            if chosen:
                return "done", chosen
            self.note = self.t["need_one"]

    def ask(self, title: str, lines: list[str], prompt: str, check) -> str:
        c, text, why = self.c, "", ""
        try:
            c.curs_set(1)
        except c.error:
            pass
        try:
            while True:
                h, w = self.scr.getmaxyx()
                _, _, drawn = self.frame(title, [*lines, "", prompt], 0, max(0, h - 5))
                y = drawn + 2
                self.put(y + 1, 1, why, c.A_BOLD)
                self.put(h - 1, 0, self.t["keys_text"], c.A_DIM)
                self.put(y, 1, "> " + text)
                key = self.scr.get_wch()
                if key in ("\n", "\r") or key == c.KEY_ENTER:
                    if not text.strip():
                        raise Back
                    why = check(text) or ""
                    if not why:
                        return text
                elif key == "\x1b":
                    raise Cancel
                elif key in ("\x7f", "\b") or key == c.KEY_BACKSPACE:
                    text = text[:-1]
                elif isinstance(key, str) and key.isprintable():
                    text += key
        finally:
            try:
                c.curs_set(0)
            except c.error:
                pass


# ---------------------------------------------------------------- 手順

def step_products(ui, ctx: Context, state: dict) -> None:
    t, current = ctx.t, {p: install.registered(ctx.root, p, ctx.name) for p in ctx.hook_products}
    lines = [t["products_info"], *[f"{t['product_name'][p]}: {t['now'].format(state=registered_text(t, current[p]))}"
                                   for p in ctx.hook_products]]
    left = [t["product_name"][p] for p in ctx.targets if p not in ctx.hook_products]
    lines += [t["unhooked"].format(products=t["list_sep"].join(left))] if left else []
    lines += [t["plugin_on"].format(where=t["list_sep"].join(plugins_on(ctx)))] if plugins_on(ctx) else []
    chosen = state.get("products") or [p for p in ctx.hook_products if current[p] is not None] or ctx.hook_products
    _, picked = ui.pick_many(t["products"], lines, [t["product"].format(name=t["product_name"][p], where=ctx.config(p)) for p in ctx.hook_products],
                             {ctx.hook_products.index(p) for p in chosen})
    state["products"] = [ctx.hook_products[i] for i in sorted(picked)]


def step_features(ui, ctx: Context, state: dict) -> None:
    t = ctx.t
    now = set().union(*[install.registered(ctx.root, p, ctx.name) or set() for p in ctx.hook_products])
    chosen = set(state.get("features") or (now & set(ctx.features)) or ctx.features)
    lines = [] if "feedback" in ctx.features else [t["nofeedback"]]
    _, picked = ui.pick_many(t["features"], lines, [t["feature"][f] for f in ctx.features],
                             {ctx.features.index(f) for f in chosen})
    state["features"] = {ctx.features[i] for i in picked}


def step_dest(ui, ctx: Context, state: dict) -> None:
    t = ctx.t
    names = t["list_sep"].join(t["product_name"][p] for p in state.get("products", []))
    features = t["sep"].join(t["feature_name"][f] for f in ctx.features if f in (state.get("features") or ctx.features))
    lines = [t["chosen"].format(products=names, features=features)]
    lines += [t["plugin_on"].format(where=t["list_sep"].join(plugins_on(ctx)))] if plugins_on(ctx) else []
    index = ui.pick(t["dest"], lines, ctx.dest_items(), 0 if state.get("register", True) else 1)
    state["register"] = index == 0


def step_nohooks(ui, ctx: Context, state: dict) -> None:
    t = ctx.t
    lines = [t["nohooks"], *[f"{t['product_name'][p]}: {t['now'].format(state=registered_text(t, install.registered(ctx.root, p, ctx.name)))}"
                             for p in ctx.hook_products]]
    ui.pick(t["dest"], lines, ctx.dest_items()[1:])
    state["register"] = False


def edit_item(ui, ctx: Context, values: dict, item: dict) -> None:
    t, path = ctx.t, item["path"]
    dotted, (how, choices) = ".".join(path), how_to_pick(item)
    now, source = effective(ctx, values, item)
    skill_value = dig(ctx.skill_data, path)
    keep = t["keep"].format(value=show(skill_value)) if skill_value is not None else t["keep_none"]
    lines = [item["label"], t["item_now"].format(value=show(now), source=source)]
    title = t["item"].format(path=dotted)
    kind = (item.get("input") or item["def"]).get("type", "string")

    def typed() -> None:
        answer = ui.ask(title, lines, t["ask"].format(path=dotted, range=t["range"].get(kind, kind)), lambda text: _why(item, text))
        put(values, path, parse_value(item, answer))

    if how == "many":
        chosen = {i for i, c in enumerate(choices) if isinstance(now, list) and c in now}
        result, picked = ui.pick_many(title, lines, [show(c) for c in choices], chosen, [keep])
        put(values, path, None if result == "extra" else [choices[i] for i in sorted(picked)])
        return
    free = how == "type" or kind == "text"
    options = [show(c) + (t["current"] if c == now else "") for c in choices] + ([t["other"]] if free else []) + [keep]
    index = ui.pick(title, lines, options, choices.index(now) if now in choices else 0)
    if index < len(choices):
        put(values, path, choices[index])
    elif free and index == len(choices):
        typed()
    else:
        put(values, path, None)


def _why(item: dict, text: str) -> str | None:
    try:
        parse_value(item, text)
    except ValueError as exc:
        return str(exc)
    return None


def step_settings(ui, ctx: Context, state: dict) -> None:
    t = ctx.t
    values = state.setdefault("values", copy.deepcopy(ctx.user_data))
    items, cursor = setting_items(ctx), 0
    lines = [*ctx.notes, *[line.format(skill=SKILL_REL) for line in t["settings_info"]]]
    while True:
        rows = []
        for item in items:
            value, source = effective(ctx, values, item)
            mark = "＊" if dig(values, item["path"]) != dig(ctx.user_data, item["path"]) else "  "
            rows.append(f"{mark}{'.'.join(item['path'])} = {show(value)}（{source}）")
        cursor = ui.pick(t["settings"].format(user=USER_REL), lines, [*rows, t["settings_next"]], cursor)
        if cursor == len(items):
            return
        try:
            edit_item(ui, ctx, values, items[cursor])
        except Back:
            continue


def step_confirm(ui, ctx: Context, state: dict) -> None:
    t = ctx.t
    files, places = planned(ctx, state)
    if not files and not places:
        ui.pick(t["confirm"], [t["nothing"]], [t["finish"]])
        return
    ui.pick(t["confirm"], [t["confirm_info"], *preview(ctx, files, places)], [t["write"]])


def run_steps(ui, ctx: Context, state: dict, steps: list) -> bool:
    """手順を順に行う。「戻る」で1つ前の手順に戻り、最初の手順で戻るとメニューに戻る（False）。"""
    i, step = 0, 1
    while 0 <= i < len(steps):
        fn, when = steps[i]
        if when is None or when(ctx, state):
            try:
                fn(ui, ctx, state)
                step = 1
            except Back:
                step = -1
        i += step
    return i >= len(steps)


def flow(ui, ctx: Context) -> dict | None:
    """メニューから選んだことを行い、書くもの（state）を返す。何も書かずに終えるなら None。"""
    t, cursor = ctx.t, 0
    intro = [line.format(user=USER_REL) for line in t["intro"]] + ctx.notes
    while True:
        try:
            cursor = ui.pick(t["title"].format(name=ctx.name), intro, t["menu"], cursor, top=True)  # 最初の画面は「終わる」で抜ける
        except Back:
            return None
        if cursor == 4:
            return None
        if cursor == 3:
            try:
                ui.pick(t["status"], status_lines(ctx), [])
            except Back:
                pass
            continue
        state = {"hooks": cursor in (0, 2), "settings": cursor in (1, 2)}
        steps = []
        if state["hooks"]:
            steps += ([(step_products, None), (step_features, lambda c, s: len(c.features) > 1), (step_dest, None)]
                      if ctx.hooks_allowed else [(step_nohooks, None)])
        steps += [(step_settings, None)] if state["settings"] else []
        if run_steps(ui, ctx, state, steps + [(step_confirm, None)]):
            return state


def interactive(ctx: Context, plain: bool) -> dict | None:
    if not plain:
        try:
            import curses
        except ImportError:
            curses = None
        if curses is not None:
            os.environ.setdefault("ESCDELAY", "25")
            try:
                locale.setlocale(locale.LC_ALL, "")  # 日本語などを端末の文字コードで出すため
            except locale.Error:
                pass
            try:
                curses.setupterm()  # 端末の種類が分からなければ、ここで curses.error になる
                return curses.wrapper(lambda scr: flow(CursesUI(scr, ctx.t), ctx))
            except curses.error:
                pass  # 番号で選ぶ画面にする
    return flow(PlainUI(ctx.t), ctx)


# ---------------------------------------------------------------- 非対話

def split(text: str) -> list[str]:
    return [v.strip() for v in re.split(r"[,、，]", text) if v.strip()]


def args_state(ctx: Context, args) -> dict:
    """引数で選んだもの。画面で選んだときと同じ形にする。"""
    t, state = ctx.t, {}
    if args.features and not args.hooks:
        raise UsageError(t["features_alone"])
    if args.hooks:
        state["hooks"] = True
        if args.hooks.strip() == "none":
            state["register"] = False
        else:
            if not ctx.hooks_allowed:
                raise UsageError(t["nohooks"])
            products, features = split(args.hooks), split(args.features) if args.features else ctx.features
            bad = [p for p in products if p not in ctx.hook_products]
            if bad or not products:
                raise UsageError(t["unknown_products"].format(bad=bad, ok=", ".join(ctx.hook_products)))
            bad = [f for f in features if f not in ctx.features]
            if bad or not features:
                raise UsageError(t["unknown_features"].format(bad=bad, ok=", ".join(ctx.features)))
            state.update(register=True, products=[p for p in ctx.hook_products if p in products], features=set(features))
    if args.set:
        values, index = copy.deepcopy(ctx.user_data), {".".join(i["path"]): i for i in setting_items(ctx)}
        for given in args.set:
            key, sep, raw = given.partition("=")
            if not sep:
                raise UsageError(t["no_eq"].format(item=given))
            item = index.get(key.strip())
            if item is None:
                raise UsageError(t["unknown_path"].format(path=key.strip(), paths=", ".join(index)))
            try:
                put(values, item["path"], parse_value(item, raw))
            except ValueError as exc:
                raise UsageError(f"{key.strip()}: {exc}") from None
        state.update(settings=True, values=values)
    return state


def no_tty(ctx: Context) -> int:
    t = ctx.t
    script = ctx.shown(Path(__file__).resolve())
    item = next((i for i in setting_items(ctx) if how_to_pick(i)[0] == "one" and how_to_pick(i)[1]), None)
    rt.emit(t["no_tty"], sys.stderr)
    rt.emit(t["no_tty_args"], sys.stderr)
    where = "--scope user" if ctx.user else "--project ."
    examples = [f"python3 {script} {where} --status"]
    if ctx.hooks_allowed and ctx.hook_products:
        examples.append(f"python3 {script} {where} --hooks {','.join(ctx.hook_products)} --features {','.join(ctx.features)} --yes")
    if item:
        examples.append(f"python3 {script} {where} --set {'.'.join(item['path'])}={show(how_to_pick(item)[1][0])} --yes")
    for line in examples:
        rt.emit(f"  {line}", sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="プロジェクトのルート。ホーム（~）ならユーザー単位。省くと、本体がホームのスキルの置き場に"
                                          "あればユーザー単位、ほかは今のディレクトリから .git を辿って決める")
    parser.add_argument("--scope", choices=["project", "user"],
                        help="user はホームに登録する（どのプロジェクトからでも使う）。project は --project か今のプロジェクト")
    parser.add_argument("--plain", action="store_true", help="矢印キーの画面ではなく、番号で選ぶ画面にする")
    parser.add_argument("--status", action="store_true", help="今の状態を見る（何も書かない）")
    parser.add_argument("--hooks", help="非対話: hooks を登録する製品（カンマ区切り）。none なら今の登録を外す")
    parser.add_argument("--features", help="非対話: 登録する機能（check、feedback）。既定は使える機能すべて")
    parser.add_argument("--set", action="append", metavar="項目=値", help="非対話: ユーザーの設定の値（例 inputs.measure=run。null で値なし）")
    parser.add_argument("--yes", action="store_true", help="非対話: 確かめずに書く。無ければ書く前の差分を見せるだけ")
    args = parser.parse_args()

    ctx = Context(install.default_root(args.project, __file__, args.scope))
    t = ctx.t
    if args.status:
        for line in status_lines(ctx):
            rt.emit(line)
        return 0
    if args.hooks or args.features or args.set:
        try:
            state = args_state(ctx, args)
        except UsageError as exc:
            rt.emit(t["args_error"].format(why=exc), sys.stderr)
            return 2
        files, places = planned(ctx, state)
        for line in preview(ctx, files, places):
            rt.emit(line)
        if not args.yes:
            if files or places:
                rt.emit(t["yes_hint"])
            return 0
        return apply(ctx, state, files, places)
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return no_tty(ctx)
    try:
        state = interactive(ctx, args.plain)
    except (Cancel, KeyboardInterrupt):
        rt.emit(t["cancelled"])
        return 0
    if state is None:
        rt.emit(t["finished"])
        return 0
    files, places = planned(ctx, state)
    return apply(ctx, state, files, places)


if __name__ == "__main__":
    sys.exit(main())
