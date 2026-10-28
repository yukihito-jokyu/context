#!/usr/bin/env python3
"""プロジェクトのスキルのカタログ（一覧の HTML と、スキルごとの HTML）を書き、「## カタログ」の節（Markdown）を標準出力に出す（RPT-02）。

一覧（既定 .skill-runs/catalog.html）には、スキルごとの状態の印と「先に見るもの」の件数、ページへのリンクを載せる。
skill-foundation で作ったスキル（dev/spec.json がある）ごとのページ（一覧の隣の catalog/<名前>.html）には、SKILL.md の
「2. 手順」と契約から作ったワークフロー図に、独立検証の記録を重ねて載せる。内容はすべてファイルから集計し、AI が図を描く
余地を残さない。ページの上に見出しの数字と「先に見るもの」を置き、下の記録はタブ（ワークフロー、エージェントの動き、
収束テスト、ルールと出力の決まり、検査が働くか、最後の実行）で切り替える。同じ名前のスキルが2つの置き場にあれば、2つ目からは
置き場のパスをページの名前にする。前に書いたページで、今は無いスキルのものは消す（このスクリプトが書いた印のあるものだけ）。
書体は Google Fonts（DotGothic16・JetBrains Mono）から読み、読めないときは端末の等幅の書体で描く。

見せ方の約束（ユーザーの指摘から決めた恒久の決まり。selftest.py の check_catalog が確かめる）:
  1. 言葉     作る側だけに通じる呼び名や、読んですぐ意味が通らない語をそのまま見せない。見せる用語は TERMS の表から
              出し、term() で、重ねると説明が出るようにする。selftest.py の BANNED_WORDS の語を、このファイルの文字列
              （説明文とコメントは除く）と、カタログに載る skill-foundation の文書に書かない
  2. 動き     クリックで点が弾ける（続けて押すと数が増え、まれに輪になる）。タブ・ラウンド・凡例の切り替えは弾むように
              動く。動きには遊びを入れ、prefers-reduced-motion では動かさない
  3. 行き先   「先に見るもの」のリンクは、タブの先頭ではなく、対象の行・操作・カードへ飛び（anchor() の id）、
              囲むタブ・ラウンド・畳んだ欄を開いて点滅させる。ページ内のリンクは、すべてページにある id を指す
  4. グラフ   系列（収束テストの課題、エージェントの動きのエージェント）は凡例から浮かび上がらせ、ほかを薄くする
  5. モデル   エージェントのモデルと推論エフォートを、Claude Code・Codex のどちらでも見せる。記録に無ければ
              「記録なし」、codex exec のようにコマンドや設定から読んだものは「設定から」と書く
  6. 推定     エージェントの各操作の理由と流れの評価は、AI が記録から推し量ったもの（analysis.json）を、「AI の推定」の
              用語を付けて推定と分かるように見せ、機械が数えた事実（手順との照合）と並べる。AI の文の「#番号」は、
              その操作の行へのリンクにする。今の記録を読んだ分析でなければ出さず、そのことを書く

  先に見るもの     違反の検出・hooks の動作・改変チェックの失敗、収束テストで結果が揃わない課題、作業ディレクトリの
                   外に触れた操作、失敗した操作を、重さの順に、対象の行や操作へのリンクを付けて並べる
  ワークフロー図「2. 手順」の番号の行（フェーズ、コマンド、ルールID、終了コードの分岐、「手順Nに戻る」とそのわけ
                   （終了コードの意味はコマンドのスクリプトの説明の「終了コード:」の行から）、
                   「〜なら…終える」の途中の終了、「エラーを0件にする」「すべて成功させ」「指摘があれば…直す」などの
                   通るまでの繰り返し、文の頭の「〜なら、」の条件）、契約の入力・出力・report.sections、hooks の有無
  図に重ねる検証   ルールID ごとの probe.py の成否、収束テストの最後のラウンドで変わったファイルを手順の本文の
                   パスで割り当てた揃い方、チェックポイント（run.py start・check・finish）を独立エージェントが通った回数、
                   最後のラウンドでエージェントが前の手順に戻ったところと人数、記録の操作から読めるそのわけ
  ルールと出力       dev/spec.json の decisions、assets/contract.json の outputs
  独立検証         dev/results/probe-results.json、dev/results/convergence/round-*/report.json と review.json、
                   dev/convergence-report.md の「結論」
  エージェントの動き  round-*/traces.json（convergence.py diff・trace が書く）。エージェントごとに、操作を手順に
                   割り当てて時間の流れで描き、操作の内訳、手順の順、失敗した操作、作業ディレクトリの外に触れた操作、
                   操作の一覧、最終の返答を載せる。印に重ねると、その操作の全文と結果を出す。課題の依頼文の下に、
                   作業ディレクトリの外に触れた操作の場所・原因と、独立しているか・測定にもれがないかの判断（決まりは
                   カードに書く）を載せる。fence.py が止めた操作（traces.json の fenced）は、外に触れた操作に数えず、
                   カードに別に載せる。表にはエージェントごとのモデルと推論エフォート（traces.json の model・effort）を載せる
  最後の実行       .skill-runs/<名前>/state.json の記録
  ほかのスキル     dev/spec.json の無いスキルは、一覧に SKILL.md の name と description だけを載せる

run.py finish が契約の report.sections（stage: finish）から呼ぶ。スキルを直した後や収束テストの後に、単独でも
実行できる。読めないスキルがあってもカタログは書き、一覧の「読めなかったスキル」に理由を出す。

終了コード: 0 書いた、1 書けなかった、2 引数の誤り

使い方:
  python3 catalog.py --project <プロジェクトのルート> [--out <一覧の HTML のパス>] [--skill <スキルのディレクトリ> ...]
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
import report_skill  # noqa: E402

PLACES = (".claude/skills", ".agents/skills")
GATES = ("start", "check", "finish")
GROUP = {"runtime": "machine", "format": "machine", "validate": "machine", "script": "tool", "template": "tool",
         "review": "human", "doc": "human"}
METRICS = [("files", "作った・変えたファイルの集合"), ("structure", "共通のファイルの骨格"), ("names", "新しく作った名前")]

ITEM = re.compile(r"^(\d+)\.\s+(.*)$")
PHASE = re.compile(r"^(フェーズ\s*\d+（[^）]*）|Phase\s+\d+\s*\([^)]*\))\s*[:：]\s*")
CODE = re.compile(r"`([^`]+)`")
PLACEHOLDER = re.compile(r"(<[^<>]+>|\{[^{}]+\})")
IDS_IN_PARENS = re.compile(r"\s*[（(](?:[A-Z]{2,5}-\d{2}[、,\s]*)+[）)]")
BACK = [re.compile(r"(?:終了コード\s*(\d+)\s*なら[、,]?\s*)?手順\s*(\d+)\s*に戻る"),
        re.compile(r"(?:(?:[Ii]f (?:the )?exit code is|[Oo]n exit code) (\d+),?\s*)?(?:go back|return) to step (\d+)")]
BRANCH = [re.compile(r"終了コード\s*(\d+)\s*なら[、,]?\s*(.+?)(?=、?終了コード\s*\d+\s*なら|。|$)"),
          re.compile(r"(?:[Ii]f (?:the )?exit code is|[Oo]n exit code) (\d+),?\s*(.+?)(?=[.;]|$)")]
CODE_LEAD = re.compile(r"終了コード\s*\d|(?:[Ii]f (?:the )?|[Oo]n )exit code")
# 手順の文を、文の頭の条件で分ける。途中で終える文、直して繰り返す文、条件で作業が変わる文の順に当てる
EXITS = [re.compile(r"^[^、。]*?(?:なら|れば|たら)[、,]?.*終える$"), re.compile(r"^[Ii]f [^,]+,.*\b(?:stop|end)\b")]
FIXES = [re.compile(r"^(?:失敗したら|指摘があれば).*直す"),
         re.compile(r"^(?:[Ff]or each finding|[Ii]f there are findings|[Ii]f (?:it|this|any \w+) fails?)\b.*\bfix")]
CONDS = [re.compile(r"^[^、。]*?(?:なら|れば|たら)、"), re.compile(r"^[Ii]f [^,]+, ")]
# 通るまで繰り返す書き方。(正規表現, コマンドがあるときの文, 無いときの文)。コマンドは直前の `〜.py`
LOOPS = [(re.compile(r"(?:([\w.-]+\.py)\b[^、。]*?の\s*)?エラーを\s*0\s*件に|(?:([\w.-]+\.py)\b[^,.;]*?)?\b(?:0|zero) errors"),
          "{} のエラーが 0 件になるまで", "エラーが 0 件になるまで"),
         (re.compile(r"(?:([\w.-]+\.py)\b[^、。]*?を\s*)?すべて成功させ|(?:([\w.-]+\.py)\b[^,.;]*?)?\buntil (?:they |it )?all pass"),
          "{} がすべて成功するまで", "すべて成功するまで"),
         (re.compile(r"次のラウンド|\bnext round\b"), "", "次のラウンドを決めて繰り返す")]
RETRY = re.compile(r"やり直す|\b(?:rerun|retry|run (?:it )?again)\b")
EXIT_DOC = re.compile(r"^(?:終了コード|Exit codes?)\s*[:：]\s*(.+)$", re.M)
SKILL_REL = re.compile(r"^(?:.*/)?\.(?:claude|agents)/skills/[^/]+/")
TOKEN = re.compile(r"\d+(?:人|件|回|通り)|[A-Za-z0-9_./<>{}:=@#$%+\-]+|\s+|.")  # 数と助数詞は行で分けない
CLOSERS = set("）」』】〕、。，．,.:;!?)]")
OPENERS = set("（「『【〔([")


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rel_to(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


# ---------------------------------------------------------------- 手順を読む

def short_command(code: str) -> str | None:
    """`python3 <skill>/scripts/run.py start --set ...` を `run.py start` の形にする。パスや値を取る引数は出さない。"""
    tokens = code.split()
    for i, tok in enumerate(tokens):
        match = re.search(r"([A-Za-z0-9_]+\.py)$", tok)
        if not match:
            continue
        parts, rest = [match.group(1)], tokens[i + 1:]
        if rest and re.fullmatch(r"[a-z][a-z-]*", rest[0]):
            parts.append(rest.pop(0))
        flags = 0
        for j, t in enumerate(rest):
            if not t.startswith("--") or flags == 2:
                continue
            value = rest[j + 1] if j + 1 < len(rest) else ""
            if value and not value.startswith("--") and not value.isdigit():
                continue
            parts.append(f"{t} {value}" if value.isdigit() else t)
            flags += 1
        return " ".join(parts)
    return None


def plain(text: str) -> str:
    """図に出す文。コマンドは短い形にし、リンクとルールID の括弧を除く。"""
    text = CODE.sub(lambda m: short_command(m.group(1)) or m.group(1), text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", IDS_IN_PARENS.sub("", text)).strip()


def sentences(text: str) -> list[str]:
    return [p.strip().rstrip("。") for p in re.split(r"(?<=。)|(?<=[a-z)]\.)\s+(?=[A-Z])", text) if p and p.strip()]


def path_patterns(raw: str) -> list[tuple[re.Pattern, int]]:
    """手順の本文に書かれたパス（`<base>/<name>/dev/spec.json` の形）を、変わったファイルに当てる正規表現にする。
    スキル自身のファイル（`<skill>/...`）とコマンドは除く。2つ目の値は、一番長く一致した手順を選ぶための字数。"""
    found = []
    for tok in (c.strip() for c in CODE.findall(raw)):
        if " " in tok or tok.startswith(("<skill", "{skill", "-")) or ("/" not in tok and not re.search(r"\.[a-z]{1,5}$", tok)):
            continue
        if (tok.endswith(".py") and "/" not in tok) or len(re.sub(r"[/.]", "", PLACEHOLDER.sub("", tok))) < 2:
            continue  # スクリプトの名前と、`<base>/<name>/` のように何にでも当たるパスは使わない
        rx = "".join(".+?" if PLACEHOLDER.fullmatch(p) else re.escape(p) for p in PLACEHOLDER.split(tok) if p)
        found.append((re.compile(r"(?:^|/)" + rx + (".*" if tok.endswith("/") else "") + "$"), len(PLACEHOLDER.sub("", tok))))
    return found


def describe(no: int, raw: str) -> dict:
    match = PHASE.match(raw)
    phase = match.group(1) if match else ""
    said = sentences(plain(raw[match.end():] if match else raw))
    title = phase or (said[0] if said else "")
    rest = [x for x in (said if phase else said[1:]) if not CODE_LEAD.match(x)]  # 終了コードの文は backs と branches で描く
    exits = [x for x in rest if any(rx.match(x) for rx in EXITS)]
    fixes = [x for x in rest if x not in exits and any(rx.match(x) for rx in FIXES)]
    conds = [x for x in rest if x not in exits + fixes and any(rx.match(x) for rx in CONDS)]
    detail = next((x for x in rest if x not in exits + fixes + conds), "")
    commands = list(dict.fromkeys(c for c in (short_command(code) for code in CODE.findall(raw)) if c))
    backs, branches = [], []
    for rx in BACK:  # cmd は戻る文の前の最後のコマンド（終了コードの意味を引く）、case は終了コードの無い戻りの文の頭
        for m in rx.finditer(raw):
            before = raw[:m.start()]
            cmd = next((c for c in reversed([short_command(x) for x in CODE.findall(before)]) if c), "")
            case = "" if m.group(1) else plain(re.split(r"。|\.\s", before)[-1]).rstrip("、, ")
            backs.append({"to": int(m.group(2)), "code": m.group(1) or "", "cmd": cmd, "case": case,
                          "label": f"終了コード{m.group(1)}" if m.group(1) else "戻る"})
    for rx in BRANCH:
        branches += [(m.group(1), plain(m.group(2))) for m in rx.finditer(raw) if not any(b.search(m.group(2)) for b in BACK)]
    found = []  # (文の順, 文の中の位置, 繰り返しの文)
    for i, x in enumerate(said):
        for rx, with_cmd, bare in LOOPS:
            for m in rx.finditer(x):
                cmd = next((g for g in m.groups() if g), None)
                found.append((i, m.start(), with_cmd.format(cmd) if cmd and with_cmd else bare))
        if x in fixes:
            found.append((i, 0, x.rstrip(".")))
    loops = [f"終了コード {code}: {action}" for code, action in branches if RETRY.search(action)]
    loops = list(dict.fromkeys(loops + [label for _, _, label in sorted(found)]))
    return {"no": no, "raw": raw, "phase": phase, "title": title, "detail": detail, "commands": commands,
            "ids": list(dict.fromkeys(_lib.ID_IN_TEXT.findall(raw))), "gates": [g for g in GATES if f"run.py {g}" in commands],
            "backs": backs, "branches": [(c, a) for c, a in branches if not RETRY.search(a)], "fixes": fixes,
            "turns": [("exit" if x in exits else "cond", x) for x in rest if x in exits + conds], "loops": loops, "patterns": path_patterns(raw)}


def parse_steps(text: str) -> list[dict]:
    body = _lib.section(text, "2. 手順") or _lib.section(text, "2. Procedure")
    items: list[list] = []
    for line in body.splitlines():
        match = ITEM.match(line)
        if match:
            items.append([int(match.group(1)), match.group(2).strip()])
        elif items and line[:1] in (" ", "\t") and line.strip():
            items[-1][1] += " " + line.strip()
    return [describe(no, raw) for no, raw in items]


# ---------------------------------------------------------------- 検証の記録を読む

def load_rounds(skill_dir: Path) -> list[dict]:
    found = []
    for path in (skill_dir / "dev/results/convergence").glob("round-*/report.json"):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        match = re.fullmatch(r"round-(\d+)", path.parent.name)
        data.setdefault("round", int(match.group(1)) if match else 0)
        review = read_json(path.parent / "review.json")
        if isinstance(review, dict):
            data["review"] = review
        traces = read_json(path.parent / "traces.json")
        if isinstance(traces, dict) and isinstance(traces.get("runs"), dict):
            data["traces"] = traces
        analysis = read_json(path.parent / "analysis.json")
        if isinstance(analysis, dict) and isinstance(analysis.get("runs"), dict):
            data["analysis"] = analysis["runs"]
        found.append(data)
    return sorted(found, key=lambda d: d.get("round", 0))


def rule_checks(probes: dict | None, rounds: list[dict]) -> dict:
    """ルールID ごとの probe の成否と、最後のラウンドのレビューの検出率。"""
    result: dict = {}
    for item in (probes or {}).get("results", []):
        entry = result.setdefault(item.get("rule", ""), {"passed": 0, "total": 0, "review": None})
        entry["total"] += 1
        entry["passed"] += bool(item.get("passed"))
    samples = rounds[-1].get("review", {}).get("samples", []) if rounds else []
    for sample in samples:
        entry = result.setdefault(sample.get("rule", ""), {"passed": 0, "total": 0, "review": None})
        rates = [entry["review"]] if entry["review"] is not None else []
        entry["review"] = min(rates + [float(sample.get("rate", 0))])
    return result


def assign_files(steps: list[dict], report: dict | None) -> tuple[dict, dict]:
    """最後のラウンドで変わったファイルを、本文のパスが一番長く一致した手順に割り当て、全員が作ったか一部だけかを数える。"""
    per_step = {s["no"]: Counter() for s in steps}
    unmatched: Counter = Counter()
    for task in (report or {}).get("tasks", []):
        agents, changed = task.get("agents", []), task.get("changed_files", {})
        if not agents or not any(changed.get(a) for a in agents):
            continue
        for rel in sorted(set().union(*(set(changed.get(a, [])) for a in agents))):
            best = None
            for step in steps:
                for rx, size in step["patterns"]:
                    if rx.search(rel) and (best is None or size > best[0]):
                        best = (size, step["no"])
            bucket = per_step[best[1]] if best else unmatched
            bucket["files"] += 1
            bucket["all" if all(rel in changed.get(a, []) for a in agents) else "partial"] += 1
    return per_step, unmatched


def gate_stats(report: dict | None) -> dict | None:
    """チェックポイントを独立エージェントが通った回数（report.json の events。記録の無い古いラウンドでは None）。"""
    runs = [t["events"][a] for t in (report or {}).get("tasks", []) if t.get("expect_status", "done") == "done"
            for a in t.get("agents", []) if isinstance(t.get("events"), dict) and a in t["events"]]
    if not runs and (report or {}).get("traces"):  # events を残す前のラウンドは、trace が集めた実行の記録で数える
        expect = {t.get("id"): t.get("expect_status", "done") for t in report.get("tasks", [])}
        runs = [[e.get("event", "") for e in r.get("events", [])] for rid, r in report["traces"]["runs"].items()
                if expect.get(rid.split("/", 1)[0], "done") == "done"]
    if not runs:
        return None
    return {"agents": len(runs), "count": Counter(e for run in runs for e in run),
            "reached": Counter(e for run in runs for e in set(run))}


READS = {"cat", "head", "tail", "sed", "less", "wc", "nl", "awk", "jq", "diff", "grep", "rg", "cmp"}
LISTS = {"ls", "find", "tree", "stat", "file", "du", "pwd"}
FILE_OPS = {"mkdir", "cp", "mv", "rm", "ln", "touch", "chmod", "tee", "rsync"}
KINDS = {"run": "実行", "write": "書く", "edit": "直す", "read": "読む", "search": "探す", "web": "Web", "other": "ほか"}
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][\w.-]*)\1")


def drop_heredocs(lines: list[str]) -> list[str]:
    """ヒアドキュメントの本文の行を除く。本文の後ろにつないだコマンドは残す（Codex は1回の実行にコマンドをつなぐ）。"""
    kept, end = [], None
    for line in lines:
        if end is not None:
            end = None if line.strip() == end else end
            continue
        kept.append(line)
        match = HEREDOC.search(line)
        end = match.group(2) if match else None
    return kept


OUTSIDE = re.compile(r"(?<![\w.~-])(?:/(?:private|tmp|Users|home|var|Volumes)/|~/)[^\s'\"`;|&)]*")


def interpret(action: dict) -> dict:
    """traces.json の1つの操作を、種類（KINDS）・表示・触れたファイル・skill のコマンドにする。"""
    tool, text = action.get("tool", ""), str(action.get("input", ""))
    files, commands, kind, label = [], [], "other", text
    if tool == "Bash":
        lines = text.splitlines() or [""]
        heredoc = any(HEREDOC.search(line) for line in lines)
        heads, cwd = [], ""
        script = "\n".join(drop_heredocs(lines)).replace("\\\n", " ")
        for seg in (s.strip() for s in re.split(r"&&|\|\||;|\||\n", script)):
            words = [w.strip("'\"") for w in seg.split()]
            if not words:
                continue
            heads.append(words[0])
            if words[0] == "cd" and len(words) > 1:
                cwd = "" if words[1] == "." else words[1].rstrip("/") + "/"
                continue
            if words[0] in ("python", "python3") or words[0].endswith(".py"):
                command = short_command(seg)
                if command:
                    commands.append(command)
            files += [(w if w.startswith("/") else cwd + w) for w in words[1:]
                      if not w.startswith("-") and re.search(r"[A-Za-z0-9_-]\.[A-Za-z]{1,5}$|/$", w)]
        if commands:
            kind = "run"
        elif heredoc or re.search(r"(?<![<>&\d])>(?!&)", text) or any(h in FILE_OPS for h in heads):
            kind = "write"
        elif any(h in READS for h in heads):
            kind = "read"
        elif any(h in LISTS for h in heads):
            kind = "search"
        elif {"git", "python", "python3"} & set(heads):
            kind = "run"
        label = "、".join(commands) if commands else lines[0][:120]
    elif tool == "Read":
        kind, files = "read", [text]
    elif tool == "Write":
        kind, files = "write", [text]
    elif tool in ("Edit", "MultiEdit", "NotebookEdit"):
        kind, files = "edit", [text]
    elif tool in ("Grep", "Glob"):
        kind = "search"
    elif tool in ("WebFetch", "WebSearch"):
        kind = "web"
    else:
        label = f"{tool} {text}".strip()
    fenced = bool(action.get("fenced"))  # fence.py が止めた操作は、外に触れていない
    return {"at": action.get("at", ""), "tool": tool, "kind": kind, "label": label, "input": text, "files": files,
            "commands": commands, "ok": action.get("ok"), "outside": bool(OUTSIDE.search(text)) and not fenced, "fenced": fenced}


def step_matchers(steps: list[dict]) -> tuple[dict, dict, list]:
    exact, prefix, mentions = {}, {}, []
    for step in steps:
        for command in step["commands"]:
            exact.setdefault(command, step["no"])
            prefix.setdefault(" ".join(command.split()[:2]), []).append(step["no"])
        refs = set(re.findall(r"\]\(([^)\s]+)\)", step["raw"])) | {c.strip() for c in CODE.findall(step["raw"])}
        refs = {re.sub(r"^.*[>}]/", "", r) for r in refs if " " not in r}
        mentions.append((step["no"], {r for r in refs if "/" in r and not PLACEHOLDER.search(r)}))
    return exact, prefix, mentions


def nearest(candidates: list[int], current: int | None) -> int:
    later = [c for c in candidates if current is None or c >= current]
    return min(later) if later else max(candidates)


def owner(files: list[str], steps: list[dict]) -> int | None:
    """書いたファイルを作る手順（本文にそのパスがあり、一番長く一致した手順）。"""
    best = None
    for f in files:
        for step in steps:
            for rx, size in step["patterns"]:
                if rx.search(f) and (best is None or size > best[0]):
                    best = (size, step["no"])
    return best[1] if best else None


def walk(actions: list[dict], steps: list[dict]) -> list[tuple[int | None, int | None]]:
    """操作ごとの（いる手順, 操作そのものが当たった手順）。コマンドは書かれた手順に移す（戻りも含む。1回の操作に複数あれば、
    最後のもの）。読む・書くは、本文にそのパスがある手順へ、前に進むときだけ移す（作った後のファイルを直すたびに前の手順へ
    戻さない）。どの手順にも当たらない操作は、直前の手順のままにする。"""
    exact, prefix, mentions = step_matchers(steps)
    current, out = None, []
    for action in actions:
        target, strong = None, False
        for command in reversed(action["commands"]):
            found = exact.get(command) or (nearest(prefix[key], current) if (key := " ".join(command.split()[:2])) in prefix else None)
            if found:
                target, strong = found, True
                break
        if target is None and action["kind"] == "read":
            candidates = sorted({no for no, refs in mentions for f in action["files"] for r in refs if f.endswith(r)})
            target = nearest(candidates, current) if candidates else None
        if target is None and action["kind"] in ("write", "edit"):
            target = owner(action["files"], steps)
        if target is not None and (strong or current is None or target > current):
            current = target
        out.append((current, target))
    return out


def parse_time(text: str) -> datetime.datetime | None:
    try:
        moment = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.astimezone()


def load_moves(rounds: list[dict], steps: list[dict]) -> dict:
    """ラウンドごと・実行ごとの、解釈した操作（経過の秒・手順・出力の抜粋・AI の推定つき）。
    AI の分析（analysis.json）は、今の記録を読んだもの（based_on が操作のハッシュと同じ）だけを操作に付ける。"""
    moves = {}
    for data in rounds:
        runs, analysis = {}, data.get("analysis", {})
        for rid, run in data.get("traces", {}).get("runs", {}).items():
            raw = [a for a in run.get("actions", []) if isinstance(a, dict)]
            actions = [interpret(a) for a in raw]
            times = [parse_time(a["at"]) for a in actions]
            start = next((t for t in times if t), None)
            for action, moment, (no, hit) in zip(actions, times, walk(actions, steps)):
                action["step"], action["hit"] = no, hit
                action["sec"] = (moment - start).total_seconds() if moment and start else None
            for action, source in zip(actions, raw):
                action["out"] = str(source.get("out", ""))
            ai = analysis.get(rid) if isinstance(analysis.get(rid), dict) else None
            fresh = bool(ai) and ai.get("based_on") == _lib.actions_hash(raw) and len(ai.get("ops", [])) == len(actions)
            for action, guess in zip(actions, ai.get("ops", []) if fresh else []):
                action["ai"] = guess if isinstance(guess, dict) else {}
            runs[rid] = {"runner": run.get("runner", ""), "source": run.get("source", ""), "actions": actions,
                         "events": run.get("events", []), **{k: run[k] for k in ("model", "effort", "settings") if run.get(k)},
                         "analysis": ai if fresh else None, "stale": bool(ai) and not fresh}
        if runs:
            moves[data.get("round")] = runs
    return moves


def seal_state(skill_dir: Path) -> tuple[str, str]:
    if not (skill_dir / _lib.SEAL_REL).is_file():
        return "none", "合格時の記録が無い"
    try:
        findings = rt.seal_findings(skill_dir, rt.load_contract(skill_dir))
    except (OSError, ValueError):
        return "bad", "合格時の記録を読めない"
    return ("ok", "合格時から変わっていない") if not findings else ("bad", f"合格時から {len(findings)} 件変わった")


def load_skill(skill_dir: Path, project: Path) -> dict:
    spec = read_json(skill_dir / _lib.SPEC_REL)
    if not isinstance(spec, dict):
        raise ValueError("dev/spec.json を読めない")
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    contract = read_json(skill_dir / "assets/contract.json") or {}
    probes = read_json(skill_dir / "dev/results/probe-results.json")
    rounds = load_rounds(skill_dir)
    steps = parse_steps(text)
    name = spec.get("name") or skill_dir.name
    last = rounds[-1] if rounds else None
    files, unmatched = assign_files(steps, last)
    report_md = skill_dir / "dev/convergence-report.md"
    report_text = report_md.read_text(encoding="utf-8") if report_md.is_file() else ""
    state = read_json(project / rt.RUNS_DIRNAME / name / "state.json")
    evals = read_json(skill_dir / "dev/evals.json") or {}
    seal = read_json(skill_dir / _lib.SEAL_REL)
    return {"dir": skill_dir, "project": project.resolve().as_posix(), "path": rel_to(skill_dir, project), "spec": spec, "name": name, "contract": contract,
            "tasks": {t["id"]: t for t in evals.get("tasks", []) if isinstance(t, dict) and t.get("id")} if isinstance(evals, dict) else {},
            "seal_files": len(seal.get("files", {})) if isinstance(seal, dict) else 0,
            "decisions": {d["id"]: d for d in spec.get("decisions", []) if d.get("id") and not d.get("retired")},
            "steps": steps, "probes": probes, "rounds": rounds, "checks": rule_checks(probes, rounds),
            "files": files, "unmatched": unmatched, "gates": gate_stats(last), "seal": seal_state(skill_dir),
            "moves": load_moves(rounds, steps),
            "conclusion": _lib.section(report_text, "結論") or _lib.section(report_text, "Conclusion"),
            "state": state if isinstance(state, dict) else None, "twins": [],
            "hooks": {p: report_skill.hook_events(project, p, name) for p in ("claude", "codex")}}


def find_skills(project: Path, extra: list[Path]) -> list[Path]:
    seen, found = set(), []
    for directory in [d for place in PLACES for d in sorted((project / place).glob("*"))] + extra:
        if not (directory / "SKILL.md").is_file() or directory.resolve() in seen:
            continue
        seen.add(directory.resolve())
        found.append(directory)
    return found


# ---------------------------------------------------------------- 図の部品

def text_width(text: str, size: float, mono: bool = True) -> float:
    total = 0.0
    for c in text:
        wide = ord(c) > 0x2E7F and not 0xFF61 <= ord(c) <= 0xFF9F
        if mono:
            total += size * (1.0 if wide else 0.6)
        elif wide:
            total += size
        elif c in "ijlI.,:;|!'`()[] ":
            total += size * 0.3
        elif c.isupper() or c in "mwMW@%&":
            total += size * 0.72
        else:
            total += size * 0.56
    return total


def wrap(text: str, width: float, size: float, max_lines: int, mono: bool = True) -> list[str]:
    lines, cur = [], ""
    for tok in TOKEN.findall(text):
        if text_width(cur + tok, size, mono) <= width or (tok in CLOSERS and cur):
            cur += tok
            continue
        carry = ""
        while cur and cur[-1] in OPENERS:  # 開き括弧は行末に残さない
            carry, cur = cur[-1] + carry, cur[:-1]
        if cur.strip():
            lines.append(cur.rstrip())
        cur = carry + tok.lstrip()
        while text_width(cur, size, mono) > width:  # 1語が幅を超えるときは文字で切る
            cut = len(cur)
            while cut > 1 and text_width(cur[:cut], size, mono) > width:
                cut -= 1
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur.strip():
        lines.append(cur.rstrip())
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        while last and text_width(last + "…", size, mono) > width:
            last = last[:-1]
        lines = lines[:max_lines - 1] + [last + "…"]
    return lines


def t(x: float, y: float, text: str, cls: str, extra: str = "") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{extra}>{esc(text)}</text>'


def chips(items: list[tuple[str, str, str]], width: float, size: float, mono: bool = True, max_rows: int = 3) -> tuple[list[str], float]:
    """(文字, class, ホバーの説明) を横に並べ、幅で折り返す。(要素, 高さ)。"""
    els, x, y, rows, h = [], 0.0, 0.0, 1, 22
    for i, (label, cls, tip) in enumerate(items):
        w = text_width(label, size, mono) + 16
        if x and x + w > width:
            if rows == max_rows:
                more = f"+{len(items) - i}"
                els.append(f'<g class="chip chip-more"><rect x="{x:.1f}" y="{y:.1f}" width="{text_width(more, size) + 16:.1f}" height="{h}" rx="4"/>'
                           + t(x + 8, y + 15.5, more, "chip-t") + "</g>")
                break
            x, y, rows = 0.0, y + h + 6, rows + 1
        els.append(f'<g class="chip {cls}"><title>{esc(tip)}</title><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="4"/>'
                   + t(x + 8, y + 15.5, label, "chip-t") + "</g>")
        x += w + 6
    return els, (y + h if items else 0.0)


def last_moves(skill: dict) -> dict:
    return skill["moves"].get(skill["rounds"][-1].get("round"), {}) if skill["rounds"] else {}


DOT_FONT = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "-": ("000", "000", "000", "111", "000", "000", "000"),
    ".": ("00", "00", "00", "00", "00", "11", "11"),
    "%": ("11000", "11001", "00010", "00100", "01000", "10011", "00011"),
    " ": ("000", "000", "000", "000", "000", "000", "000"),
}
SPARK = ("....#....", ".#..#..#.", "..#.#.#..", "...###...", "#########", "...###...", "..#.#.#..", ".#..#..#.", "....#....")


def dot_text(parts: list[tuple[str, str]], pitch: float = 4.6, label: str = "") -> str:
    """数字を 5×7 の点で描く。parts は (文字, class)。点の消えた所も薄い点で埋める。"""
    r, col, els = pitch * 0.42, 0, []
    for text, cls in parts:
        for ch in text:
            glyph = DOT_FONT.get(ch, DOT_FONT[" "])
            for y, row in enumerate(glyph):
                for x, bit in enumerate(row):
                    els.append(f'<circle cx="{(col + x) * pitch + r:.1f}" cy="{y * pitch + r:.1f}" r="{r:.2f}" class="{cls if bit == "1" else "dm-off"}"/>')
            col += len(glyph[0]) + 1
    w, h = max(col - 2, 0) * pitch + 2 * r, 6 * pitch + 2 * r
    name = label or "".join(text for text, _ in parts)
    return (f'<svg class="dm" viewBox="0 0 {w:.1f} {h:.1f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{esc(name)}">'
            + "".join(els) + "</svg>")


def pixel_mark(cell: int = 3) -> str:
    """見出しの印（点で描いた ✻）。"""
    size = cell * len(SPARK)
    rects = "".join(f'<rect x="{x * cell}" y="{y * cell}" width="{cell - 0.6:.1f}" height="{cell - 0.6:.1f}"/>'
                    for y, row in enumerate(SPARK) for x, c in enumerate(row) if c == "#")
    return f'<svg class="px-mark" width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">{rects}</svg>'


def pixel_cells(x: float, y: float, width: float, parts: list[tuple[int, str]], total: float, h: float = 10) -> list[str]:
    """数を、点の並び（幅 5px・間 2px の升）で描く。値のある部分は1升以上を点ける。"""
    n = max(int((width + 2) // 7), 1)
    lit: list[str] = []
    for value, cls in parts:
        k = max(1, round(n * value / total)) if value and total else 0
        lit += [cls] * k
    lit = lit[:n]
    return [f'<rect x="{x + i * 7:.1f}" y="{y:.1f}" width="5" height="{h}" rx="1" class="{lit[i] if i < len(lit) else "ev-track"}"/>'
            for i in range(n)]


# ---------------------------------------------------------------- ワークフロー図

W, LANE, RAIL, CX, CW, AX, AW = 1040, 104, 126, 172, 540, 748, 282
PAD, GAP, TOP, LANES = 16, 30, 50, 5


def decision_group(d: dict) -> str:
    levels = d.get("control", [])
    return next((GROUP[lv] for lv in _lib.LEVELS if lv in levels), "human")


def decision_chip(rid: str, skill: dict) -> tuple[str, str, str]:
    d = skill["decisions"].get(rid)
    if d is None:
        return rid, "chip-unknown", f"{rid}（spec に無い ID）"
    check = skill["checks"].get(rid, {})
    mark, tip = "", [f"{rid} {d.get('title', '')}", "守らせ方: " + ("、".join(LEVEL_NAMES.get(lv, lv) for lv in d.get("control", [])) or "なし")]
    if check.get("total"):
        failed = check["total"] - check["passed"]
        mark = " ✕" if failed else " ✓"
        tip.append(f"probe: {check['total']} 件中 成功 {check['passed']} 件")
    if check.get("review") is not None:
        tip.append(f"レビューの検出率: {check['review']:.2f}")
    return rid + mark, f"chip-{decision_group(d)}" + (" chip-ng" if mark == " ✕" else ""), "\n".join(tip)


def card(title: str, gate: str, lines: list[tuple], commands: list[str], ids: list[tuple[str, str, str]],
         tip: str) -> tuple[list[str], float, list[float]]:
    """手順のカード（左上が原点）。gate は右上の札（チェックポイントの名前）。lines は (文, class, 最大の行数[, 頭に太字で付ける語])。
    (要素, 高さ, 途中で終える行の中心の y)。"""
    inner = CW - 2 * PAD
    els, y, exits = [], PAD, []
    tag_w = text_width(gate, 12) + 20 if gate else 0
    if gate:
        els.append(f'<rect x="{CW - PAD - tag_w:.1f}" y="{y - 1}" width="{tag_w:.1f}" height="22" rx="4" class="wf-tag"/>'
                   + t(CW - PAD - tag_w / 2, y + 14.5, gate, "wf-tag-t", ' text-anchor="middle"'))
    heads = wrap(title, inner - (tag_w + 12 if gate else 0), 15, 2)
    els += [t(PAD, y + 15 + i * 22, line, "wf-title") for i, line in enumerate(heads)]
    y += 22 * max(1, len(heads)) + 4
    for text, cls, most, *extra in lines:
        lead = extra[0] if extra else ""
        indent = sum(13 if ord(c) > 0x7F else 7.8 for c in lead)  # 記号は全角で数え、続きの行と頭の語が重ならないようにする
        if lead:
            els.append(t(PAD, y + 14, lead, "wf-lead wf-lead-obs" if cls == "wf-obs-line" else "wf-lead"))
        if cls == "wf-exit":
            exits.append(y + 9.5)
        for line in wrap(text, inner - indent, 13, most):
            els.append(t(PAD + indent, y + 14, line, cls))
            y += 21
    if commands:
        cmd_els, h = chips([(c, "chip-cmd", c) for c in commands], inner, 12.5, max_rows=2)
        els.append(f'<g transform="translate({PAD},{y + 6:.1f})">' + "".join(cmd_els) + "</g>")
        y += h + 8
    if ids:
        id_els, h = chips(ids, inner, 12.5)
        els.append(f'<g transform="translate({PAD},{y + 6:.1f})">' + "".join(id_els) + "</g>")
        y += h + 8
    height = y + PAD - 2
    box = f'<rect width="{CW}" height="{height:.1f}" rx="8" class="wf-card{" wf-gate" if gate else ""}"/>'
    return [f"<title>{esc(tip)}</title>", box] + els, height, exits


def evidence(step: dict, skill: dict, outputs: list[tuple[str, str]]) -> list[dict]:
    """手順の右に並べる独立検証の記録（最後のラウンド）。bar は数を棒で、text は文で出す。"""
    rows = []
    moves = last_moves(skill)
    count = sum(a["step"] == step["no"] for run in moves.values() for a in run["actions"])
    if count:
        rows.append({"kind": "bar", "label": "操作", "parts": [(count, "ev-ops")], "value": f"{count} 回"})
    files = skill["files"].get(step["no"])
    if files and files["files"]:
        rows.append({"kind": "bar", "label": "ファイル", "parts": [(files["all"], "ev-all"), (files["partial"], "ev-part")],
                     "value": f"{files['files']} 件", "sub": f"全員が作った {files['all']}・一部だけ {files['partial']}"})
    stats = skill["gates"]
    if stats:
        n, total, reached = stats["agents"], stats["count"], stats["reached"]
        if "start" in step["gates"]:
            rows.append({"kind": "text", "label": "start", "ok": reached["start"] == n,
                         "text": f"{reached['start']}/{n} 人が実行" + (f"・やり直し {total['restart']} 回" if total["restart"] else "")})
        if "check" in step["gates"]:
            rows.append({"kind": "text", "label": "check", "ok": None, "text": f"計 {total['check']} 回・1人あたり {total['check'] / n:.1f} 回"})
        if "finish" in step["gates"]:
            rows.append({"kind": "text", "label": "finish", "ok": reached["finish"] == n,
                         "text": f"{reached['finish']}/{n} 人が通過" + (f"・却下 {total['finish-rejected']} 回" if total["finish-rejected"] else "")})
            if total["stop-blocked"]:
                rows.append({"kind": "text", "label": "hooks", "ok": None, "text": f"応答を止めた {total['stop-blocked']} 回"})
    rows += [{"kind": "text", "label": "出力", "ok": None, "text": f"{oid} を書く"} for oid, path in outputs if path and path in step["raw"]]
    return rows


def evidence_els(rows: list[dict], y: float, scale: dict) -> tuple[list[str], float]:
    els, bx = [], AX + 70
    bw = AW - 70 - 66
    for row in rows:
        els.append(t(AX, y + 14, row["label"], "ev-k"))
        if row["kind"] == "bar":
            els += pixel_cells(bx, y + 5, bw, row["parts"], scale.get(row["label"]) or 0)
            els.append(t(AX + AW - 58, y + 14, row["value"], "ev-v"))
            y += 24
            if row.get("sub"):
                els.append(t(bx, y + 8, row["sub"], "ev-sub"))
                y += 19
        else:
            mark = {True: '<tspan class="ev-ok">✓ </tspan>', False: '<tspan class="ev-warn">! </tspan>', None: ""}[row["ok"]]
            els.append(f'<text x="{bx}" y="{y + 14:.1f}" class="ev-t">{mark}{esc(row["text"])}</text>')
            y += 24
    return els, y


def exit_meanings(script: Path) -> dict:
    """スクリプトの説明の「終了コード: 0 成功、1 検査の指摘あり、…」の行を {番号: 意味} にする。無ければ空。"""
    try:
        match = EXIT_DOC.search(script.read_text(encoding="utf-8")[:6000])
    except (OSError, UnicodeDecodeError):
        return {}
    items = re.split(r"[、,]\s*(?=\d+\s)", match.group(1).strip()) if match else []
    return {m.group(1): IDS_IN_PARENS.sub("", m.group(2)).strip() for m in (re.match(r"(\d+)\s+(.+)", x) for x in items) if m}


def back_reason(skill: dict, back: dict, by_no: dict) -> str:
    """文にある戻りのわけ。終了コードの意味（コマンドのスクリプトの説明）と、戻った先の手順で直すこと。"""
    parts, script = [], back["cmd"].split()[0] if back["cmd"] else ""
    if back["code"]:
        meaning = exit_meanings(skill["dir"] / "scripts" / script).get(back["code"]) if script else None
        parts.append(f"終了コード {back['code']} は「{meaning}」（{script} の説明）" if meaning else
                     f"終了コード {back['code']} の意味は、手順の文にも" + (f" {script} の説明にも" if script else "") + "書かれていない")
    elif not back["case"]:
        parts.append("戻る場合が手順の文に書かれていない")
    if by_no[back["to"]]["fixes"]:
        parts.append(f"手順 {back['to']} で: {by_no[back['to']]['fixes'][0]}")
    return "。".join(parts)


VERBS = {"read": "読んでいた", "search": "探していた", "write": "書いていた", "edit": "直していた", "run": "実行していた"}


def ahead_target(entry: dict, no: int, steps: list[dict]) -> str:
    """操作を手順 no に当てた最初の操作を「dev/probes.json を読んでいた」の形にする。"""
    refs = next((r for n, r in step_matchers(steps)[2] if n == no), set())
    files = [f for f in entry["files"] if any(f.endswith(r) for r in refs) or owner([f], steps) == no]
    what = SKILL_REL.sub("", files[0]) if files else (entry["label"][:40] if entry["kind"] == "run" else "")
    return f"{what} を{VERBS[entry['kind']]}" if what and entry["kind"] in VERBS else ""


def back_cause(acts: list[dict], i: int, steps: list[dict]) -> tuple[str, list]:
    """acts[i] から acts[i + 1] へ前の手順に戻ったわけを、記録の操作から書く。エージェントが書いた理由ではない。
    (わけ, [(直したファイル, そのファイルを作る手順), ...])"""
    prev, dst = acts[i], acts[i + 1]["step"]
    if prev["ok"] is False:
        op = f"{KINDS[prev['kind']]} {prev['label']}"
        return f"直前の操作が失敗した（{op if len(op) <= 48 else op[:47] + '…'}）", []
    stay = []  # 戻る前に、元の手順にいた間の操作
    for a in reversed(acts[:i + 1]):
        if a["step"] != prev["step"]:
            break
        stay.append(a)
    if all(a["step"] != dst for a in acts[:i]):  # 先の手順のファイルに触れて、操作の当て先が先に進んでいた
        entry = next(a for a in acts if a["step"] == prev["step"])
        what = ahead_target(entry, prev["step"], steps)
        return f"手順 {dst} をまだしていなかった" + (f"（先に手順 {prev['step']} の {what}）" if what else ""), []
    edited = dict.fromkeys(f for a in reversed(stay) if a["kind"] in ("write", "edit") for f in a["files"])
    earlier = [(SKILL_REL.sub("", f), o) for f in edited if (o := owner([f], steps)) is not None and o < prev["step"]]
    failed = "失敗した操作の後に、" if any(a["ok"] is False for a in stay) else ""
    if earlier:
        return f"{failed}前の手順で作るファイルを直した", earlier
    return f"{failed}記録からはわからない（前の手順で作るファイルは直していない）", []


def observed_backs(skill: dict) -> dict:
    """最後のラウンドで、エージェントが前の手順に戻ったところ。戻った回数だけ入る。
    {(元の手順, 戻った手順): [(エージェント, 戻って最初の操作, わけ, 直したファイル), ...]}"""
    found: dict = {}
    for rid, run in sorted(last_moves(skill).items()):
        acts = [a for a in run["actions"] if a["step"] is not None]
        for i, (prev, cur) in enumerate(zip(acts, acts[1:])):
            if cur["step"] < prev["step"]:
                found.setdefault((prev["step"], cur["step"]), []).append(
                    (rid, f"{KINDS[cur['kind']]} {cur['label']}") + back_cause(acts, i, skill["steps"]))
    return found


def observed_reason(who: list[tuple]) -> str:
    """実際の戻りのわけを、人数の多い順に（同数ならわけの文字順）。前の手順で作るファイルを直した人がいれば、そのファイルも書く。"""
    parts = []
    counts = Counter(reason for _, reason in {(w[0], w[2]) for w in who})
    for reason, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):  # set の順はハッシュの種で変わるので、同数の順を決める
        by_step: dict = {}
        for f, o in dict.fromkeys(pair for w in who if w[2] == reason for pair in w[3]):
            by_step.setdefault(o, []).append(f)
        made = "、".join(f"手順 {o} で作る " + "・".join(fs[:3]) + (f" ほか {len(fs) - 3} 件" if len(fs) > 3 else "")
                        for o, fs in sorted(by_step.items()))
        parts.append(f"{n}人: {reason}" + (f"（{made}）" if made else ""))
    return "／".join(parts)


def step_name(step: dict) -> str:
    name = step["phase"] or step["title"]
    return name if len(name) <= 24 else name[:23] + "…"


def workflow_svg(skill: dict) -> str:
    spec, contract, steps, name = skill["spec"], skill["contract"], skill["steps"], skill["name"]
    outputs = [(o.get("id", ""), o.get("path", "").replace("{run}", f"{rt.RUNS_DIRNAME}/{name}"))
               for o in contract.get("outputs", spec.get("outputs", []))]
    outputs = [(oid, re.sub(r"\{in:([^}]+)\}", r"<\1>", path)) for oid, path in outputs]
    invoke = ([f"/{name}（Claude Code）"] if "claude" in spec.get("targets", []) else []) + \
             ([f"${name}（Codex）"] if "codex" in spec.get("targets", []) else [])
    how = "依頼の内容から自動で選ばれる" if spec.get("triggers", {}).get("implicit") is not False else "明示したときだけ使われる"
    inputs = []
    for i in spec.get("inputs", []):
        if i.get("ask"):
            note = "聞く"
        elif i.get("default") is not None:
            note = "既定 " + json.dumps(i.get("default"), ensure_ascii=False)
        else:
            note = "任意"
        inputs.append(f"{i.get('key')}（{note}）")
    rows = [(None, card("起動と入力", "", [(f"{how}。明示: {'・'.join(invoke) or 'なし'}", "wf-sub", 2),
                                         ("入力: " + ("、".join(inputs) or "なし"), "wf-sub", 4)], [], [],
                        "SKILL.md の「1. 使う場面」と「3. 入力」"), [])]
    by_no = {s["no"]: s for s in steps}
    rnd = skill["rounds"][-1].get("round") if skill["rounds"] else None
    seen = {k: v for k, v in observed_backs(skill).items() if k[0] in by_no and k[1] in by_no}
    for step in steps:
        no = step["no"]
        lines = [(step["detail"], "wf-sub", 2)] if step["detail"] else []
        lines += [(x, "wf-exit", 2, "■ 終了 ") if kind == "exit" else (x, "wf-cond", 2, "◇ 条件 ") for kind, x in step["turns"][:3]]
        lines += [(f"終了コード {code}: {action}", "wf-branch", 2, "└ ") for code, action in step["branches"][:3]]
        if step["loops"]:
            lines.append((f"手順 {no} の中で: " + "／".join(step["loops"]), "wf-loop-t", 3, "↻ 繰り返す "))
        for b in step["backs"]:  # 戻る場合・戻り先・わけを、戻る元のカードに書く
            if b["to"] in by_no and b["to"] < no:
                case = f"{b['label']}なら、" if b["code"] else (f"{b['case']}、" if b["case"] else "")
                lines.append((f"{case}手順 {b['to']}「{step_name(by_no[b['to']])}」へ", "wf-back-line", 2, "↩ 戻る "))
                why = back_reason(skill, b, by_no)
                if why:
                    lines.append((why, "wf-back-line", 3, "└ なぜ "))
        went = sorted(((dst, who) for (src, dst), who in seen.items() if src == no), key=lambda x: (-len({w[0] for w in x[1]}), x[0]))
        for dst, who in went[:3]:
            firsts = Counter(w[1] for w in who).most_common()
            first = firsts[0][0] if len(firsts[0][0]) <= 48 else firsts[0][0][:47] + "…"
            lines.append((f"手順 {dst}「{step_name(by_no[dst])}」へ {len({w[0] for w in who})}人。戻って最初の操作: {first}"
                          + (f" ほか {len(firsts) - 1} 通り" if len(firsts) > 1 else ""), "wf-obs-line", 3, "↩ 実際の戻り "))
            lines.append((observed_reason(who), "wf-obs-line", 3, "└ なぜ "))
        ids = [decision_chip(rid, skill) for rid in step["ids"]]
        gate = ("チェックポイント " + "・".join(step["gates"])) if step["gates"] else ""
        rows.append((step, card(step["title"], gate, lines, step["commands"], ids, step["raw"]), evidence(step, skill, outputs)))
    sections = [short_command(s.get("run", "")) or s.get("run", "") for s in contract.get("report", {}).get("sections", [])]
    bottom = [("finish が出した本文をそのまま返答する" + (f"。報告の節: {'、'.join(sections)}" if sections else ""), "wf-sub", 3)]
    bottom += [(f"出力 {o.get('id')}: {o.get('path', '').replace('{run}', f'{rt.RUNS_DIRNAME}/{name}')}", "wf-sub", 2)
               for o in contract.get("outputs", spec.get("outputs", []))]
    rows.append((None, card("報告と出力", "", bottom, [], [], "SKILL.md の「5. 出力の契約」と「7. 報告」"), []))
    scale = {label: max([sum(v for v, _ in r["parts"]) for _, _, ev in rows for r in ev if r["label"] == label] + [0])
             for label in ("操作", "ファイル")}

    back_els, cards, nodes, ev_els, flow_els, y = [], [], [], [], [], float(TOP)
    spans, centers = {}, []
    for step, (parts, height, exit_ys), ev in rows:
        drawn, bottom_y = evidence_els(ev, y + 6, scale)
        ev_els += drawn
        target = f' id="{anchor(name, "wf", step["no"])}"' if step else ""
        cards.append(f'<g{target} transform="translate({CX},{y:.1f})">' + "".join(parts) + "</g>")
        cy = y + 26
        centers.append(cy)
        if step is None:
            nodes.append(f'<rect x="{RAIL - 6}" y="{cy - 6:.1f}" width="12" height="12" rx="2" class="wf-end"/>')
        else:
            spans[step["no"]] = (y, height, cy)
            gate = " wf-node-gate" if step["gates"] else ""
            nodes.append(f'<rect x="{RAIL - 15}" y="{cy - 15:.1f}" width="30" height="30" rx="5" class="wf-node{gate}"/>'
                         + t(RAIL, cy + 4.6, str(step["no"]), "wf-node-t" + (" wf-node-t-gate" if gate else ""), ' text-anchor="middle"'))
            if step["loops"]:  # 通るまで繰り返す手順は、番号の右に輪を付ける
                x0 = RAIL + 15
                flow_els.append(f'<path d="M{x0},{cy - 8:.1f} C{x0 + 22},{cy - 17:.1f} {x0 + 22},{cy + 17:.1f} {x0 + 1},{cy + 8:.1f}" '
                                f'class="wf-loop" marker-end="url(#wf-arrow-small)"><title>{esc("繰り返す: " + "／".join(step["loops"]))}</title></path>')
        for ey in exit_ys:  # 途中で終える道は、カードの右へ抜けて終わりの印に入る
            ya = y + ey
            flow_els.append(f'<path d="M{CX + CW},{ya:.1f} H{CX + CW + 13}" class="wf-exit-edge" marker-end="url(#wf-arrow-small)"/>'
                            f'<rect x="{CX + CW + 17}" y="{ya - 4:.1f}" width="8" height="8" rx="1.5" class="wf-end"><title>ここで終わる</title></rect>')
        y += max(height, bottom_y - y) + GAP
    total_h = y - GAP + 20
    rail = f'<line x1="{RAIL}" y1="{centers[0]:.1f}" x2="{RAIL}" y2="{centers[-1]:.1f}" class="wf-rail"/>'
    edges = []  # (class, 元, 先, 名前, ホバーの説明)。文の戻りは実線、最後のラウンドの実際の戻りは点線
    for s in steps:
        for b in s["backs"]:
            if b["to"] in spans and b["to"] < s["no"]:
                who = sorted({w[0] for w in seen.pop((s["no"], b["to"]), [])})
                note = f"。R{rnd} で戻った人: " + "、".join(who) if who else ""
                why = back_reason(skill, b, by_no)
                edges.append(("wf-back", s["no"], b["to"], b["label"] + (f"・実際に戻った {len(who)}人" if who else ""),
                              f"手順 {s['no']} の文にある戻り（{b['label']}）" + (f"。なぜ: {why}" if why else "") + note))
    observed = list(seen.items())
    for (src, dst), who in observed:
        agents = sorted({w[0] for w in who})
        edges.append(("wf-obs", src, dst, f"実際に戻った {len(agents)}人" + (f"・{len(who)}回" if len(who) > len(agents) else ""),
                      f"R{rnd} で手順 {src} から手順 {dst} に戻った（{len(who)} 回）: " + "、".join(agents) + f"。なぜ: {observed_reason(who)}"))
    lanes: list = [[] for _ in range(LANES)]  # 通り道ごとの (先, 元)。短い線から、重ならない一番内側の通り道に置く
    placed, hidden = [], 0
    for e in sorted(edges, key=lambda e: (e[1] - e[2], e[0] != "wf-back", e[1])):
        k = next((k for k, used in enumerate(lanes) if all(e[1] < lo or e[2] > hi for lo, hi in used)), None)
        if k is None:
            hidden += e[0] == "wf-obs"
            continue
        lanes[k].append((e[2], e[1]))
        placed.append((k, e))
    ports: dict = {}

    def port(no):  # 同じ番号に出入りする線は、上下に少しずらす
        k = ports.get(no, 0)
        ports[no] = k + 1
        return spans[no][2] + (0, -7, 7, -12, 12)[min(k, 4)]

    for lane, (cls, src, dst, tag, tip) in placed:
        lx = LANE - 18 - 18 * lane
        y1, y2 = port(src), port(dst)
        arrow = "wf-arrow-back" if cls == "wf-back" else "wf-arrow-obs"
        back_els.append(f'<g><title>{esc(tip)}</title><path d="M{RAIL - 16},{y1:.1f} H{lx} V{y2:.1f} H{RAIL - 19}" class="{cls}" '
                        f'marker-end="url(#{arrow})"/><text transform="translate({lx - 6:.1f},{(y1 + y2) / 2:.1f}) rotate(-90)" '
                        f'text-anchor="middle" class="{cls}-t">{esc(tag)}</text></g>')
    if hidden:
        back_els.append(t(CX, total_h + 4, f"実際の戻り {len(observed)} 通りのうち {len(observed) - hidden} 通りを描いた"
                          "（ほかは「エージェントの動き」で見る）", "wf-note"))
        total_h += 24
    region = []
    start = next((s["no"] for s in steps if "start" in s["gates"]), None)
    finish = next((s["no"] for s in reversed(steps) if "finish" in s["gates"]), None)
    if spec.get("control", {}).get("hooks", True) and start and finish and start <= finish:
        top_y = spans[start][0] - 28
        end_y = spans[finish][0] + spans[finish][1] + 10
        region.append(f'<rect x="{CX - 10}" y="{top_y:.1f}" width="{CW + 20}" height="{end_y - top_y:.1f}" rx="10" class="wf-hooks">'
                      "<title>hooks が働く範囲：編集の前（保護ファイルの停止）、編集の後（出力の検査）、応答を終える前（出力全体の検査）</title></rect>")
        region.append(t(CX + 4, top_y + 18, "hooks が働く範囲（run.py start から finish まで）", "wf-hooks-t"))
    people = len(last_moves(skill))
    right_head = (f"独立検証 R{rnd} の記録（{people} 人）" if people else f"独立検証 R{rnd} の記録") if rnd is not None else "独立検証の記録なし"
    head = (t(CX, 22, "手順（SKILL.md の「2. 手順」）", "wf-colh") + t(AX, 22, right_head, "wf-colh")
            + f'<line x1="{CX}" y1="33" x2="{W - 10}" y2="33" class="wf-colline"/>')
    defs = "<defs>" + "".join(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{size}" markerHeight="{size}" '
                              f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="{cls}"/></marker>'
                              for mid, size, cls in (("wf-arrow-back", 7, "wf-arrow-back"), ("wf-arrow-obs", 6, "wf-arrow-obs"),
                                                     ("wf-arrow-small", 4.5, "wf-arrow-back"))) + "</defs>"
    label = f"{name} のワークフロー図。手順 {len(steps)} 個"
    return (f'<svg class="wf" viewBox="0 0 {W} {total_h:.0f}" width="{W}" height="{total_h:.0f}" role="img" '
            f'aria-label="{esc(label)}" xmlns="http://www.w3.org/2000/svg">{defs}{head}' + "".join(region) + rail
            + "".join(back_els) + "".join(cards) + "".join(nodes) + "".join(flow_els) + "".join(ev_els) + "</svg>")


# ---------------------------------------------------------------- 収束テストの図

def metric_chart(rounds: list[dict], key: str, threshold: float, order: list[str]) -> str:
    w, h, left, right, top, bottom = 330, 210, 32, 44, 12, 28
    xs = [d.get("round") for d in rounds]
    span = (w - left - right) / (len(xs) - 1) if len(xs) > 1 else 0

    def px(rd):
        return left + (xs.index(rd) * span if len(xs) > 1 else (w - left - right) / 2)

    def py(v):
        return top + (1 - v) * (h - top - bottom)

    els = []
    for v in (0, 0.25, 0.5, 0.75, 1):
        els.append(f'<line x1="{left}" y1="{py(v):.1f}" x2="{w - right}" y2="{py(v):.1f}" class="{"ch-axis" if v == 0 else "ch-grid"}"/>')
        if v in (0, 0.5, 1):
            els.append(t(left - 8, py(v) + 4, f"{v:g}", "ch-tick", ' text-anchor="end"'))
    for rd in xs:
        els.append(t(px(rd), h - 7, f"R{rd}", "ch-tick", ' text-anchor="middle"'))
    els.append(f'<line x1="{left}" y1="{py(threshold):.1f}" x2="{w - right}" y2="{py(threshold):.1f}" class="ch-threshold"/>')
    ends = []
    for i, tid in enumerate(order):
        pts = [(d.get("round"), task.get(key)) for d in rounds for task in d.get("tasks", [])
               if task.get("id") == tid and isinstance(task.get(key), (int, float))]
        if not pts:
            continue
        color = f"s{i % 6 + 1}"
        if len(pts) > 1:
            els.append(f'<polyline points="{" ".join(f"{px(r):.1f},{py(v):.1f}" for r, v in pts)}" class="ch-line {color}"/>')
        for r, v in pts:
            els.append(f'<rect x="{px(r) - 4:.1f}" y="{py(v) - 4:.1f}" width="8" height="8" rx="1" class="ch-dot {color}"/>')
            els.append(f'<circle cx="{px(r):.1f}" cy="{py(v):.1f}" r="11" class="ch-hit {color}"><title>R{r} {esc(tid)} {key} {v:.3f}</title></circle>')
        ends.append([py(pts[-1][1]), px(pts[-1][0]), tid.split("-")[0], color])
    ends.sort()
    for i in range(1, len(ends)):  # 線の端の名前が重ならないよう、14px ずつ離す
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 14)
    els += [t(x + 9, y + 4.5, label, f"ch-end {color}") for y, x, label, color in ends]
    return (f'<svg class="ch" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(key)} のラウンドごとの値">'
            + "".join(els) + "</svg>")


# ---------------------------------------------------------------- エージェントの動きの図

def mark_pop(agent: str, color: str, n: int, a: dict, where: str, nxt: dict | None) -> str:
    """印（スクリプトの実行・失敗・作業ディレクトリの外）に重ねたときに出す中身の HTML。属性に入れるので改行は文字参照にする。"""
    kinds = ([("run", "skill のスクリプトの実行" if a["commands"] else "コマンドの実行")] if a["kind"] == "run" else []) \
        + ([("ng", "外への操作を止めた" if a["fenced"] else "失敗した操作")] if a["ok"] is False else []) \
        + ([("out", "作業ディレクトリの外に触れた操作")] if a["outside"] else [])
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", a["input"])
    lines = text.splitlines()
    cut = "\n".join(lines[:14])[:700]
    rest = len(text) - len(cut)
    body, last = [], 0
    for m in OUTSIDE.finditer(cut):  # 作業ディレクトリの外のパスに印を付ける
        body += [esc(cut[last:m.start()]), f"<mark>{esc(m.group(0))}</mark>"]
        last = m.end()
    body.append(esc(cut[last:]) + (f"\n…（ほか {rest} 字）" if rest > 0 else ""))
    result = {False: '<span class="no">✕ 失敗</span>', True: '<span class="yes">✓ 成功</span>'}.get(a["ok"], "記録なし")
    if a["fenced"]:
        result = '<span class="no">✕ 外への操作を fence.py が止めた（外には触れていない）</span>'
    rows = [("手順", esc(where)), ("結果", result)]
    if a["outside"] or a["fenced"]:
        rows.append(("止めたパス" if a["fenced"] else "外のパス",
                     "<br>".join(f"<code>{esc(p)}</code>" for p in dict.fromkeys(OUTSIDE.findall(text))) or "—"))
    if a["ok"] is False and nxt:  # 失敗の後にどうしたか
        rows.append(("次の操作", esc(("" if nxt["kind"] == "other" else KINDS[nxt["kind"]] + " ") + nxt["label"][:80])))
    head = "".join(f'<span class="pop-k pop-k-{k}">{esc(label)}</span>' for k, label in kinds)
    chips = "".join(f"<code>{esc(c)}</code>" for c in a["commands"])
    pop = (f'<div class="pop pop-{kinds[0][0]}"><div class="pop-h">{head}</div>'
           f'<div class="pop-m"><span class="sw {color}"></span>{esc(agent)} ・ #{n} ・ {a["sec"] / 60:.1f} 分 ・ {esc(a["tool"])}</div>'
           + (f'<div class="pop-c">{chips}</div>' if chips else "") + f'<pre>{"".join(body)}</pre>'
           + "<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>"
           + f'<div class="pop-f">操作の一覧の #{n} ・ <span class="pin-off">クリックで固定</span><span class="pin-on">Esc か外をクリックで閉じる</span></div></div>')
    return esc(pop).replace("\n", "&#10;")


def movement_svg(steps: list[dict], runs: list[tuple[str, dict]], uid: str) -> str:
    """縦が手順（上が始め）、横が経過時間。手順の行の中にエージェントごとの帯を持ち、いた時間を点の並びの棒で描く。"""
    rows = [("始める前", None, False)] + [(s["phase"] or s["title"], s["no"], bool(s["gates"])) for s in steps]
    lanes, lane_h, lane_gap = max(1, len(runs)), 9, 4
    band = lanes * lane_h + (lanes - 1) * lane_gap
    row_h = max(30, band + 16)
    w, left, right, top = 1040, 300, 18, 6
    plot_h = row_h * len(rows)
    h = top + plot_h + 32
    end = max([a["sec"] for _, run in runs for a in run["actions"] if a["sec"] is not None] + [60]) / 60
    tick = next(x for x in (1, 2, 5, 10, 15, 20, 30, 60, 120, 240) if end / x <= 8)
    end = -(-end // tick) * tick
    index = {no: k for k, (_, no, _) in enumerate(rows)}
    uid = re.sub(r"[^A-Za-z0-9_-]", "-", uid)

    def px(sec):
        return left + sec / 60 / end * (w - left - right)

    def ly(no, i):
        return top + row_h * index.get(no, 0) + (row_h - band) / 2 + i * (lane_h + lane_gap)

    els, bars, links, hits, marks = [], [], [], [], []  # hits は印の無い操作。印のある操作（marks）を上に重ねる
    names = {s["no"]: step_name(s) for s in steps}
    for k, (label, no, gate) in enumerate(rows):
        y = top + row_h * k
        if k % 2 == 0:
            els.append(f'<rect x="0" y="{y:.1f}" width="{w}" height="{row_h}" class="mv-zebra"/>')
        els.append(f'<rect x="8" y="{y + row_h / 2 - 11:.1f}" width="30" height="22" rx="4" class="mv-no{" mv-no-gate" if gate else ""}"/>')
        els.append(t(23, y + row_h / 2 + 4.5, "前" if no is None else str(no), "mv-no-t" + (" mv-no-t-gate" if gate else ""), ' text-anchor="middle"'))
        els += [t(48, y + row_h / 2 + 4.5, line, "mv-row" + (" mv-row-gate" if gate else "")) for line in wrap(label, left - 62, 13, 1)]
    m = 0
    while m <= end + 1e-9:
        x = px(m * 60)
        els.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" class="mv-grid"/>')
        els.append(t(x, top + plot_h + 21, f"{m:g} 分", "mv-tick", ' text-anchor="middle"'))
        m += tick
    for i, (agent, run) in enumerate(runs):
        color = f"s{i % 6 + 1}"
        timed = [a for a in run["actions"] if a["sec"] is not None]
        segs: list[list] = []  # [手順, 始め, 終わり, 操作の数]。終わりは次の手順に移った時刻
        for a in timed:
            if segs and segs[-1][0] == a["step"]:
                segs[-1][2], segs[-1][3] = a["sec"], segs[-1][3] + 1
            else:
                if segs:
                    segs[-1][2] = a["sec"]
                segs.append([a["step"], a["sec"], a["sec"], 1])
        for k, (no, a, b, n) in enumerate(segs):
            x1 = px(a)
            x2 = max(px(b), x1 + 4)
            y = ly(no, i)
            where = "始める前" if no is None else f"手順 {no}"
            tip = f"{agent}: {where}（{a / 60:.1f}〜{b / 60:.1f} 分、操作 {n} 回）"
            bars.append(f'<rect x="{x1:.1f}" y="{y:.1f}" width="{x2 - x1:.1f}" height="{lane_h}" class="mv-bar {color}"><title>{esc(tip)}</title></rect>')
            if k + 1 < len(segs):
                links.append(f'<line x1="{x2:.1f}" y1="{y + lane_h / 2:.1f}" x2="{x2:.1f}" y2="{ly(segs[k + 1][0], i) + lane_h / 2:.1f}" '
                             f'class="mv-link {color}"/>')
        acts = run["actions"]
        for k, a in enumerate(acts):
            if a["sec"] is None:
                continue
            n, x, y = k + 1, px(a["sec"]), ly(a["step"], i) + lane_h / 2  # n は操作の一覧の番号と同じ
            tip = (f"{agent} #{n} {a['sec'] / 60:.1f} 分 {KINDS[a['kind']]}: {a['label']}"
                   + ("（失敗）" if a["ok"] is False else "") + ("（作業ディレクトリの外）" if a["outside"] else ""))
            if a["ok"] is False:
                mark = (f'<g class="mv-ng"><circle cx="{x:.1f}" cy="{y:.1f}" r="6"/>'
                        f'<path d="M{x - 2.6:.1f},{y - 2.6:.1f} L{x + 2.6:.1f},{y + 2.6:.1f} M{x + 2.6:.1f},{y - 2.6:.1f} L{x - 2.6:.1f},{y + 2.6:.1f}"/></g>')
            elif a["outside"]:
                mark = f'<rect x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" rx="1.5" class="mv-out"/>'
            elif a["kind"] == "run":
                mark = f'<rect x="{x - 1.6:.1f}" y="{y - 1.6:.1f}" width="3.2" height="3.2" class="mv-run"/>'
            else:  # 印の無い操作は、ブラウザの標準の説明だけ
                hits.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" class="mv-hit {color}"><title>{esc(tip)}</title></circle>')
                continue
            where = "始める前" if a["step"] is None else f"手順 {a['step']} {names.get(a['step'], '')}"
            nxt = acts[k + 1] if k + 1 < len(acts) else None
            focus = ' tabindex="0"' if a["ok"] is False or a["outside"] else ""  # 数の少ない失敗と外だけキーボードで巡る
            marks.append(f'<g class="mv-pt {color}" data-pop="{mark_pop(agent, color, n, a, where, nxt)}" aria-label="{esc(tip)}"{focus}>'
                         f'{mark}<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="mv-hit"/></g>')
    defs = (f'<defs><pattern id="pxp-{uid}" width="5" height="{h}" patternUnits="userSpaceOnUse"><rect width="4" height="{h}" fill="#fff"/></pattern>'
            f'<mask id="pxm-{uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="url(#pxp-{uid})"/></mask></defs>')
    return (f'<svg class="mv" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="エージェントがいた手順の時間の流れ">{defs}'
            + "".join(els) + "".join(links) + f'<g mask="url(#pxm-{uid})">' + "".join(bars) + "</g>" + "".join(hits) + "".join(marks) + "</svg>")


def step_seq(actions: list[dict]) -> str:
    """通った手順の順。前の手順に戻ったところに印を付ける。"""
    seq = []
    for a in actions:
        label = "前" if a["step"] is None else a["step"]
        if not seq or seq[-1] != label:
            seq.append(label)
    shown = seq if len(seq) <= 32 else seq[:20] + ["…"] + seq[-10:]
    items, prev = [], None
    for s in shown:
        if s == "…":
            items.append('<span class="sq gap">…</span>')
            continue
        if isinstance(s, int) and isinstance(prev, int) and s < prev:
            items.append(f'<span class="sq back" title="手順 {prev} から手順 {s} に戻った">{s}</span>')
        else:
            items.append(f'<span class="sq">{esc(s)}</span>')
        prev = s
    return '<span class="seq">' + "".join(items) + "</span>"


def key_item(svg: str, label: str) -> str:
    return f'<span><svg width="26" height="14" viewBox="0 0 26 14" aria-hidden="true">{svg}</svg><span>{label}</span></span>'


def agent_key(cls: str) -> str:
    return "".join(f'<rect x="{x}" y="3" width="4" height="8" class="mv-bar {cls}"/>' for x in (1, 6, 11, 16, 21))


MARK_KEYS = (key_item(agent_key("s1") + '<rect x="11.4" y="5.4" width="3.2" height="3.2" class="mv-run"/>', "skill のスクリプトの実行")
             + key_item('<g class="mv-ng"><circle cx="13" cy="7" r="6"/><path d="M10.4,4.4 L15.6,9.6 M15.6,4.4 L10.4,9.6"/></g>', "失敗した操作")
             + key_item('<rect x="8" y="2" width="10" height="10" rx="1.5" class="mv-out"/>', "作業ディレクトリの外に触れた操作")
             + '<span class="muted">印に重ねると中身が出る（クリック・タップで固定、Esc で閉じる）</span>')


def status_badge(status: str) -> str:
    kind = {"done": "ok", "unused": "none", "failed": "bad", "aborted": "warn"}.get(status, "none" if not status else "warn")
    return badge(kind, STATUS_NAMES.get(status, status) or "—")


SETTINGS_NOTE = "codex exec の記録はモデルを持たないので、コマンドの -m・-c か ~/.codex/config.toml から読んだ値"


def model_cell(run: dict) -> str:
    """エージェントのモデルと推論エフォート。記録に無ければ「記録なし」。"""
    if not run.get("model") and not run.get("effort"):
        return '<td class="muted">記録なし</td>'
    src = f'<small class="muted" title="{esc(SETTINGS_NOTE)}">（設定から）</small>' if run.get("settings") else ""
    return (f'<td class="mdl"><code>{esc(run.get("model") or "—")}</code>'
            f'<span class="eff">{esc(run.get("effort") or "記録なし")}</span>{src}</td>')


def model_list(runs) -> str:
    """ラウンドで使ったモデルと推論エフォート（同じ組は1つにまとめる）。"""
    pairs = dict.fromkeys(r["model"] + (f"（{r['effort']}）" if r.get("effort") else "") for r in runs if r.get("model"))
    return esc("、".join(pairs))


TMP_ROOT = r"/(?:private/)?(?:var/folders/[^/]+/[^/]+/T|tmp|var/tmp)"
OUT_PLACES = [  # (種類, 場所の根を1つ目の組に取る正規表現, 名前, 原因, ほかのエージェントからも見えるか)。上から順に当てる
    ("tool-results", re.compile(r"^(.*/\.claude/projects/[^/]+/[^/]+/tool-results/[^/]+)"),
     "Claude Code が長い出力を逃がしたファイル（tool-results）",
     "出力が長いと、Claude Code は本文の代わりにこのファイルのパスを返す。エージェントはそれを読んで、自分の操作の出力の続きを見た", False),
    ("scratchpad", re.compile(r"^(/(?:private/)?tmp/claude-\d+/[^/]+/[^/]+(?:/scratchpad(?:/[^/]+)?)?)"),
     "Claude Code のセッションの一時置き場（scratchpad）",
     "Claude Code は、一時ファイルをセッションごとの scratchpad に置くよう指示する。Agent ツールで動かしたエージェントにも、"
     "動かした側のセッションの置き場が渡され、プロンプトの縛り（作業ディレクトリの外は読まず、変えない）よりこの指示に従った", True),
    ("convergence", re.compile(r"^(" + TMP_ROOT + r"/skill-foundation(?:/[^/]+)?)"),
     "convergence.py の既定の作業場所（OS の一時ディレクトリ）",
     "convergence.py の prepare・run・diff を --workdir 無しで実行すると、OS の一時ディレクトリの skill-foundation/<スキルの名前> に"
     "ラウンドの作業場所を作る。場所はスキルの名前だけで決まるので、同じスキルを作るエージェントの間で重なる", True),
    ("tmp", re.compile(r"^(" + TMP_ROOT + r"(?:/[^/]+)?)"), "OS の一時ディレクトリ", "エージェントが一時ファイルの置き場に選んだ", True),
    ("home", re.compile(r"^((?:~|/Users/[^/]+|/home/[^/]+)(?:/[^/]+)?)"), "ホームディレクトリ", "作業ディレクトリの外の、ユーザーのファイルに触れた", True),
    ("other", re.compile(r"^(/[^/]+(?:/[^/]+)?)"), "そのほかの場所", "作業ディレクトリの外のファイルに触れた", True),
]
PROJECT_PLACE = ("元のプロジェクト（作業ディレクトリの写し元）",
                 "作業ディレクトリの外にある元のプロジェクトに触れた。元のプロジェクトには、作成の経緯（前のラウンドの記録など）がある", True)
HIDDEN_OUT = re.compile(r"^convergence\.py (?:prepare|run|diff)\b.*--round")  # 入力にパスが無くても外に書くコマンド
HIDDEN_NAME = re.compile(r"convergence\.py\s+(?:prepare|run|diff)\s+(?:--\S+\s+\S+\s+)*\S*?([\w.-]+)/?(?:\s|$)")
REMOVE = re.compile(r"(?:^|[;&|(]\s*)(?:rm|rmdir)\s")
TRACE_CUT = 400  # convergence.py の trace が残す入力の字数
LEVELS = {"good": "✓ 守られている", "warn": "▲ 条件つき", "unknown": "？ 判断できない", "bad": "✕ 守られていない"}


def out_key(kind: str, root: str) -> str:
    """場所の根を比べる形。OS の一時ディレクトリはエージェントごとにパスが違っても同じ場所として扱う。"""
    return re.sub("^" + TMP_ROOT, "$TMPDIR", root) if kind in ("convergence", "tmp") else root


def outside_touches(run: dict, project: str) -> list[dict]:
    """1人の操作のうち、作業ディレクトリの外に触れたもの。convergence.py を --workdir 無しで実行した操作（入力にパスは無いが、
    既定の作業場所に書く）も入れる。"""
    found = []
    for n, a in enumerate(run["actions"], 1):
        if a["fenced"]:
            continue
        verb = "消す" if REMOVE.search(a["input"]) else KINDS[a["kind"]]
        for p in dict.fromkeys(OUTSIDE.findall(a["input"])):
            if project and (p == project or p.startswith(project + "/")):
                kind, root = "project", project
            else:
                kind, root = next(((k, m.group(1)) for k, rx, *_ in OUT_PLACES if (m := rx.match(p))), ("other", p))
            found.append({"n": n, "a": a, "verb": verb, "kind": kind, "root": root, "key": out_key(kind, root), "path": p,
                          "cut": len(a["input"]) >= TRACE_CUT and a["input"].endswith(p), "hidden": False})
        if any(HIDDEN_OUT.match(c) for c in a["commands"]) and "--workdir" not in a["input"]:
            name = HIDDEN_NAME.search(a["input"])
            key = "$TMPDIR/skill-foundation" + (f"/{name.group(1)}" if name else "")
            found.append({"n": n, "a": a, "verb": "書く", "kind": "convergence", "root": key, "key": key, "path": "",
                          "cut": False, "hidden": True})
    return found


def related(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def out_judge(agent: str, touches: list[dict], others: list[tuple[str, str]]) -> tuple[list, list]:
    """1人の外の操作から、独立性とテスト性の (段, 理由) を決める。others は同じラウンドのほかのエージェントの (名前, 場所)。"""
    made, foreign, unknown, shared, writes, runs, skill_files = [], [], [], [], [], [], []
    for x in touches:
        if x["cut"]:
            unknown.append(x)
            continue
        if x["kind"] == "tool-results":
            continue
        if x["verb"] in ("書く", "直す"):
            made.append(x["key"])
        elif not any(related(m, x["key"]) for m in made):
            foreign.append(x)
        if x["verb"] in ("書く", "直す", "消す"):
            writes.append(x)
            if re.search(r"/\.(?:claude|agents)/skills/", x["path"]):
                skill_files.append(x)
        elif x["verb"] == "実行":
            runs.append(x)
        if dict(OUT_PLACE_INFO)[x["kind"]][2] and x["key"] not in [s["key"] for s in shared]:
            shared.append(x)
    mine = [x["key"] for x in touches if x["kind"] != "tool-results" and not x["cut"]]
    hit = sorted({name for name, key in others for m in mine if related(m, key)})
    indep = []
    if hit:
        indep.append(("bad", f"{agent}: 同じ外の場所に、ほかのエージェント（{'、'.join(hit)}）も触れた"))
    for x in foreign:
        indep.append(("bad", f"{agent}: 自分が作っていない {short_out(x['root'])} を{x['verb']}（#{x['n']}）"))
    for x in unknown:
        indep.append(("unknown", f"{agent}: 入力が記録の上限（{TRACE_CUT} 字）で切れ、どこに触れたかを決められない（#{x['n']}）"))
    if not indep and shared:
        roots = {x["key"]: x["root"] for x in shared}  # 上下の場所が両方あれば、下だけを書く
        places = "、".join(short_out(r) for k, r in roots.items() if not any(o != k and o.startswith(k + "/") for o in roots))
        indep.append(("warn", f"{agent}: 外では自分が作った {places} の中だけを使い、ほかのエージェントは同じ場所に触れていない。"
                              "ただし、ほかのエージェントからも見える場所にある"))
    if not indep:
        indep.append(("good", f"{agent}: 外で読んだのは、Claude Code が返した自分の出力のファイルだけ"))
    test = []
    if skill_files:
        test.append(("bad", f"{agent}: 作るスキルのファイルを外に書いた（#{'・#'.join(str(x['n']) for x in skill_files)}）"))
    if writes or runs:
        failed = sorted({x["n"] for x in writes + runs if x["a"]["ok"] is False})
        left = [r for r in dict.fromkeys(x["root"] for x in writes if not x["hidden"]) if out_exists(r)]
        test.append(("warn", f"{agent}: 外での書き込み・削除 {len({x['n'] for x in writes})} 回"
                     + (f"と実行 {len({x['n'] for x in runs})} 回" if runs else "")
                     + "は、収束テストの測定（作業ディレクトリの中で変わったファイル）に入らない"
                     + (f"。うち #{'・#'.join(map(str, failed))} は失敗した" if failed else "")
                     + (f"。{'、'.join(short_out(r) for r in left)} は今も残っている" if left else "")))
    if not test:
        test.append(("good", f"{agent}: 外は読んだだけで、測定に入らない書き込みは無い"))
    return indep, test


def out_exists(root: str) -> bool:
    try:
        return not root.startswith("$") and Path(root).exists()
    except OSError:
        return False


def short_out(path: str) -> str:
    """長い外のパスの、セッションやプロジェクトの名前の部分を縮める。"""
    path = re.sub(r"(/tmp/claude-\d+/)[^/]+/([0-9a-f]{8})[0-9a-f-]*", r"\1…/\2…", path)
    path = re.sub(r"(/\.claude/projects/)[^/]+/([0-9a-f]{8})[0-9a-f-]*", r"\1…/\2…", path)
    return re.sub(r"^/(?:private/)?var/folders/[^/]+/[^/]+/T(?=/|$)", "$TMPDIR", path)


OUT_PLACE_INFO = [(k, (label, cause, shared)) for k, _, label, cause, shared in OUT_PLACES] + [("project", PROJECT_PLACE)]
OUT_RULES = ("<li><b>独立しているか</b><ul><li>✕ 同じラウンドのほかのエージェントも同じ外の場所に触れた。または、自分が作っていない外のものを読んだ・実行した・消した</li>"
             "<li>？ 記録の入力が切れていて、触れた場所を決められない</li>"
             "<li>▲ 外では自分が作った場所だけを使ったが、そこはほかのエージェントからも見える</li>"
             "<li>✓ 外で読んだのは、Claude Code が返した自分の出力のファイルだけ</li></ul></li>"
             "<li><b>測定にもれがないか</b><ul><li>✕ 作るスキルのファイルを外に書いた</li>"
             "<li>▲ 外で書いた・消した・実行した（収束テストの測定に入らない）</li><li>✓ 外は読んだだけ</li></ul></li>"
             "<li>「自分が作った」は、その場所（またはその上下の場所）に、同じエージェントが先に書いたこと。"
             "「今も残っている」は、カタログを作った時点でその場所があること</li>")


def outside_card(members: list[tuple[str, dict]], round_runs: dict, task: str, project: str) -> str:
    """課題の依頼文の下に置く、作業ディレクトリの外に触れた操作の原因と、独立性・テスト性の判断。"""
    per = [(agent, outside_touches(run, project)) for agent, run in members]
    per = [(agent, ts) for agent, ts in per if ts]
    fenced = [(agent, n, a) for agent, run in members for n, a in enumerate(run["actions"], 1) if a["fenced"]]
    stopped = ""
    if fenced:
        who = "・".join(f"{agent} {sum(1 for a2, _, _ in fenced if a2 == agent)} 回" for agent in dict.fromkeys(a for a, _, _ in fenced))
        ops = [f'<code title="{esc(a["input"][:300])}">{esc(agent)} #{n} {esc(KINDS[a["kind"]])} '
               f'{esc((OUTSIDE.findall(a["input"]) or [a["label"]])[0][:48])}</code>' for agent, n, a in fenced]
        stopped = (f'<div class="ob-p"><div class="ob-ph"><b>{term("fence", "外への操作を止めた記録")}（fence.py）</b><span>{esc(who)}</span></div>'
                   '<p><span class="ob-k">原因</span>作業ディレクトリの外のパスに触れようとしたか、決まりに沿わない形で道具を呼んだ。'
                   'fence.py が止め、エージェントには止めた理由が返った。止めた操作は外に触れていないので、上の2つの判断には入れない</p>'
                   f'<p class="ob-ops"><span class="ob-k">止めたこと</span>{"".join(ops[:10])}'
                   + (f'<span class="muted">ほか {len(ops) - 10} 件</span>' if len(ops) > 10 else "") + "</p></div>")
    if not per:
        if not fenced:
            return ""
        return (f'<section class="ob" aria-label="作業ディレクトリの外に触れた操作"><h4 class="ob-t">作業ディレクトリの外に触れた操作'
                f'<span class="ob-n">{esc(f"外に触れた印 0 回・止めた操作 {len(fenced)} 回")}</span></h4>{stopped}</section>')
    keys = [(rid, x["key"]) for rid, run in round_runs.items() for x in outside_touches(run, project)
            if x["kind"] != "tool-results" and not x["cut"]]
    judged = [(agent, *out_judge(agent, ts, [(rid, k) for rid, k in keys if rid != f"{task}/{agent}"])) for agent, ts in per]
    order = list(LEVELS)
    boxes = []
    for title, ask, idx in (("独立しているか", "ほかのエージェントや作成の経緯と、外を通して影響し合っていないか", 1),
                            ("測定にもれがないか", "収束テストの測定（作業ディレクトリの中で変わったファイル）が、したことを捉えているか", 2)):
        items = [item for row in judged for item in row[idx]]
        level = max((lv for lv, _ in items), key=order.index)
        boxes.append(f'<div class="ob-v ob-{level}"><div class="ob-vh"><span>{title}</span><b>{LEVELS[level]}</b></div>'
                     f'<p class="ob-q">{ask}</p><ul>' + "".join(f"<li>{esc(text)}</li>" for _, text in items) + "</ul></div>")
    places = []
    info = dict(OUT_PLACE_INFO)
    for kind in dict.fromkeys(x["kind"] for _, ts in per for x in ts):
        label, cause, _ = info[kind]
        rows = [(agent, x) for agent, ts in per for x in ts if x["kind"] == kind]
        roots = list(dict.fromkeys(x["root"] for _, x in rows))
        who = "・".join(f"{agent} {len({x['n'] for a2, x in rows if a2 == agent})} 回" for agent in dict.fromkeys(a for a, _ in rows))
        ops = []
        for agent, x in rows:
            what = x["a"]["label"][:60] if x["hidden"] else (x["path"][len(x["root"]):].lstrip("/") or x["root"].rsplit("/", 1)[-1])
            ops.append(f'<code title="{esc(x["a"]["input"][:300])}">{esc(agent)} #{x["n"]} {esc(x["verb"])} {esc(what[:48])}'
                       + ("（入力にパスが無い）" if x["hidden"] else "") + ("（記録が切れている）" if x["cut"] else "")
                       + ("（失敗）" if x["a"]["ok"] is False else "") + "</code>")
        ops = list(dict.fromkeys(ops))
        places.append(f'<div class="ob-p"><div class="ob-ph"><b>{esc(label)}</b><span>{esc(who)}</span></div>'
                      + "".join(f'<code class="ob-path" title="{esc(r)}">{esc(short_out(r))}</code>' for r in roots)
                      + f'<p><span class="ob-k">原因</span>{esc(cause)}</p>'
                      + f'<p class="ob-ops"><span class="ob-k">したこと</span>{"".join(ops[:10])}'
                      + (f'<span class="muted">ほか {len(ops) - 10} 件</span>' if len(ops) > 10 else "") + "</p></div>")
    visible = sum(len({x["n"] for x in ts if not x["hidden"]}) for _, ts in per)
    hidden = sum(len({x["n"] for x in ts if x["hidden"]}) for _, ts in per)
    count = (f"外に触れた印 {visible} 回" + (f"・入力にパスが無い外への書き込み {hidden} 回" if hidden else "") + f"・{len(per)} 人"
             + (f"・止めた操作 {len(fenced)} 回" if fenced else ""))
    return (f'<section class="ob" aria-label="作業ディレクトリの外に触れた操作"><h4 class="ob-t">作業ディレクトリの外に触れた操作'
            f'<span class="ob-n">{esc(count)}</span></h4><div class="ob-vs">{"".join(boxes)}</div>{"".join(places)}{stopped}'
            f'<details class="ob-rule"><summary>判断の決まり</summary><ul>{OUT_RULES}</ul></details></section>')


FIT_NAMES = {"ok": ("✓", "要る"), "detour": ("↷", "寄り道"), "waste": ("◌", "無駄"), "wrong": ("✕", "誤り")}  # AI の推定の、操作の当てはまり
VERDICT_NAMES = {"good": ("ok", "妥当"), "fair": ("warn", "寄り道・無駄あり"), "poor": ("bad", "見直しが要る")}  # 流れの評価（札の色, 名前）
MATCH_MARKS = {"step": "✓", "doc": "✓", "side": "◇", "back": "↩", "off": "・"}  # 手順との照合の印
OUT_SHOW = 300  # 操作の一覧に出す出力の字数（記録には convergence.py の trace が先頭と末尾を残す）


def is_manual(action: dict) -> bool:
    """スキルの手順書（SKILL.md）を読む操作。手順のどこにも書かれないが、手順を知るための操作。"""
    return action["kind"] == "read" and any(f == "SKILL.md" or f.endswith("/SKILL.md") for f in action["files"])


def similar(a: dict, b: dict) -> bool:
    if a["kind"] != b["kind"]:
        return False
    if a["commands"] or b["commands"]:
        return a["commands"] == b["commands"]
    return difflib.SequenceMatcher(None, a["label"], b["label"]).ratio() >= 0.6


def retries(acts: list[dict]) -> dict[int, int]:
    """失敗した操作の後、3つ以内にした同じような操作。{やり直した操作の位置: 失敗した操作の位置}"""
    found: dict[int, int] = {}
    for i, a in enumerate(acts):
        if a["ok"] is False:
            j = next((j for j in range(i + 1, min(i + 4, len(acts))) if j not in found and similar(a, acts[j])), None)
            if j is not None:
                found[j] = i
    return found


def match_note(acts: list[dict], i: int) -> tuple[str, str]:
    """操作 i を手順に照らした結果（機械）。(印の種類, 文)"""
    a = acts[i]
    prev = next((b["step"] for b in reversed(acts[:i]) if b["step"] is not None), None)
    if a["hit"] is None:
        if is_manual(a):
            return "doc", "手順書（SKILL.md）を読む"
        return "off", "どの手順にも当たらない" + (f"（手順 {a['step']} の途中）" if a["step"] else "（手順を始める前）")
    if a["step"] is not None and prev is not None and a["step"] < prev:
        return "back", f"手順 {prev} から手順 {a['step']} に戻る"
    if a["hit"] != a["step"]:
        return "side", f"手順 {a['hit']} のファイル（手順 {a['step']} の途中）"
    return "step", f"手順 {a['step']}"


def op_links(text: str, prefix: str, count: int) -> str:
    """AI の文の「#12」を、操作の一覧のその行へのリンクにする。"""
    def link(m: re.Match) -> str:
        n = int(m.group(1))
        return jump(f"{prefix}-{n}", m.group(0)) if 1 <= n <= count else m.group(0)
    return re.sub(r"(?<!&)#(\d+)", link, inline(text))


def flow_facts(run: dict, steps: list[dict]) -> str:
    """流れを手順に照らした事実（機械が数える）。"""
    acts = run["actions"]
    marks = [match_note(acts, i)[0] for i in range(len(acts))]
    seen = {a["step"] for a in acts}
    missed = [s for s in steps if s["no"] not in seen]
    redo, failed = retries(acts), sum(a["ok"] is False for a in acts)
    gates = [str(e.get("event", "")) for e in run.get("events", []) if isinstance(e, dict)]
    rows = [("いた手順の並び", step_seq(acts)),
            ("記録に通った跡が無い手順", "、".join(f'<span title="{esc(step_name(s))}">手順 {s["no"]}</span>' for s in missed) or "なし"),
            ("手順を戻った", f"{marks.count('back')} 回"),
            ("どの手順にも当たらない操作", f"{marks.count('off')} 件"),
            ("失敗した操作", f"{failed} 件" + (f"（うち {len(redo)} 件は、すぐに同じような操作をし直した）" if redo else "")),
            ("チェックポイント（run.py）", " → ".join(esc(g) for g in gates) or "記録なし")]
    return ('<div class="fl-mech"><h4>' + term("match") + "</h4><dl>"
            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl></div>")


def ai_flow(run: dict, prefix: str) -> str:
    """流れの評価（AI の推定）。分析が無いか、記録が取り直された後のものでなければ、そう書く。"""
    ai, head = run.get("analysis"), f'<h4>流れの評価（{term("ai")}）'
    if not ai:
        why = ("記録（traces.json）が取り直された後の分析ではないので出さない。<code>convergence.py analysis-prepare</code> からやり直す"
               if run.get("stale") else "このエージェントの分析は無い。<code>convergence.py analysis-prepare</code> で作る")
        return f'<div class="fl-ai none">{head}</h4><p class="muted">{why}</p></div>'
    flow, count = ai.get("flow", {}), len(run["actions"])
    kind, name = VERDICT_NAMES.get(flow.get("verdict"), ("none", "不明"))
    parts = [f'<div class="fl-ai" id="{prefix}-ai">{head}{badge(kind, name)}</h4><p>{op_links(flow.get("summary", ""), prefix, count)}</p>']
    for key, label in (("issues", "問題だった点"), ("suggestions", "スキルの直し方の案")):
        if flow.get(key):
            parts.append(f"<h5>{label}</h5><ul>" + "".join(f"<li>{op_links(x, prefix, count)}</li>" for x in flow[key]) + "</ul>")
    if ai.get("compare"):
        parts.append(f'<h5>ほかのエージェントとの違い</h5><p>{op_links(ai["compare"], prefix, count)}</p>')
    fits = Counter(o.get("fit") for o in ai.get("ops", []))
    tally = "、".join(f"{FIT_NAMES[k][1]} {fits[k]}" for k in FIT_NAMES if fits[k])
    by = model_list([ai]) or "モデルは記録なし"
    parts.append(f'<p class="by">操作の当てはまり: {esc(tally)}。分析したエージェント: {esc(ai.get("runner", ""))}、{by}</p>')
    return "".join(parts) + "</div>"


def ops_table(acts: list[dict], prefix: str) -> str:
    """操作の一覧。行の id は「prefix-番号」で、「先に見るもの」と AI の文の「#番号」のリンクの飛び先になる。"""
    rows, redo = [], retries(acts)
    for n, a in enumerate(acts, 1):
        cls = ' class="ng"' if a["ok"] is False or a["outside"] else ""
        minute = "—" if a["sec"] is None else format(a["sec"] / 60, ".1f")
        result = []
        if a["ok"] is False:
            result.append('<span class="no">✕ 失敗</span>')
        elif a["ok"]:
            result.append('<span class="yes">✓</span>')
        if a["outside"]:
            result.append('<span class="no">外</span>')
        if a["fenced"]:
            result.append('<span class="no">止めた</span>')
        kind, note = match_note(acts, n - 1)
        match = f'<span class="mt mt-{kind}">{MATCH_MARKS[kind]} {esc(note)}</span>'
        if n - 1 in redo:
            match += f'<span class="mt mt-redo">↻ {jump(f"{prefix}-{redo[n - 1] + 1}", f"#{redo[n - 1] + 1}")} のし直し</span>'
        out = a.get("out", "")
        shown = out if len(out) <= OUT_SHOW else out[:OUT_SHOW] + "…"
        detail = f'<details class="out"><summary>出力</summary><pre>{esc(shown)}</pre></details>' if out else ""
        guess = a.get("ai") or {}
        mark, fit = FIT_NAMES.get(guess.get("fit"), ("", ""))
        why = (f'<span class="fit fit-{esc(guess.get("fit"))}" title="{esc(fit)}">{mark} {esc(fit)}</span> {op_links(guess.get("why", ""), prefix, len(acts))}'
               if guess else '<span class="muted">—</span>')
        rows.append(f'<tr id="{prefix}-{n}"{cls}><td class="num">{n}</td><td class="num">{minute}</td><td><span class="kd kd-{a["kind"]}">{KINDS[a["kind"]]}</span></td>'
                    f'<td><code>{esc(a["label"][:240])}</code>{detail}</td><td class="match">{match}</td>'
                    f'<td>{" ".join(result) or "—"}</td><td class="why">{why}</td></tr>')
    return ('<div class="logbox"><table class="ops"><thead><tr><th class="num">#</th><th class="num">分</th><th>種類</th><th>内容</th>'
            f'<th>{term("match")}</th><th>結果</th><th>理由（{term("ai")}）</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def section_movement(skill: dict) -> str:
    if not skill["moves"]:
        return ('<div class="card empty"><p>収束テストの <code>round-*/traces.json</code> が無い。<code>convergence.py diff</code> が書く。'
                'それより前のラウンドには <code>convergence.py trace</code> で足す。</p></div>')
    messages = {(d.get("round"), t.get("id"), a): t.get("messages", {}).get(a, "")
                for d in skill["rounds"] for t in d.get("tasks", []) for a in t.get("agents", [])}
    statuses = {(d.get("round"), t.get("id"), a): t.get("status", {}).get(a, "")
                for d in skill["rounds"] for t in d.get("tasks", []) for a in t.get("agents", [])}
    group = f"mv-{skill['name']}"
    rounds = sorted(skill["moves"], reverse=True)
    buttons, panes = [], []
    for rnd in rounds:
        runs = skill["moves"][rnd]
        pane_id = f"{group}-r{rnd}"
        buttons.append(f'<button type="button" role="tab" data-for="{esc(group)}" data-show="{esc(pane_id)}">ラウンド {esc(rnd)}'
                       f'<span class="cnt">{len(runs)} 人</span></button>')
        most = max([len(r["actions"]) for r in runs.values()] + [1])
        known = list(skill["tasks"])  # dev/evals.json の課題の順に並べる
        tasks = sorted(dict.fromkeys(rid.split("/", 1)[0] for rid in sorted(runs)), key=lambda x: (known.index(x) if x in known else len(known), x))
        table, cards = [], []
        for task in tasks:
            members = [(rid.split("/", 1)[1], runs[rid]) for rid in sorted(runs) if rid.startswith(task + "/")]
            prompt = str(skill["tasks"].get(task, {}).get("prompt", ""))
            table.append(f'<tr class="grp"><th colspan="10"><span class="tid">{esc(task)}</span><span class="muted">{esc(prompt)}</span></th></tr>')
            logs = []
            for i, (agent, run) in enumerate(members):
                acts = run["actions"]
                counts = Counter(a["kind"] for a in acts)
                failed = sum(a["ok"] is False for a in acts)
                outside = sum(bool(a["outside"]) for a in acts)
                secs = [a["sec"] for a in acts if a["sec"] is not None]
                took = f"{max(secs) / 60:.0f} 分" if secs else "—"
                kinds = "・".join(f"{KINDS[k]} {counts[k]}" for k in KINDS if counts[k]) or "—"
                color = f"s{i % 6 + 1}"
                share = 100 * len(acts) / most
                rid = f"{task}/{agent}"
                prefix = anchor(skill["name"], "op", rnd, rid)
                verdict = (run["analysis"] or {}).get("flow", {}).get("verdict")
                kind, name = VERDICT_NAMES.get(verdict, ("none", "記録が変わった" if run["stale"] else "分析なし"))
                judged = jump(f"{prefix}-ai", badge(kind, name)) if verdict in VERDICT_NAMES else badge(kind, name)
                table.append(f'<tr><td class="who"><span class="sw {color}"></span>{esc(agent)}</td>{model_cell(run)}'
                             f'<td>{status_badge(statuses.get((rnd, task, agent), ""))}</td>'
                             f'<td class="num">{took}</td><td class="num"><span class="opsn">{len(acts)}<span class="bar"><i style="width:{share:.0f}%"></i></span></span></td>'
                             f'<td class="kinds">{esc(kinds)}</td><td class="num">{badge("bad", str(failed)) if failed else "0"}</td>'
                             f'<td class="num">{badge("bad", str(outside)) if outside else "0"}</td><td>{step_seq(acts)}</td><td>{judged}</td></tr>')
                flags = (f' {badge("bad", "失敗 " + str(failed))}' if failed else "") + (f' {badge("bad", "外 " + str(outside))}' if outside else "")
                flags += f" {badge(kind, name)}" if verdict in VERDICT_NAMES else ""
                message = messages.get((rnd, task, agent), "")
                reply = f'<details class="reply"><summary>最終の返答（末尾）</summary><pre>{esc(message)}</pre></details>' if message else ""
                model = model_list([run]) + ("（設定から）" if run.get("settings") else "")
                logs.append(f'<details class="log" id="{anchor(skill["name"], "log", rnd, rid)}"><summary><span class="sw {color}"></span>'
                            f'<b>{esc(agent)}</b>の操作 {len(acts)} 件{flags}' + (f'<span class="mdl-s">{model}</span>' if model else "")
                            + f'<span class="src">{esc(run["source"])}</span></summary>'
                            f'<div class="flow">{flow_facts(run, skill["steps"])}{ai_flow(run, prefix)}</div>{ops_table(acts, prefix)}{reply}</details>')
            agents = "".join(f'<button type="button" class="fk" data-focus="s{i % 6 + 1}" aria-pressed="false">'
                             f'<svg width="26" height="14" viewBox="0 0 26 14" aria-hidden="true">{agent_key(f"s{i % 6 + 1}")}</svg>{esc(agent)}</button>'
                             for i, (agent, _) in enumerate(members))
            uid = f"{skill['name']}-{rnd}-{task}"
            cards.append(f'<article class="card task" data-focus-scope><header><h3>{esc(task)}</h3>' + (f'<p class="prompt">{esc(prompt)}</p>' if prompt else "")
                         + outside_card(members, runs, task, skill["project"])
                         + f'</header><div class="key focus-key">{agents}{MARK_KEYS}</div><div class="scroll">{movement_svg(skill["steps"], members, uid)}</div>'
                         + f'<div class="logs">{"".join(logs)}</div></article>')
        panes.append(f'<div class="pane" id="{esc(pane_id)}" data-pane="{esc(group)}" role="tabpanel">'
                     '<div class="card"><div class="scroll"><table class="mvt"><thead><tr><th>エージェント</th>'
                     f'<th>モデル・{term("effort")}</th><th>結果</th><th class="num">かかった時間</th>'
                     '<th class="num">操作</th><th>内訳</th><th class="num">失敗</th><th class="num">外に触れた</th><th>通った手順の順（↩ は戻り）</th>'
                     f'<th>流れの評価（{term("ai")}）</th></tr></thead>'
                     f'<tbody>{"".join(table)}</tbody></table></div></div>{"".join(cards)}</div>')
    how = ('<details class="howto"><summary>図の読み方</summary><p>行が手順、横が経過時間。エージェントごとの棒は、その手順にいた時間。'
           'エージェントの名前を押すと、その人の棒と印だけを浮かび上がらせる（もう一度押すと戻る）。'
           'コマンドは SKILL.md に書かれた手順に移す（戻りも含む）。読む・書くは、本文にそのパスがある手順へ、前に進むときだけ移す。'
           '操作の記録は、Claude Code の Agent ツールの記録、Codex のサブエージェントの記録、codex exec の出力から集めた'
           '（claude -p で動かしたときは start・check・finish の時刻だけ）。'
           'モデルと推論エフォートは、Claude Code はサブエージェントの記録か claude -p の出力から、Codex はサブエージェントの記録か、'
           'codex exec のコマンドの -m・-c、無ければ ~/.codex/config.toml から読む（設定から読んだものには「設定から」と付ける）。'
           '棒と点に重ねると、操作の中身が出る。印（スクリプトの実行・失敗・外に触れた操作）は、コマンドの全文、結果、手順、外のパス、'
           '失敗の後の操作を出し、クリックかタップで固定できる（Esc で閉じる）。'
           'エージェントの名前の行を開くと、操作の一覧と、流れの見立てが出る。「手順との照合」は機械が各操作を手順に当てたもの、'
           '「理由」と「流れの評価」は、別の AI が記録（操作の入力・出力・成否と手順）から推し量ったもの（convergence.py analysis-prepare・'
           'analysis-collect が作る）。エージェント自身の考えは記録に残らないので、推定であって、本人の理由ではない。'
           'AI の文の「#12」は、その操作の行へのリンク。</p></details>')
    return (f'<div class="bar-row"><div class="seg" role="tablist" aria-label="ラウンド">{"".join(buttons)}</div>{how}</div>'
            + "".join(panes))


# ---------------------------------------------------------------- HTML の部品

PREFIX_NAMES = {"TRG": "起動", "IN": "入力", "STEP": "手順", "OUT": "出力", "RPT": "報告", "CTL": "制御"}
GROUP_NAMES = {"machine": "機械が確かめる", "tool": "スクリプト・ひな形", "human": "レビュー・文書だけ"}
TABS = [("workflow", "ワークフロー"), ("movement", "エージェントの動き"), ("convergence", "収束テスト"),
        ("decisions", "ルールと出力の決まり"), ("probes", "検査が働くか"), ("state", "最後の実行")]
# 見せる用語の表。ページの言葉はここから出し、名前に重ねると説明が出る（見せ方の約束 1）
TERMS = {
    "seal": ("改変チェック", "検証に合格したときの、SKILL.md・scripts・assets・references の中身の指紋（assets/seal.json）と、"
                         "今のファイルを見比べる。合格した後に書き換わっていると、次の run.py start が止まる。"
                         "直して合格し直したら skill_lint.py --final --seal で記録し直す。"),
    "probe": ("違反の見本", "わざとルールを破った見本（dev/probes.json）を、ルールの検査が見つけて止めるかを probe.py で確かめる。"),
    "wiring": ("hooks の動作", "hooks が製品の設定に登録され、スキルの実行中は働き、実行していないときは何もしないかを probe.py で確かめる。"),
    "convergence": ("収束テスト", "これまでの会話を持たない別のエージェント数人に同じ課題を解かせ、作ったものがどれだけ揃うかを 0〜1 で測る。"
                              "基準を満たせば、誰が使っても同じ結果になるとみなす。"),
    "control": ("守らせ方", "ルールを何で守らせるか。実行時に止める・自動で直す・検査で止める は機械が守らせる。"
                        "スクリプトが出す・ひな形を写す は道具が助ける。完了前に見直す・文書で伝える は AI や人が守る。"),
    "basis": ("決めた根拠", "答えがいくつも考えられるルールで、その答えにしたわけ。依頼の指定 → 後付けする既存のスキルの書き方 → "
                        "プロジェクトの決まり → 公式の決まり → 機械で守らせられる答え → 道具を増やさない答え → 判断の少ない答え → "
                        "最も普及している答え の順に当てはめ、最初に当たったものを書く。"),
    "gate": ("チェックポイント", "run.py start・check・finish。手順の区切りでスクリプトが状態と出力を確かめ、満たさなければ先へ進ませない。"),
    "fence": ("外への操作の停止", "fence.py が、作業ディレクトリの外のパスに触れる操作などを、実行の前に止める。"
                              "止めた操作は外に触れていないので、外に触れた数には入れない。"),
    "runner": ("動かし方", "収束テストのエージェントを何で動かしたか。claude は claude -p、codex は codex exec、"
                       "subagent は会話の中のサブエージェント。"),
    "back": ("実際の戻り", "最後のラウンドの記録で、エージェントが前の手順に実際に戻ったところ。SKILL.md の文にある「手順Nに戻る」とは別に数える。"),
    "effort": ("推論エフォート", "モデルが答える前にどれだけ考えるかの設定（low・medium・high・xhigh など）。"),
    "match": ("手順との照合", "各操作を SKILL.md の手順に機械で当てたもの。コマンドは書かれた手順へ、読む・書くは本文にそのパスがある手順へ当てる。"
                           "✓ 手順どおり、↩ 前の手順に戻った、◇ 途中で別の手順のファイルに触れた、・ どの手順にも当たらない、"
                           "↻ 失敗の直後に同じような操作をし直した。"),
    "ai": ("AI の推定", "エージェント自身の考えは記録に残らない（Codex は暗号化され、Claude Code は空になる）。そこで別の AI が、"
                      "操作の入力・出力・成否と手順を突き合わせて推し量った。本人の理由ではなく、外れることもある。"
                      "当てはまりは、✓ 要る・↷ 寄り道（害は無い）・◌ 無駄・✕ 誤り。"),
}
LEVEL_NAMES = {"runtime": "実行時に止める", "format": "自動で直す", "validate": "検査で止める", "script": "スクリプトが出す",
               "template": "ひな形を写す", "review": "完了前に見直す", "doc": "文書で伝える"}
STATUS_NAMES = {"done": "完了", "failed": "失敗", "aborted": "中断", "unused": "始めなかった"}
METRIC_NAMES = {"files": "ファイルの揃い", "structure": "骨格の揃い", "names": "名前の揃い", "content": "中身の揃い"}


def term(key: str, label: str = "") -> str:
    """用語の表の語。重ねるか押すと、その場で説明を出す。"""
    name, text = TERMS[key]
    return f'<span class="term" tabindex="0" data-pop="{esc(f"<b>{esc(name)}</b><br>{esc(text)}")}">{esc(label or name)}</span>'


def anchor(*parts) -> str:
    """飛び先の id。「先に見るもの」のリンクは、この id の行や操作へ直接飛ぶ（見せ方の約束 3）。"""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", "-".join(str(p) for p in parts))


def inline(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(text))


def markdown(text: str) -> str:
    """「結論」の節を表示する。段落、「- 」の箇条書き、表だけを扱う。"""
    out, para, items, table = [], [], [], []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()
        if table:
            rows = [r for r in table if not re.fullmatch(r"\|[\s:|-]+\|", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            head = "".join(f"<th>{inline(c)}</th>" for c in cells[0]) if cells else ""
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
            out.append(f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            table.clear()

    for line in text.strip().splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("|"):
            if para or items:
                flush()
            table.append(s)
        elif s.startswith(("- ", "* ")):
            if para or table:
                flush()
            items.append(s[2:])
        else:
            if items or table:
                flush()
            para.append(s)
    flush()
    return "".join(out)


def badge(kind: str, text: str) -> str:
    return f'<span class="st st-{kind}"><i aria-hidden="true"></i>{esc(text)}</span>'


def fmt(value) -> str:
    return "—" if not isinstance(value, (int, float)) else f"{value:.3f}"


def thresholds(skill: dict) -> dict:
    rounds = skill["rounds"]
    return {"files": 1.0, "structure": 1.0, "names": 0.8, **(rounds[-1].get("thresholds", {}) if rounds else {})}


def summary(skill: dict) -> dict:
    """見出しの数字と状態。kind は ok・warn・bad・none。"""
    probes = skill["probes"] or {}
    results, wiring = probes.get("results", []), probes.get("wiring", [])
    p_fail = [r for r in results if not r.get("passed")]
    w_fail = [w for w in wiring if not w.get("passed")]
    skip = str(skill["spec"].get("convergence", {}).get("skip_reason") or "").strip()
    tasks = skill["rounds"][-1].get("tasks", []) if skill["rounds"] else []
    ok = sum(bool(x.get("converged")) for x in tasks)
    if skip:
        conv = ("none", "省いた")
    elif not tasks:
        conv = ("none", "結果なし")
    else:
        conv = ("ok" if ok == len(tasks) else "warn", "満たす" if ok == len(tasks) else "要確認")
    return {"results": results, "wiring": wiring, "p_fail": p_fail, "w_fail": w_fail, "skip": skip, "tasks": tasks, "ok": ok,
            "probe": ("none", "結果なし") if not results else ("bad", "失敗あり") if p_fail else ("ok", "成功"),
            "wire": ("none", "結果なし") if not wiring else ("bad", "失敗あり") if w_fail else ("ok", "成功"),
            "conv": conv, "seal": skill["seal"], "round": skill["rounds"][-1].get("round") if skill["rounds"] else None}


def meter(parts: list[tuple[int, str]]) -> str:
    total = sum(v for v, _ in parts)
    if not total:
        return '<span class="meter"></span>'
    return '<span class="meter">' + "".join(f'<i class="{cls}" style="flex:{v}"></i>' for v, cls in parts if v) + "</span>"


def tiles(skill: dict, sm: dict) -> str:
    name = skill["name"]
    n = len(skill["decisions"])
    machine = sum(any(lv in _lib.MACHINE for lv in d.get("control", [])) for d in skill["decisions"].values())

    def tile(tab, label, value, sub, state, bar):
        top = f'<span class="tile-k">{label}</span>' + (badge(*state) if state else "")
        return (f'<a class="tile" href="#skill-{esc(name)}-{tab}"><span class="tile-top">{top}</span><span class="tile-v">{value}</span>'
                f'{bar}<span class="tile-s">{sub}</span></a>')

    def ratio(a, b):
        return dot_text([(str(a), "dm-on"), (f"/{b}", "dm-dim")]) if b else '<span class="tile-word">—</span>'

    results, wiring = sm["results"], sm["wiring"]
    seal_kind, seal_text = sm["seal"]
    seal_value = {"ok": "変更なし", "bad": "変更あり", "none": "記録なし"}.get(seal_kind, "—")
    conv_sub = ("理由: " + esc(sm["skip"])) if sm["skip"] else (f"R{esc(sm['round'])} で基準を満たした課題" if sm["tasks"] else "収束テストの記録が無い")
    shown = bool(sm["tasks"]) and not sm["skip"]
    return '<div class="tiles">' + "".join([
        tile("decisions", "ルール", dot_text([(str(n), "dm-on")]), f"機械が確かめる {machine}・人が守る {n - machine}", None,
             meter([(machine, "acc"), (n - machine, "mute")])),
        tile("probes", "違反の検出", ratio(len(results) - len(sm["p_fail"]), len(results)), "わざと破った見本を検査が止めた数（組み込みの検査を含む）",
             sm["probe"], meter([(len(results) - len(sm["p_fail"]), "good"), (len(sm["p_fail"]), "crit")])),
        tile("probes", "hooks の動作", ratio(len(wiring) - len(sm["w_fail"]), len(wiring)), "実行中は働き、実行していないときは何もしないか", sm["wire"],
             meter([(len(wiring) - len(sm["w_fail"]), "good"), (len(sm["w_fail"]), "crit")])),
        tile("convergence", "収束テスト", ratio(sm["ok"], len(sm["tasks"])) if shown else '<span class="tile-word">—</span>', conv_sub, sm["conv"],
             meter([(sm["ok"], "good"), (len(sm["tasks"]) - sm["ok"], "warn")]) if shown else meter([])),
        tile("state", "改変チェック", f'<span class="tile-word">{seal_value}</span>',
             esc(seal_text) + (f"・見比べたファイル {skill['seal_files']} 件" if skill["seal_files"] else ""),
             ({"ok": ("ok", "一致"), "bad": ("bad", "要確認"), "none": ("warn", "なし")}.get(seal_kind, ("none", "—"))),
             meter([(1, {"ok": "good", "bad": "crit"}[seal_kind])] if seal_kind in ("ok", "bad") else [])),
    ]) + "</div>"


ATTN_LEVELS = {"crit": "要対応", "warn": "要確認", "info": "参考"}


def jump(target: str, label: str) -> str:
    return f'<a href="#{esc(target)}" class="jump">{label}</a>'


def first_op(run: dict, hit) -> int:
    """hit に当たる最初の操作の番号（操作の一覧の # と同じ）。"""
    return next(n for n, a in enumerate(run["actions"], 1) if hit(a))


def attention_items(skill: dict, sm: dict) -> list[tuple[str, str, str, str]]:
    """先に見てほしいもの。(重さ, 文, 飛び先の場所の名前, 飛び先の id) を重さの順（要対応 → 要確認 → 参考）に。
    文の中の ID・課題・エージェントも、それぞれの行や操作へのリンクにする。"""
    name, items = skill["name"], []
    tabs = dict(TABS)
    if sm["p_fail"]:
        shown = sm["p_fail"][:6]
        ids = "、".join(jump(anchor(name, "probe", r.get("id", "")), f'<code>{esc(r.get("id", ""))}</code>') for r in shown)
        items.append(("crit", f"違反の見本 {len(sm['p_fail'])} 件を検査が止められなかった（{ids}{'…' if len(sm['p_fail']) > 6 else ''}）",
                      f"{tabs['probes']} › {esc(shown[0].get('id', ''))} の行", anchor(name, "probe", shown[0].get("id", ""))))
    if sm["w_fail"]:
        w = sm["w_fail"][0]
        items.append(("crit", f"hooks の動作の確認 {len(sm['w_fail'])} 件が失敗した",
                      f"{tabs['probes']} › hooks の動作 › {esc(w.get('check', ''))}", anchor(name, "wire", w.get("platform", ""), w.get("check", ""))))
    if sm["seal"][0] == "bad":
        items.append(("crit", "改変チェック: " + esc(sm["seal"][1]) + "。次の run.py start が止まる"
                      "（直して合格し直したら <code>skill_lint.py --final --seal</code> で記録し直す）",
                      f"{tabs['state']} › 改変チェック", anchor(name, "seal")))
    elif sm["seal"][0] == "none":
        items.append(("warn", "改変チェックの記録（合格時のファイルの指紋）が無い（<code>skill_lint.py --final --seal</code> で記録する）",
                      f"{tabs['state']} › 改変チェック", anchor(name, "seal")))
    if skill.get("twins"):
        items.append(("warn", "同じ名前のスキルが別の場所にもある（" + "、".join(f"<code>{esc(p)}</code>" for p in skill["twins"])
                      + "）。中身を確かめて外し、本体の <code>install.py --project .</code> でリンクにする"
                        "（<code>--mode copy</code> で置いた複製なら、このままでよい）", "ページの上 › 置き場", anchor(name, "place")))
    th = thresholds(skill)
    if sm["tasks"] and not sm["skip"]:
        misses = []
        for task in sm["tasks"]:
            if task.get("converged"):
                continue
            low = [f"{METRIC_NAMES[k]} {task[k]:.2f}" for k in ("files", "structure", "names")
                   if isinstance(task.get(k), (int, float)) and task[k] < float(th.get(k, 1.0))]
            misses.append((task.get("id", ""), jump(anchor(name, "conv", sm["round"], task.get("id", "")), f"<b>{esc(task.get('id', ''))}</b>")
                           + (f"（{'・'.join(low)}）" if low else "")))
        if misses:
            items.append(("warn", f"収束テスト R{esc(sm['round'])} で結果が揃わなかった課題 {len(misses)} 件: " + "、".join(m for _, m in misses),
                          f"{tabs['convergence']} › R{esc(sm['round'])} › {esc(misses[0][0])} の行", anchor(name, "conv", sm["round"], misses[0][0])))
    moves, rnd = last_moves(skill), sm["round"]
    for key, level, lead, hit in (("outside", "warn", "作業ディレクトリの外に触れたエージェント", lambda a: bool(a["outside"])),
                                  ("failed", "info", "失敗した操作のあるエージェント", lambda a: a["ok"] is False)):
        found = [(rid, run, sum(bool(hit(a)) for a in run["actions"])) for rid, run in sorted(moves.items())]
        found = [(rid, first_op(run, hit), n) for rid, run, n in found if n]
        if found:
            links = "、".join(jump(anchor(name, "op", rnd, rid, k), f"<b>{esc(rid)}</b>") + f"（{n} 回）" for rid, k, n in found)
            rid, k, _ = found[0]
            items.append((level, f"{lead}: {links}", f"{tabs['movement']} › R{esc(rnd)} › {esc(rid)} の操作 #{k}", anchor(name, "op", rnd, rid, k)))
    judged = [(rid, run["analysis"]["flow"]) for rid, run in sorted(moves.items()) if run.get("analysis")]
    poor = [rid for rid, flow in judged if flow.get("verdict") == "poor"]
    if poor:
        links = "、".join(jump(anchor(name, "op", rnd, rid, "ai"), f"<b>{esc(rid)}</b>") for rid in poor)
        items.append(("warn", f"流れに見直しが要る（{term('ai')}）エージェント: {links}",
                      f"{tabs['movement']} › R{esc(rnd)} › {esc(poor[0])} の流れの評価", anchor(name, "op", rnd, poor[0], "ai")))
    missing = [rid for rid, run in sorted(moves.items()) if run["actions"] and not run.get("analysis")]
    if missing:
        items.append(("info", f"R{esc(rnd)} の {len(missing)} 人の記録に、AI の分析が無いか、記録が取り直された後の分析ではない"
                      "（<code>convergence.py analysis-prepare</code> で作り直す）",
                      f"{tabs['movement']} › R{esc(rnd)} › {esc(missing[0])}", anchor(name, "log", rnd, missing[0])))
    stats = skill["gates"]
    if stats and stats["reached"]["finish"] < stats["agents"]:
        finish = next((s["no"] for s in reversed(skill["steps"]) if "finish" in s["gates"]), None)
        items.append(("warn", f"finish まで通ったのは {stats['reached']['finish']}/{stats['agents']} 人",
                      f"{tabs['workflow']} › 手順 {finish}" if finish else tabs["workflow"],
                      anchor(name, "wf", finish) if finish else f"skill-{name}-workflow"))
    return items


def attention(skill: dict, sm: dict) -> str:
    """先に見てほしいものを、対象の行や操作へのリンクを付けて並べる。"""
    items = attention_items(skill, sm)
    if not items:
        return ('<section class="attn" aria-label="要点"><h3>先に見るもの</h3><ul><li class="good"><span class="pt"></span>'
                '<div><span class="lvl">問題なし</span>違反の検出・hooks の動作・改変チェック・収束テストに、先に見るべきものは無い。</div></li></ul></section>')
    rows = "".join(f'<li class="{lv}"><span class="pt"></span><div><span class="lvl">{ATTN_LEVELS[lv]}</span>{text}</div>'
                   f'<div class="go">└ {jump(target, where + " へ")}</div></li>' for lv, text, where, target in items)
    return f'<section class="attn" aria-label="要点"><h3>先に見るもの</h3><ul>{rows}</ul></section>'


def section_decisions(skill: dict) -> str:
    uses: dict = {}
    for step in skill["steps"]:
        for rid in step["ids"]:
            uses.setdefault(rid, []).append(step["no"])
    table_id = f"dec-{skill['name']}"
    groups = Counter(decision_group(d) for d in skill["decisions"].values())
    buttons = [f'<button type="button" data-filter="all" aria-pressed="true">すべて<span class="cnt">{len(skill["decisions"])}</span></button>']
    buttons += [f'<button type="button" data-filter="{g}" aria-pressed="false"><span class="lv lv-{g}">ID</span>{GROUP_NAMES[g]}'
                f'<span class="cnt">{groups[g]}</span></button>' for g in GROUP_NAMES if groups[g]]
    order = _lib.PREFIXES + sorted({rid.split("-")[0] for rid in skill["decisions"]} - set(_lib.PREFIXES))
    rows = []
    for prefix in order:
        members = [(rid, d) for rid, d in skill["decisions"].items() if rid.split("-")[0] == prefix]
        if not members:
            continue
        rows.append(f'<tr class="grp"><th colspan="6">{esc(prefix)}<span class="muted">{PREFIX_NAMES.get(prefix, "")}・{len(members)} 件</span></th></tr>')
        for rid, d in members:
            levels = "".join(f'<span class="lv lv-{GROUP.get(lv, "human")}" title="{esc(lv)}">{esc(LEVEL_NAMES.get(lv, lv))}</span>'
                             for lv in d.get("control", []))
            check = skill["checks"].get(rid, {})
            verified = []
            if check.get("total"):
                failed = check["total"] - check["passed"]
                verified.append(badge("bad" if failed else "ok", f"probe {check['passed']}/{check['total']}"))
            if check.get("review") is not None:
                verified.append(badge("ok" if check["review"] >= 1 else "warn", f"レビュー {check['review']:.2f}"))
            detail = f"<p>{inline(d.get('decision', ''))}</p>"
            if d.get("how"):
                detail += f'<p><span class="k">守らせる仕組み</span>{inline(d["how"])}</p>'
            if d.get("why_not_machine"):
                detail += f'<p><span class="k">機械にしない理由</span>{inline(d["why_not_machine"])}</p>'
            basis = _lib.BASES.get(d.get("basis"), (d.get("basis") or "—",))[0]
            steps = "".join(f'<span class="sq">{n}</span>' for n in uses.get(rid, [])) or '<span class="muted">—</span>'
            rows.append(f'<tr data-group="{decision_group(d)}"><td><code class="rid">{esc(rid)}</code></td>'
                        f'<td><details class="dd"><summary>{inline(d.get("title", ""))}</summary>{detail}</details></td>'
                        f'<td>{levels}</td><td class="basis">{esc(basis)}</td><td>{"".join(verified) or "—"}</td><td><span class="seq">{steps}</span></td></tr>')
    return (f'<div class="card"><div class="card-head"><h3>ルールと守らせ方</h3><div class="seg seg-sm" data-filter-for="{esc(table_id)}">{"".join(buttons)}</div></div>'
            '<p class="lead">dev/spec.json のルール。題をクリックすると、ルールの全文と守らせる仕組みが開く。'
            f'{term("control")}は、ルールを何で守らせるか（色の付いたものは機械が守らせる）。{term("basis")}は、ほかの答えもあり得るときに、その答えにしたわけ。'
            '点線の付いた語に重ねると説明が出る。</p>'
            f'<div class="scroll"><table class="dec" id="{esc(table_id)}"><thead><tr><th>ID</th><th>ルール</th><th>{term("control")}</th><th>{term("basis")}</th>'
            f'<th>検証</th><th>使う手順</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></div>')


def section_outputs(skill: dict) -> str:
    rows = []
    for o in skill["contract"].get("outputs", skill["spec"].get("outputs", [])):
        count = o.get("count", {})
        checks = "".join(f'<li><code>{esc(c.get("rule", ""))}</code> {esc(c.get("type", ""))}'
                         + (f'<span class="muted">（{esc(c["stage"])} のとき）</span>' if c.get("stage") else "") + "</li>" for c in o.get("checks", []))
        rows.append(f'<tr><td><code class="rid">{esc(o.get("id", ""))}</code><div class="muted">{esc(o.get("label", ""))}</div></td>'
                    f'<td><code>{esc(o.get("path", ""))}</code></td><td class="num">{esc(count.get("min", "—"))}〜{esc(count.get("max", "—"))}</td>'
                    f'<td><ul class="plain">{checks}</ul></td></tr>')
    body = (f'<div class="scroll"><table><thead><tr><th>出力</th><th>置き場</th><th class="num">件数</th><th>検査（ルールID）</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>') if rows else '<p class="muted">契約に出力が無い。</p>'
    return ('<div class="card"><h3>出力の決まり</h3><p class="lead">assets/contract.json に書いた出力。hooks と finish が、置き場・件数・検査を確かめる。</p>'
            f"{body}</div>")


def section_probes(skill: dict, sm: dict) -> str:
    probes = skill["probes"]
    if not probes:
        return '<div class="card empty"><p><code>dev/results/probe-results.json</code> が無い（probe.py を実行していない）。</p></div>'
    results = sorted(probes.get("results", []), key=lambda r: bool(r.get("passed")))
    passed = len(results) - len(sm["p_fail"])
    rows = []
    for r in results:
        ok = bool(r.get("passed"))
        rows.append(f'<tr id="{anchor(skill["name"], "probe", r.get("id", ""))}"' + ("" if ok else ' class="ng"') + ">"
                    f'<td>{badge("ok" if ok else "bad", "止めた" if ok else "止められなかった")}</td>'
                    f'<td><code class="rid">{esc(r.get("id", ""))}</code></td><td>{inline(r.get("detail", ""))}</td></tr>')
    rows = "".join(rows)
    wiring = probes.get("wiring", [])
    platforms = list(dict.fromkeys(w.get("platform", "") for w in wiring))
    names = list(dict.fromkeys(w.get("check", "") for w in wiring))
    cell = {(w.get("platform", ""), w.get("check", "")): w for w in wiring}
    matrix = []
    for check in names:
        tds = []
        for p in platforms:
            w = cell.get((p, check))
            if w is None:
                tds.append('<td class="muted">—</td>')
                continue
            mark = '<span class="yes">✓</span>' if w.get("passed") else '<span class="no">✕</span>'
            tds.append(f'<td id="{anchor(skill["name"], "wire", p, check)}">{mark} <span class="muted">{inline(w.get("detail", ""))}</span></td>')
        matrix.append(f'<tr><td><code>{esc(check)}</code></td>{"".join(tds)}</tr>')
    heads = "".join(f"<th>{esc(report_skill.PRODUCTS.get(p, p))}</th>" for p in platforms)
    wire_html = (f'<div class="card"><h3>hooks の動作</h3><p class="lead">probe.py が、hooks が製品の設定に登録され、スキルの実行中は働き、'
                 '実行していないときは何もしないかを、製品ごとに確かめた結果。</p>'
                 f'<div class="scroll"><table class="wire"><thead><tr><th>検査</th>{heads}</tr></thead><tbody>{"".join(matrix)}</tbody></table></div></div>') if wiring else ""
    big = dot_text([(str(passed), "dm-on"), (f"/{len(results)}", "dm-dim")], pitch=3.6)
    return (f'<div class="card"><div class="card-head"><h3>違反を見つけて止めるか</h3><span class="big">{big}<small>止めた</small></span></div>'
            f'{meter([(passed, "good"), (len(sm["p_fail"]), "crit")])}'
            f'<p class="lead">わざとルールを破った{term("probe")}（dev/probes.json）を、ルールの検査が止めるかを probe.py が確かめた結果。'
            'ID に builtin が付くものは、スキルに組み込みの検査（start・finish などの止め方）。止められなかったものが先に並ぶ。</p>'
            f'<details class="more"{" open" if sm["p_fail"] else ""}><summary>{len(results)} 件を見る</summary><div class="scroll"><table><thead><tr><th>結果</th>'
            f'<th>ID</th><th>内容</th></tr></thead><tbody>{rows}</tbody></table></div></details></div>{wire_html}')


def metric_cell(value, threshold: float) -> str:
    if not isinstance(value, (int, float)):
        return '<td class="num muted">—</td>'
    state = "hi" if value >= threshold else "lo"
    return (f'<td class="num"><span class="mcell">{value:.3f}<span class="mbar"><i class="{state}" style="width:{100 * min(value, 1):.0f}%"></i>'
            f'<b style="left:{100 * min(threshold, 1):.0f}%"></b></span></span></td>')


def section_convergence(skill: dict, sm: dict) -> str:
    if sm["skip"]:
        return f'<div class="card empty"><p>{badge("none", "実施していない")} 理由: {inline(sm["skip"])}</p></div>'
    rounds = skill["rounds"]
    if not rounds:
        return '<div class="card empty"><p><code>dev/results/convergence/round-*/report.json</code> が無い。</p></div>'
    order = list(dict.fromkeys(task.get("id", "") for d in rounds for task in d.get("tasks", [])))
    th = thresholds(skill)
    last = rounds[-1]
    met = [task.get("id", "") for task in sm["tasks"] if task.get("converged")]
    big = dot_text([(str(sm["ok"]), "dm-on"), ("/" + str(len(sm["tasks"])), "dm-dim")], pitch=5.6)
    verdict = (f'<div class="verdict {"ok" if sm["ok"] == len(sm["tasks"]) else "warn"}">{big}'
               f'<div><b>R{esc(last.get("round"))} で結果が揃った課題</b>'
               + (f'<span class="muted">（{esc("、".join(met))}）</span>' if met else "")
               + f'<p>{term("convergence")}は、課題ごとに、独立エージェントが作ったものの揃い方を 0〜1 で測る（1 なら全員が同じ）。'
               f'基準: {METRIC_NAMES["files"]} ≥ {th.get("files", 1.0):g}・{METRIC_NAMES["structure"]} ≥ {th.get("structure", 1.0):g}・'
               f'{METRIC_NAMES["names"]} ≥ {th.get("names", 0.8):g}。{METRIC_NAMES["content"]}は参考の値で、基準に使わない。</p></div></div>')
    prompts = {tid: str(skill["tasks"].get(tid, {}).get("prompt", "")) for tid in order}
    legend = "".join(f'<button type="button" class="fk" data-focus="s{i % 6 + 1}" aria-pressed="false" title="{esc(prompts[tid])}">'
                     f'<span class="sw s{i % 6 + 1}"></span>{esc(tid)}</button>' for i, tid in enumerate(order))
    charts = "".join(f'<figure><figcaption><b>{METRIC_NAMES[key]}</b><span>{label}（{key}）</span><em>基準 {float(th.get(key, 1.0)):g} 以上（破線）</em></figcaption>'
                     f'{metric_chart(rounds, key, float(th.get(key, 1.0)), order)}</figure>' for key, label in METRICS)
    rows = []
    for d in reversed(rounds):
        runners = "、".join(d.get("runners", []))
        models = model_list(skill["moves"].get(d.get("round"), {}).values())
        rows.append(f'<tr class="grp"><th colspan="8">R{esc(d.get("round"))}<span class="muted">{term("runner")} {esc(runners or "—")}'
                    + (f"・モデル {models}" if models else "") + "</span></th></tr>")
        for task in d.get("tasks", []):
            status_text = "、".join(sorted({STATUS_NAMES.get(s, s) for s in task.get("status", {}).values()})) or "—"
            verdict_cell = badge("ok", "揃った") if task.get("converged") else badge("warn", "揃わない")
            rows.append(f'<tr id="{anchor(skill["name"], "conv", d.get("round"), task.get("id", ""))}"><td><span class="tid">{esc(task.get("id", ""))}</span></td>'
                        f'<td class="num">{len(task.get("agents", []))} 人</td>'
                        f'<td>{esc(status_text)}</td>' + metric_cell(task.get("files"), float(th.get("files", 1.0)))
                        + metric_cell(task.get("structure"), float(th.get("structure", 1.0))) + metric_cell(task.get("names"), float(th.get("names", 0.8)))
                        + f'<td class="num muted">{fmt(task.get("content"))}</td><td>{verdict_cell}</td></tr>')
    heads = "".join(f'<th class="num">{METRIC_NAMES[k]}<small>{k}</small></th>' for k in ("files", "structure", "names"))
    table = ('<div class="card"><h3>ラウンドごとの値</h3><p class="lead">棒の縦線が基準。新しいラウンドが上。「終わり方」はエージェントの実行の結果。</p>'
             '<div class="scroll"><table class="conv"><thead><tr><th>課題</th>'
             f'<th class="num">人数</th><th>終わり方</th>{heads}<th class="num">{METRIC_NAMES["content"]}<small>content・参考</small></th>'
             f'<th>基準</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></div>')
    extra = []
    samples = last.get("review", {}).get("samples", [])
    if samples:
        items = "".join(f'<li>{badge("ok" if float(s.get("rate", 0)) >= 1 else "warn", format(float(s.get("rate", 0)), ".2f"))}'
                        f'<code>{esc(s.get("id", ""))}</code><span class="muted">（{esc(s.get("rule", ""))}）</span></li>' for s in samples)
        extra.append(f'<div><h4>レビューの検出率</h4><p class="lead">最後のラウンドの完了前チェックリストで、違反を見つけた割合。</p><ul class="plain">{items}</ul></div>')
    partial = []
    for task in last.get("tasks", []):
        files = task.get("partial_files", [])
        if files:
            items = "".join(f'<li><code>{esc(p.get("path", ""))}</code><span class="muted">{esc("、".join(p.get("who", [])))}</span></li>' for p in files)
            partial.append(f'<details class="more"><summary><b>{esc(task.get("id", ""))}</b> 一部のエージェントだけが作ったファイル {len(files)} 件</summary>'
                           f'<ul class="plain files">{items}</ul></details>')
    if partial:
        extra.append(f'<div><h4>R{esc(last.get("round"))} で人によって違ったファイル</h4>{"".join(partial)}</div>')
    conclusion = (f'<div class="card prose"><h3>結論</h3><p class="lead">dev/convergence-report.md の「結論」。</p>{markdown(skill["conclusion"])}</div>'
                  if skill["conclusion"].strip() else "")
    return (verdict + f'<div class="card" data-focus-scope><div class="key focus-key"><span class="muted">課題を押すと、その線だけを浮かび上がらせる</span>{legend}</div>'
            f'<div class="charts">{charts}</div></div>{table}'
            + (f'<div class="card split">{"".join(extra)}</div>' if extra else "") + conclusion)


def section_state(skill: dict) -> str:
    state = skill["state"]
    seal_kind, seal_text = skill["seal"]
    mark = badge("ok" if seal_kind == "ok" else "bad" if seal_kind == "bad" else "warn", seal_text)
    seal = (f'<div class="card" id="{anchor(skill["name"], "seal")}"><h3>{term("seal")}</h3><p>{mark}'
            + (f' 見比べたファイル {skill["seal_files"]} 件（SKILL.md、scripts、assets、references）' if skill["seal_files"] else "")
            + '</p><p class="lead">検証に合格したとき（finish が検査に通ったとき）のファイルの指紋（assets/seal.json）と、今のファイルを見比べる。'
              '合格した後に書き換えると、ここに出て、次の run.py start が止まる。</p></div>')
    if not state:
        return seal + (f'<div class="card empty"><p>このプロジェクトに実行の記録（<code>{rt.RUNS_DIRNAME}/{esc(skill["name"])}/state.json</code>）が無い。'
                       'スキルを実行すると、start から finish までの記録がここに出る。</p></div>')
    events = state.get("history", [])[-40:]
    kind = {"done": "ok", "failed": "bad", "aborted": "warn"}.get(state.get("status"), "none")
    items = "".join(f'<li><time>{esc(str(e.get("at", ""))[11:19])}</time><b>{esc(e.get("event", ""))}</b>'
                    + (f'<span class="muted">{esc(e.get("detail", ""))}</span>' if e.get("detail") else "") + "</li>" for e in events)
    return seal + (f'<div class="card"><h3>最後の実行</h3><p>{badge(kind, "結果: " + STATUS_NAMES.get(state.get("status"), str(state.get("status", "—"))))} '
                   f'開始 {esc(state.get("started_at", "—"))}・終了 {esc(state.get("finished_at", "—"))}</p><ol class="timeline">{items}</ol></div>')


def section_skill(skill: dict) -> str:
    spec, name = skill["spec"], skill["name"]
    sm = summary(skill)
    products = "、".join(report_skill.PRODUCTS.get(x, x) for x in spec.get("targets", []))
    hooks = "、".join(f"{report_skill.PRODUCTS[p]} {len(e)}" for p, e in skill["hooks"].items() if e) or "登録なし"
    status = {"building": "作っている途中", "ready": "完成"}.get(spec.get("status"), spec.get("status", "—"))
    mode = {"new": "新しく作った", "retrofit": "既存のスキルに後付けした"}.get(spec.get("mode"), spec.get("mode", "—"))
    meta = [("置き場", f"<code>{esc(skill['path'])}</code>"), ("対象", esc(products)),
            ("言語", esc(report_skill.LANGUAGES.get(spec.get("language"), spec.get("language", "")))),
            ("状態", esc(f"{status}（{mode}）")), ("hooks の登録", esc(hooks))]
    place_id = anchor(name, "place")
    meta_html = "".join((f'<div id="{place_id}">' if k == "置き場" else "<div>") + f"<dt>{k}</dt><dd>{v}</dd></div>" for k, v in meta)
    unmatched = skill["unmatched"]
    rnd = skill["rounds"][-1].get("round") if skill["rounds"] else None
    arrow = '<path d="M20,4 L25,7 L20,10 z" class="wf-arrow-back"/>'
    notes = [f'<span><span class="lg lg-gate"></span><span>{term("gate")}（<code>run.py start</code>・<code>check</code>・<code>finish</code>）のある手順</span></span>',
             '<span><span class="lg lg-hooks"></span><span>hooks が働く範囲</span></span>',
             key_item('<path d="M5,2.5 C24,0 24,14 7,11.5" class="wf-loop"/><path d="M3,11.6 L8.4,8.6 L8.6,14 z" class="wf-arrow-back"/>',
                      "<b>↻ 繰り返す</b> 通るまで繰り返す手順（エラー 0 件まで、すべて成功まで、直してやり直す）。番号の横の輪"),
             key_item('<path d="M1,7 H13" class="wf-exit-edge"/><path d="M12,4.5 L16,7 L12,9.5 z" class="wf-arrow-back"/>'
                      '<rect x="17.5" y="3" width="8" height="8" rx="1.5" class="wf-end"/>', "<b>■ 終了</b> 途中で終える道（「〜なら…終える」）"),
             '<span><span><b>◇ 条件</b> 文の頭の「〜なら、」「〜なければ、」で変わる作業</span></span>',
             key_item('<path d="M1,7 H21" class="wf-back"/>' + arrow, "<b>↩ 戻る</b> 手順の文にある戻り（「手順Nに戻る」）。戻る元のカードに、戻る場合と戻り先、"
                      "「└ なぜ」に終了コードの意味（スクリプトの説明の「終了コード:」の行）と戻った先で直すことを書く")]
    if observed_backs(skill):
        notes.append(key_item('<path d="M2,7 H19" class="wf-obs"/><path d="M19,4 L24,7 L19,10 z" class="wf-arrow-obs"/>',
                              f"<b>↩ {term('back')}</b> R{esc(rnd)} で独立エージェントが実際に戻ったところと人数。戻る元のカードに、戻り先と戻って最初の操作、"
                              "「└ なぜ」に記録の操作から読めるわけ（直前の失敗、まだしていなかった手順、前の手順で作るファイルを直した）を書く"))
    notes.append('<span><span class="lv lv-machine">ID</span><span>機械が確かめるルール</span></span><span><span class="lv lv-tool">ID</span>'
                 '<span>スクリプト・ひな形</span></span><span><span class="lv lv-human">ID</span><span>レビュー・文書だけ（✓ ✕ は、違反の見本を検査が止めたかどうか）</span></span>')
    caption = ""
    if skill["rounds"]:
        caption = ('<p class="lead">左のオレンジの点線は、最後のラウンドの記録で、エージェントが前の手順に戻ったところ（操作を手順に当てたのは推定で、'
                   '人ごとの流れは「エージェントの動き」で見る）。その「なぜ」は記録の操作から書いたもので、エージェントが書いた理由ではない。'
                   f'右の「操作」はその手順でのエージェントの操作の回数、「ファイル」は R{esc(rnd)} で作った・変えたファイルを'
                   '手順の本文に書かれたパスに当てて数えたもの（一番長く一致した手順）。'
                   + (f'本文にパスが無いファイル {unmatched["files"]} 件（全員 {unmatched["all"]}・一部だけ {unmatched["partial"]}）は数えていない。'
                      if unmatched["files"] else "")
                   + "チェックポイントの人数は、完了まで進む課題のエージェントだけを数える。"
                   + ("チェックポイントを通った回数は、このラウンドの記録に無い。" if skill["gates"] is None else "") + "</p>")
    steps_html = "".join(f'<li value="{s["no"]}">{inline(s["raw"])}</li>' for s in skill["steps"])
    diagram = workflow_svg(skill) if skill["steps"] else '<p class="muted">SKILL.md の「2. 手順」に番号の行が無い。</p>'
    movers = last_moves(skill)
    flagged = sum(any(a["outside"] for a in run["actions"]) for run in movers.values())
    counts = {"workflow": f'{len(skill["steps"])} 手順', "movement": f"{len(movers)} 人" if movers else "",
              "convergence": f"R{sm['round']}" if sm["round"] is not None and not sm["skip"] else "",
              "decisions": str(len(skill["decisions"])), "probes": str(len(sm["results"])) if sm["results"] else "", "state": ""}
    warn_tabs = {"movement": flagged > 0, "convergence": sm["conv"][0] == "warn", "probes": bool(sm["p_fail"] or sm["w_fail"]),
                 "state": sm["seal"][0] != "ok"}
    group = f"tab-{name}"
    tabs = "".join(f'<button type="button" role="tab" data-for="{esc(group)}" data-show="skill-{esc(name)}-{key}" data-hash="">{label}'
                   + (f'<span class="cnt{" warn" if warn_tabs.get(key) else ""}">{esc(counts[key])}</span>' if counts.get(key) else
                      ('<span class="cnt warn">!</span>' if warn_tabs.get(key) else "")) + "</button>" for key, label in TABS)
    panes = {
        "workflow": (f'<div class="card"><p class="lead">SKILL.md の「2. 手順」と出力の決まり（assets/contract.json）から描いた流れ。'
                     '左の番号が手順、右が最後のラウンドの収束テストで、独立エージェント（これまでの会話を持たないエージェント）が残した記録。'
                     f'カードに重ねると本文が出る。</p><div class="scroll">{diagram}</div><div class="key notes">{"".join(notes)}</div>{caption}</div>'
                     f'<details class="card more"><summary>手順の本文（SKILL.md の「2. 手順」）</summary><ol class="steps">{steps_html}</ol></details>'),
        "movement": section_movement(skill),
        "convergence": section_convergence(skill, sm),
        "decisions": section_decisions(skill) + section_outputs(skill),
        "probes": section_probes(skill, sm),
        "state": section_state(skill),
    }
    body = "".join(f'<div class="pane" id="skill-{esc(name)}-{key}" data-pane="{esc(group)}" role="tabpanel" aria-label="{label}">{panes[key]}</div>'
                   for key, label in TABS)
    return f"""
<section class="skill" id="skill-{esc(name)}">
  <header class="sk-head">
    <p class="eyebrow">skill-foundation で作ったスキル</p>
    <h2>{esc(name)}</h2>
    <p class="sk-title">{inline(spec.get("title", ""))}</p>
    <p class="sk-purpose">{inline(spec.get("purpose", ""))}</p>
    <dl class="meta">{meta_html}</dl>
  </header>
  {tiles(skill, sm)}
  {attention(skill, sm)}
  <div class="tabs" role="tablist" aria-label="{esc(name)} の記録">{tabs}</div>
  {body}
</section>"""


SERIES = {"light": ["#2a78d6", "#1baf7a", "#6250d6", "#e87ba4", "#eda100", "#008300"],
          "dark": ["#3987e5", "#199e70", "#9085e9", "#d55181", "#c98500", "#008300"]}
DARK = ("--bg:#191814;--panel:#201f1c;--sunken:#2a2925;--zebra:#24231f;--ink:#ede9df;--ink-2:#bdb7a9;--muted:#948e80;"
        "--line:#34322d;--line-2:#4a473f;--dot-off:#35332d;--grid-dot:rgba(237,233,223,.06);"
        "--accent:#d97757;--accent-ink:#eb9877;--accent-soft:rgba(217,119,87,.15);--on-accent:#1b1a17;"
        "--good:#22b322;--good-ink:#62d062;--good-soft:rgba(34,179,34,.13);--warn:#fab219;--warn-ink:#f6c453;--warn-soft:rgba(250,178,25,.12);"
        "--crit:#e05252;--crit-ink:#f28a8a;--crit-soft:rgba(224,82,82,.15);--on-crit:#ffffff;--shadow:0 10px 30px rgba(0,0,0,.55);"
        + "".join(f"--s{i}:{c};" for i, c in enumerate(SERIES["dark"], 1)))
LIGHT = ("--bg:#f6f5f1;--panel:#ffffff;--sunken:#efede7;--zebra:#faf9f6;--ink:#1f1e1b;--ink-2:#504d45;--muted:#706c62;"
         "--line:#e4e1d8;--line-2:#cdc9bd;--dot-off:#e6e3da;--grid-dot:rgba(31,30,27,.08);"
         "--accent:#c6613f;--accent-ink:#a84f30;--accent-soft:#f8e7e0;--on-accent:#ffffff;"
         "--good:#0ca30c;--good-ink:#087a08;--good-soft:#e3f4e3;--warn:#fab219;--warn-ink:#875800;--warn-soft:#fdf1d6;"
         "--crit:#d03b3b;--crit-ink:#b02b2b;--crit-soft:#fbe6e6;--on-crit:#ffffff;--shadow:0 8px 26px rgba(31,30,27,.18);"
         + "".join(f"--s{i}:{c};" for i, c in enumerate(SERIES["light"], 1)))
SERIES_CSS = "".join(f".s{i}.mv-bar,.sw.s{i}{{fill:var(--s{i});background:var(--s{i})}}.ch-line.s{i},.mv-link.s{i}{{stroke:var(--s{i})}}"
                     f".ch-dot.s{i}{{fill:var(--s{i})}}" for i in range(1, 7))
SEGMENTS = "repeating-linear-gradient(90deg,#000 0 5px,transparent 5px 7px)"
FONTS = "https://fonts.googleapis.com/css2?family=DotGothic16&family=JetBrains+Mono:wght@400;700&display=swap"

CSS = """
/* 端末の画面のような見た目: 点の格子の地、等幅の本文、点で描いた数字。左にスキルの一覧、右に見出し・数字・先に見るもの、その下をタブで切り替える */
:root{""" + DARK + """color-scheme:dark;
--mono:"JetBrains Mono","SF Mono",Menlo,Consolas,"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic UI",Meiryo,monospace;
--display:"DotGothic16","JetBrains Mono","SF Mono",Menlo,"Hiragino Sans","Noto Sans JP",monospace}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){""" + LIGHT + """color-scheme:light}}
:root[data-theme="light"]{""" + LIGHT + """color-scheme:light}
*{box-sizing:border-box}
[hidden]{display:none!important}
.wrap,.skill,.pane,.task,.logs,.others,.idx,.sk-head{grid-template-columns:minmax(0,1fr)}
html{scroll-padding-top:64px}
body{margin:0;background-color:var(--bg);background-image:radial-gradient(var(--grid-dot) 1px,transparent 1.5px);background-size:20px 20px;
color:var(--ink);font:15px/1.8 var(--mono);-webkit-font-smoothing:antialiased}
code,.mono{font-family:var(--mono);font-size:.93em}
a{color:var(--accent-ink);text-decoration:none}a:hover{text-decoration:underline dotted;text-underline-offset:3px}
:focus-visible{outline:2px dashed var(--accent);outline-offset:2px}
h1,h2,h3,h4{text-wrap:balance}
.app{display:grid;grid-template-columns:292px minmax(0,1fr);min-height:100vh}
.rail{position:sticky;top:0;height:100vh;overflow:auto;padding:22px 16px 28px;border-right:1px dashed var(--line-2);background:var(--panel)}
.brand{display:flex;gap:12px;align-items:center;margin:0 4px 18px}
.brand b{display:block;font:400 18px/1.35 var(--display);letter-spacing:.04em}
.brand span{display:block;font-size:13px;color:var(--muted);word-break:break-all;line-height:1.45}
.px-mark{display:block;flex:none;fill:var(--accent)}
.search{width:100%;padding:9px 12px;border:1px solid var(--line-2);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;font-size:14px}
.search::placeholder{color:var(--muted)}
.search:focus{outline:none;border-color:var(--accent)}
.nv{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:4px}
.nv-skill{display:grid;gap:2px;padding:10px 12px;border-radius:6px;color:var(--ink)}
.nv-skill:hover{background:var(--sunken);text-decoration:none}
.nv .nm{font-size:14.5px;font-weight:700}
.nv .nm::before{content:"> ";color:var(--accent)}
.nv .tl{font-size:13px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nv .marks{display:flex;flex-wrap:wrap;gap:2px 12px;margin-top:6px}
.nv .marks .st{font-size:12.5px}
.nv-sub{list-style:none;margin:2px 0 8px 18px;padding:0 0 0 10px;border-left:1px dotted var(--line-2)}
.nv-sub a{display:block;padding:3px 8px;font-size:13.5px;color:var(--ink-2);border-radius:4px}
.nv-sub a:hover{background:var(--sunken);color:var(--ink);text-decoration:none}
.nv-h{font-size:13px;color:var(--muted);letter-spacing:.06em;margin:24px 10px 6px;font-weight:700}
.nv-other a{display:block;padding:4px 10px;border-radius:4px;font-size:13.5px;color:var(--ink-2)}
.nv-home{display:block;margin:14px 0 0;padding:6px 12px;border-radius:6px;font-size:13.5px;font-weight:700}
.nv-home:hover{background:var(--sunken);text-decoration:none}
.nv-skill[aria-current="page"]{background:var(--sunken)}
.nv .pl{font-size:12.5px;color:var(--muted);overflow-wrap:anywhere}
main{min-width:0;padding-block:28px 56px;padding-left:max(40px,env(safe-area-inset-left,0px));padding-right:max(40px,env(safe-area-inset-right,0px))}
.wrap{max-width:1140px;margin:0 auto;display:grid;gap:44px}
.top{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:14px 22px;align-items:start;padding:20px 22px;border:1px solid var(--accent);border-radius:10px;background:var(--panel)}
.top .px-mark{margin-top:4px}
.top h1{margin:0;font:400 26px/1.3 var(--display);letter-spacing:.04em}
.top h1::after{content:"";display:inline-block;width:.5em;height:1em;margin-left:8px;vertical-align:-.12em;background:var(--accent);animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.top .when{margin:6px 0 0;font-size:13.5px;color:var(--ink-2);overflow-wrap:anywhere}
.regen{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:10px 0 0;font-size:13.5px;color:var(--ink-2)}
.regen code{background:var(--sunken);padding:4px 10px;border-radius:4px;color:var(--ink);word-break:break-all}
.regen code::before{content:"$ ";color:var(--accent)}
.btn{font:inherit;font-size:13px;padding:3px 12px;border-radius:4px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink);cursor:pointer}
.btn:hover{border-color:var(--accent);color:var(--accent-ink)}
.theme{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line-2);border-radius:6px;background:var(--bg)}
.theme button{font:inherit;font-size:13px;padding:4px 12px;border:0;border-radius:4px;background:none;color:var(--ink-2);cursor:pointer}
.theme button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent);font-weight:700}
.skill{display:grid;gap:22px;min-width:0}
.sk-head{display:grid;gap:6px}
.eyebrow{margin:0;font-size:13px;letter-spacing:.06em;color:var(--accent-ink);font-weight:700}
.eyebrow::before{content:"✻ "}
.sk-head h2{margin:0;font:400 38px/1.2 var(--display);letter-spacing:.02em;overflow-wrap:anywhere}
.sk-title{margin:4px 0 0;font-size:18px;font-weight:700;line-height:1.6}
.sk-purpose{margin:0;color:var(--ink-2);max-width:72ch}
.meta{display:flex;flex-wrap:wrap;gap:6px 26px;margin:10px 0 0;font-size:13.5px}
.meta div{display:flex;gap:8px}.meta dt{color:var(--muted)}.meta dd{margin:0;color:var(--ink-2)}
.tiles{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.tile{display:grid;gap:10px;align-content:start;padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--ink)}
a.tile:hover{border-color:var(--accent);text-decoration:none}
.tile-top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:4px 8px;min-height:24px}
.tile-k{font-size:13px;color:var(--ink-2);font-weight:700}
.tile-v{display:flex;align-items:flex-end;min-height:34px}
.tile-word{font:400 26px/1.2 var(--display)}
.tile-s{font-size:13px;color:var(--muted);line-height:1.55}
.dm{display:block;max-width:100%;height:auto}
.dm-on{fill:var(--ink)}.dm-dim{fill:var(--muted)}.dm-off{fill:var(--dot-off)}
.big{display:inline-flex;align-items:flex-end;gap:10px}
.big small{font-size:13.5px;color:var(--muted);font-weight:700}
.meter{display:flex;height:8px;background:var(--dot-off);-webkit-mask-image:""" + SEGMENTS + """;mask-image:""" + SEGMENTS + """}
.meter i{display:block;height:100%}
.meter .good{background:var(--good)}.meter .crit{background:var(--crit)}.meter .warn{background:var(--warn)}
.meter .acc{background:var(--accent)}.meter .mute{background:var(--line-2)}
.attn{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 20px 18px}
.attn h3{margin:0 0 12px;font:400 18px/1.4 var(--display);letter-spacing:.04em}
.attn ul{list-style:none;margin:0;padding:0;display:grid;gap:14px}
.attn li{display:grid;grid-template-columns:12px minmax(0,1fr);gap:2px 12px;font-size:14.5px;line-height:1.75}
.attn .pt{width:9px;height:9px;border-radius:50%;margin-top:.6em;background:var(--muted)}
.attn li.crit .pt{background:var(--crit)}.attn li.warn .pt{background:var(--warn)}.attn li.info .pt{background:var(--ink-2)}.attn li.good .pt{background:var(--good)}
.attn .lvl{font-weight:700;margin-right:10px}
.attn li.crit .lvl{color:var(--crit-ink)}.attn li.warn .lvl{color:var(--warn-ink)}.attn li.info .lvl{color:var(--ink-2)}.attn li.good .lvl{color:var(--good-ink)}
.attn .go{grid-column:2;font-size:13.5px;color:var(--muted)}
.attn .go a{font-weight:700}
.tabs{position:sticky;top:0;z-index:5;display:flex;gap:2px;overflow-x:auto;background:var(--bg);border-bottom:1px dashed var(--line-2);scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tabs button,.seg button{font:inherit;cursor:pointer;white-space:nowrap;display:inline-flex;gap:8px;align-items:center}
.tabs button{position:relative;font-size:14.5px;font-weight:700;color:var(--ink-2);background:none;border:0;padding:13px 14px 12px}
.tabs button::before{content:"";width:7px;height:7px;flex:none;background:var(--line-2)}
.tabs button:hover{color:var(--ink)}
.tabs button[aria-selected="true"]{color:var(--ink)}
.tabs button[aria-selected="true"]::before{background:var(--accent)}
.tabs button[aria-selected="true"]::after{content:"";position:absolute;left:12px;right:12px;bottom:-1px;height:3px;
background:repeating-linear-gradient(90deg,var(--accent) 0 3px,transparent 3px 5px)}
.cnt{font-size:12.5px;font-weight:700;padding:0 7px;border-radius:4px;background:var(--sunken);color:var(--ink-2);line-height:1.7}
.cnt.warn{background:var(--warn-soft);color:var(--warn-ink)}
.pane{display:grid;gap:16px;min-width:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:20px 22px;min-width:0}
.card h3{margin:0;font-size:16px;line-height:1.5;display:flex;align-items:center;gap:10px}
.card h3::before{content:"";width:8px;height:8px;flex:none;background:var(--accent)}
.card h4{margin:0 0 6px;font-size:14.5px}
.card-head{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between;margin-bottom:8px}
.lead{margin:6px 0 14px;color:var(--ink-2);font-size:14px;max-width:86ch}
.card > .lead:last-child{margin-bottom:0}
.empty p{margin:0;color:var(--ink-2)}
.prose p,.prose li{max-width:80ch}.prose ul{padding-left:22px}
.scroll{overflow-x:auto;max-width:100%}
.seg{display:inline-flex;flex-wrap:wrap;gap:4px;padding:3px;border-radius:6px;border:1px solid var(--line-2);background:var(--bg)}
.seg button{font-size:14px;font-weight:700;color:var(--ink-2);background:none;border:0;border-radius:4px;padding:5px 12px}
.seg button[aria-selected="true"],.seg button[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent-ink);box-shadow:inset 0 0 0 1px var(--accent)}
.seg-sm button{font-size:13px;padding:4px 10px}
.bar-row{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
.howto{font-size:14px;color:var(--ink-2)}
.howto summary{cursor:pointer;font-weight:700;color:var(--accent-ink)}
.howto p{margin:6px 0 0;max-width:90ch}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 12px;text-align:left;vertical-align:top;border-bottom:1px dashed var(--line)}
thead th{font-size:13px;color:var(--muted);font-weight:700;letter-spacing:.03em;white-space:nowrap;border-bottom:1px solid var(--line-2)}
tbody tr:last-child td{border-bottom:0}
tr.grp th{background:var(--sunken);font-size:13.5px;color:var(--ink);font-weight:700;padding:8px 12px;border-bottom:0}
tr.grp th .muted{font-weight:400;margin-left:12px}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.muted{color:var(--muted)}
.tid,.rid{font-weight:700;font-size:13.5px;white-space:nowrap}
ul.plain{list-style:none;padding:0;margin:0;display:grid;gap:6px}
ul.plain li{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:baseline}
ul.files{margin-top:8px;font-size:13.5px}
.st{display:inline-flex;gap:6px;align-items:center;font-size:13px;font-weight:700;white-space:nowrap;line-height:1.5;color:var(--ink-2)}
.st i{width:8px;height:8px;border-radius:50%;flex:none;background:var(--muted)}
.st-ok{color:var(--good-ink)}.st-ok i{background:var(--good)}
.st-bad{color:var(--crit-ink)}.st-bad i{background:var(--crit)}
.st-warn{color:var(--warn-ink)}.st-warn i{background:var(--warn)}
td .st{margin:1px 10px 1px 0}
.lv{display:inline-block;font:700 12.5px/1.7 var(--mono);padding:0 7px;border-radius:4px;margin:1px 4px 1px 0;border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel)}
.lv-machine{background:var(--accent-soft);border-color:var(--accent);color:var(--accent-ink)}
.lv-human{border-style:dashed}
.key{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;font-size:13.5px;color:var(--ink-2)}
.key > span{display:inline-flex;gap:8px;align-items:center}
.key > span > span:last-child{display:inline}
.key.notes{margin-top:16px;padding-top:14px;border-top:1px dashed var(--line-2)}
.lg{display:inline-block;flex:none}
.lg-gate{width:24px;height:16px;border:2px solid var(--accent);border-radius:3px}
.lg-hooks{width:24px;height:16px;background:var(--accent-soft);border:1.5px dashed var(--accent);border-radius:3px}
.sw{display:inline-block;width:18px;height:7px;flex:none;vertical-align:middle;margin-right:8px;
-webkit-mask-image:repeating-linear-gradient(90deg,#000 0 4px,transparent 4px 5px);mask-image:repeating-linear-gradient(90deg,#000 0 4px,transparent 4px 5px)}
.steps{margin:14px 0 0;padding-left:26px;font-size:14px;color:var(--ink-2)}.steps li{margin:8px 0}
.steps li::marker{color:var(--accent);font-weight:700}
details.more > summary{cursor:pointer;font-weight:700;font-size:14px}
.card.more > summary{color:var(--ink)}
details.dd summary{cursor:pointer;font-weight:700}
details.dd p{margin:8px 0;color:var(--ink-2);font-size:14px;max-width:70ch}
details.dd .k{display:inline-block;font-size:13px;font-weight:700;color:var(--muted);margin-right:8px}
td.basis{font-size:13.5px;color:var(--ink-2);min-width:130px}
.seq{display:flex;flex-wrap:wrap;gap:3px}
.sq{font:700 12.5px/22px var(--mono);min-width:24px;padding:0 5px;text-align:center;border-radius:3px;background:var(--sunken);color:var(--ink-2)}
.sq.back{background:var(--warn-soft);color:var(--warn-ink)}.sq.back::before{content:"↩";margin-right:1px}
.sq.gap{background:none}
table.mvt td{vertical-align:middle}
.dec .seq{flex-wrap:nowrap}table.wire td:first-child{white-space:nowrap}
td.who{white-space:nowrap;font-size:13.5px;font-weight:700}
td.kinds{font-size:13px;color:var(--ink-2);min-width:160px}
.opsn{display:inline-flex;align-items:center;gap:8px}
.bar{display:inline-block;width:61px;height:8px;background:var(--dot-off);overflow:hidden;-webkit-mask-image:""" + SEGMENTS + """;mask-image:""" + SEGMENTS + """}
.bar i{display:block;height:100%;background:var(--accent)}
.task{display:grid;gap:14px}
.task header{display:grid;gap:4px}
.task h3{font-size:16px}
.prompt{margin:0;color:var(--ink-2);font-size:14px;max-width:90ch}
.prompt::before{content:"> ";color:var(--accent);font-weight:700}
.ob{margin-top:10px;border:1px solid var(--line-2);border-radius:8px;background:var(--bg);padding:14px 16px;display:grid;gap:12px;min-width:0}
.ob-t{margin:0;font-size:14px;display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}
.ob-t::before{content:"";width:8px;height:8px;flex:none;border:2px solid var(--crit);border-radius:2px}
.ob-n{font-size:12.5px;font-weight:400;color:var(--muted)}
.ob-vs{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:10px}
.ob-v{min-width:0;border:1px solid var(--line-2);border-left:4px solid var(--muted);border-radius:6px;padding:10px 12px;background:var(--panel)}
.ob-vh{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px;font-weight:700}
.ob-vh b{font-size:13px;padding:0 8px;border-radius:3px;background:var(--sunken);color:var(--ink-2)}
.ob-good{border-left-color:var(--good)}.ob-good .ob-vh b{background:var(--good-soft);color:var(--good-ink)}
.ob-warn{border-left-color:var(--warn)}.ob-warn .ob-vh b{background:var(--warn-soft);color:var(--warn-ink)}
.ob-bad{border-left-color:var(--crit)}.ob-bad .ob-vh b{background:var(--crit-soft);color:var(--crit-ink)}
.ob-q{margin:2px 0 6px;font-size:12.5px;line-height:1.6;color:var(--muted)}
.ob-v ul{margin:0;padding-left:1.2em;font-size:13px;line-height:1.7;overflow-wrap:anywhere}
.ob-p{min-width:0;border-top:1px dashed var(--line-2);padding-top:10px;display:grid;gap:4px;font-size:13px;line-height:1.7}
.ob-p p{margin:0}.ob-ph{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px}.ob-ph span{color:var(--muted);font-size:12.5px}
.ob-path{font-size:12.5px;color:var(--crit-ink);overflow-wrap:anywhere}
.ob-k{display:inline-block;min-width:5.5em;color:var(--muted)}
.ob-ops code{display:inline-block;font-size:12.5px;margin:2px 6px 2px 0;padding:0 6px;border-radius:3px;background:var(--sunken);overflow-wrap:anywhere}
.ob-rule summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--accent-ink)}.ob-rule ul{margin:6px 0 0;padding-left:1.2em;font-size:12.5px;line-height:1.7}.ob-rule ul ul{margin:0;padding-left:.4em;list-style:none}
.logs{display:grid;gap:8px}
details.log{border:1px solid var(--line);border-radius:6px;background:var(--panel)}
details.log > summary{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;padding:10px 14px;cursor:pointer;list-style:none;font-size:14px}
details.log > summary::-webkit-details-marker{display:none}
details.log > summary::before{content:"▸";color:var(--accent);width:1ch}
details.log[open] > summary::before{content:"▾"}
.src{margin-left:auto;font-size:12.5px;color:var(--muted)}
.logbox{max-height:480px;overflow:auto;border-top:1px dashed var(--line-2)}
.logbox thead th{position:sticky;top:0;background:var(--panel);z-index:1}
table.ops td{font-size:13.5px;padding:6px 12px}
table.ops code{white-space:pre-wrap;word-break:break-all;font-size:13px}
table.ops tr.ng td,table tr.ng td{background:var(--crit-soft)}
table.ops tr.ng td:first-child{box-shadow:inset 3px 0 0 var(--crit)}
.kd{font-size:12.5px;font-weight:700;padding:1px 8px;border-radius:3px;background:var(--sunken);color:var(--ink-2);white-space:nowrap}
.kd-run{background:var(--accent-soft);color:var(--accent-ink)}
.yes{color:var(--good-ink);font-weight:700}.no{color:var(--crit-ink);font-weight:700}
details.reply{padding:0 14px 12px}
details.reply summary{cursor:pointer;font-size:13.5px;font-weight:700;color:var(--ink-2);padding-top:10px}
.flow{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:12px;padding:12px 14px;border-top:1px dashed var(--line-2)}
.fl-mech,.fl-ai{min-width:0;border:1px solid var(--line);border-radius:6px;padding:10px 14px;background:var(--zebra)}
.fl-ai{border-left:3px solid var(--accent)}.fl-ai.none{border-left-color:var(--line-2)}
.flow h4{margin:0 0 8px;font-size:14px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
.flow h5{margin:12px 0 4px;font-size:13px;color:var(--ink-2)}
.flow p,.flow li{margin:0;font-size:13.5px;line-height:1.75}
.flow ul{margin:0;padding-left:1.3em}
.fl-mech dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:6px 14px;margin:0;font-size:13px}
.fl-mech dt{color:var(--muted)}.fl-mech dd{margin:0;min-width:0}
.fl-ai .by{margin-top:12px;font-size:12.5px;color:var(--muted)}
td.match{min-width:14ch;max-width:30ch}
.mt{display:block;font-size:12.5px;line-height:1.6;color:var(--ink-2)}
.mt-back{color:var(--warn-ink);font-weight:700}.mt-off{color:var(--muted)}.mt-redo{color:var(--crit-ink);font-weight:700}
td.why{min-width:24ch;max-width:52ch;font-size:13px;line-height:1.65}
.fit{font-weight:700;white-space:nowrap;margin-right:2px}
.fit-ok{color:var(--good-ink)}.fit-detour{color:var(--warn-ink)}.fit-waste{color:var(--muted)}.fit-wrong{color:var(--crit-ink)}
details.out summary{cursor:pointer;font-size:12px;color:var(--muted);margin-top:2px}
details.out pre{margin:4px 0 0;max-height:180px;overflow:auto;font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-all;
  background:var(--sunken);padding:6px 8px;border-radius:4px}
@media (max-width:760px){.flow{grid-template-columns:minmax(0,1fr)}}
pre{white-space:pre-wrap;font:13px/1.65 var(--mono);background:var(--sunken);padding:14px 16px;border-radius:6px;border-left:3px solid var(--accent);max-height:420px;overflow:auto;margin:8px 0 0}
.verdict{display:flex;flex-wrap:wrap;gap:16px 24px;align-items:center;padding:18px 22px;border-radius:8px;border:1px solid var(--line);background:var(--panel)}
.verdict.warn{border-color:var(--warn);background:var(--warn-soft)}.verdict.ok{border-color:var(--good);background:var(--good-soft)}
.verdict > div{flex:1 1 320px;min-width:0}
.verdict p{margin:6px 0 0;font-size:14px;color:var(--ink-2);max-width:80ch}
.charts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin-top:16px}
.charts figure{margin:0;min-width:0}
.charts figcaption{display:flex;flex-wrap:wrap;gap:2px 8px;align-items:baseline;margin-bottom:6px;font-size:13.5px}
.charts figcaption b{font-size:14.5px}
.charts figcaption span{color:var(--ink-2)}.charts figcaption em{font-style:normal;color:var(--muted);width:100%;font-size:13px}
.mcell{display:inline-flex;align-items:center;gap:8px}
.mbar{position:relative;display:inline-block;width:61px;height:8px;background:repeating-linear-gradient(90deg,var(--dot-off) 0 5px,transparent 5px 7px)}
.mbar i{position:absolute;left:0;top:0;bottom:0;-webkit-mask-image:""" + SEGMENTS + """;mask-image:""" + SEGMENTS + """}
.mbar i.hi{background:var(--good)}.mbar i.lo{background:var(--warn)}
.mbar b{position:absolute;top:-3px;bottom:-3px;width:2px;margin-left:-1px;background:var(--ink)}
.split{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:24px}
.timeline{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:2px;font-size:14px}
.timeline li{display:flex;flex-wrap:wrap;gap:4px 14px;padding:6px 0;border-bottom:1px dashed var(--line)}
.timeline time{color:var(--muted);font-size:13px}
.others,.idx{display:grid;gap:12px}
.others h2,.idx h2{margin:0;font:400 22px/1.35 var(--display);letter-spacing:.03em}
.others-grid,.idx-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:12px}
.sk-card{display:grid;gap:6px;align-content:start;color:var(--ink)}
a.sk-card:hover{border-color:var(--accent);text-decoration:none}
.sk-card .nm{font-size:16px;font-weight:700;overflow-wrap:anywhere}.sk-card .nm::before{content:"> ";color:var(--accent)}
.sk-card .tl{font-size:14px;color:var(--ink-2)}
.sk-card .pl{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.sk-card .marks{display:flex;flex-wrap:wrap;gap:2px 12px}
.sk-card .at{font-size:13.5px;color:var(--ink-2)}.sk-card .at b{margin-right:6px}
.sk-card .at .crit{color:var(--crit-ink)}.sk-card .at .warn{color:var(--warn-ink)}.sk-card .at .good{color:var(--good-ink)}
.others .card p{margin:6px 0 0;font-size:14px;color:var(--ink-2)}
.others .card b{font-size:14.5px}
footer{color:var(--muted);font-size:13px;border-top:1px dashed var(--line-2);padding-top:18px}
svg text{font-family:var(--mono)}
.wf,.mv{display:block;width:100%;height:auto;min-width:900px}
.wf-colh{font-size:13px;font-weight:700;fill:var(--muted);letter-spacing:.04em}
.wf-colline{stroke:var(--line-2);stroke-width:1;stroke-dasharray:2 3}
.wf-card{fill:var(--panel);stroke:var(--line-2);stroke-width:1}
.wf-gate{stroke:var(--accent);stroke-width:1.6}
.wf-title{font-size:15px;font-weight:700;fill:var(--ink)}
.wf-sub,.wf-branch{font-size:13px;fill:var(--ink-2)}
.wf-tag{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1}.wf-tag-t{font-size:12px;font-weight:700;fill:var(--accent-ink)}
.wf-rail{stroke:var(--line-2);stroke-width:3;stroke-dasharray:0 7;stroke-linecap:round}
.wf-node{fill:var(--panel);stroke:var(--line-2);stroke-width:1.5}
.wf-node-gate{fill:var(--accent);stroke:var(--accent)}
.wf-node-t{font-size:13px;font-weight:700;fill:var(--ink-2)}
.wf-node-t-gate{fill:var(--on-accent)}
.wf-end{fill:var(--muted)}
.wf-hooks{fill:var(--accent-soft);fill-opacity:.6;stroke:var(--accent);stroke-width:1.2;stroke-dasharray:4 4}
.wf-hooks-t{font-size:12.5px;font-weight:700;fill:var(--accent-ink);letter-spacing:.02em}
.wf-back{fill:none;stroke:var(--ink-2);stroke-width:1.6}
.wf-arrow-back{fill:var(--ink-2)}
.wf-back-t{font-size:12px;fill:var(--ink-2)}
.wf-obs{fill:none;stroke:var(--accent);stroke-width:2.2;stroke-dasharray:0 5;stroke-linecap:round}
.wf-arrow-obs{fill:var(--accent)}
.wf-obs-t{font-size:12px;font-weight:700;fill:var(--accent-ink)}
.wf-loop,.wf-exit-edge{fill:none;stroke:var(--ink-2);stroke-width:1.6}
.wf-lead{font-size:13px;font-weight:700;fill:var(--ink)}
.wf-cond,.wf-exit,.wf-loop-t,.wf-back-line,.wf-obs-line{font-size:13px;fill:var(--ink-2)}
.wf-lead-obs{fill:var(--accent-ink)}
.wf-note{font-size:12.5px;fill:var(--muted)}
.chip rect{fill:var(--panel);stroke:var(--line-2)}
.chip-t{font-size:12.5px;fill:var(--ink)}
.chip-cmd rect{fill:var(--sunken);stroke:none}
.chip-machine rect{fill:var(--accent-soft);stroke:var(--accent);stroke-width:.8}.chip-machine .chip-t{fill:var(--accent-ink);font-weight:700}
.chip-human rect{stroke-dasharray:3 2}
.chip-unknown rect{stroke:var(--muted);stroke-dasharray:1 2}
.chip-ng rect{fill:var(--crit-soft);stroke:var(--crit)}.chip-ng .chip-t{fill:var(--crit-ink)}
.chip-more rect{fill:none;stroke:none}.chip-more .chip-t{fill:var(--muted)}
.ev-k{font-size:12.5px;font-weight:700;fill:var(--muted)}
.ev-track{fill:var(--dot-off)}
.ev-ops{fill:var(--accent)}.ev-all{fill:var(--good)}.ev-part{fill:var(--warn)}
.ev-v{font-size:13px;font-weight:700;fill:var(--ink)}
.ev-sub{font-size:12.5px;fill:var(--ink-2)}
.ev-t{font-size:13px;fill:var(--ink-2)}.ev-ok{fill:var(--good-ink);font-weight:700}.ev-warn{fill:var(--warn-ink);font-weight:700}
.ch{display:block;width:100%;height:auto}
.ch-grid{stroke:var(--line-2);stroke-width:1;stroke-dasharray:1 4;stroke-linecap:round}.ch-axis{stroke:var(--line-2);stroke-width:1}
.ch-tick{font-size:12px;fill:var(--muted)}
.ch-threshold{stroke:var(--ink-2);stroke-width:1.4;stroke-dasharray:5 4}
.ch-line{fill:none;stroke-width:2;stroke-linejoin:round}
.ch-dot{stroke:var(--panel);stroke-width:2}
.ch-hit,.mv-hit{fill:transparent}
.ch-end{font-size:12px;font-weight:700;fill:var(--ink-2)}
.mv-zebra{fill:var(--zebra)}
.mv-no{fill:var(--sunken)}.mv-no-gate{fill:var(--accent)}
.mv-no-t{font-size:12.5px;font-weight:700;fill:var(--ink-2)}.mv-no-t-gate{fill:var(--on-accent)}
.mv-row{font-size:13px;fill:var(--ink-2)}.mv-row-gate{fill:var(--accent-ink);font-weight:700}
.mv-grid{stroke:var(--line-2);stroke-width:1;stroke-dasharray:1 4;stroke-linecap:round}
.mv-tick{font-size:12px;fill:var(--muted)}
.mv-link{stroke-width:1.2;opacity:.6;stroke-dasharray:2 2}
.mv-run{fill:var(--panel)}
.mv-ng circle{fill:var(--crit);stroke:var(--panel);stroke-width:1.5}.mv-ng path{stroke:var(--on-crit);stroke-width:1.6;stroke-linecap:round;fill:none}
.mv-out{fill:var(--panel);stroke:var(--crit);stroke-width:2}
.mv-pt{cursor:pointer}.mv-pt:focus{outline:none}.mv-pt:focus-visible .mv-hit,.mv-pt.is-on .mv-hit{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:2 2}
.mv-pop{position:fixed;z-index:50;left:0;top:0;width:max-content;max-width:min(480px,calc(100vw - 32px));padding:10px 12px;background:var(--panel);
color:var(--ink);border:1px solid var(--line-2);border-radius:6px;box-shadow:var(--shadow);font:12.5px/1.6 var(--mono);pointer-events:none}
.mv-pop.is-pinned{pointer-events:auto;border-color:var(--ink-2)}
.pop{border-left:3px solid var(--accent);padding-left:10px;display:grid;gap:6px}.pop-ng,.pop-out{border-left-color:var(--crit)}
.pop-h{display:flex;flex-wrap:wrap;gap:4px}
.pop-k{font-weight:700;padding:0 7px;border-radius:3px;background:var(--accent-soft);color:var(--accent-ink)}
.pop-k-ng,.pop-k-out{background:var(--crit-soft);color:var(--crit-ink)}
.pop-m{color:var(--ink-2)}.pop-m .sw{width:14px;margin-right:6px}
.pop-c{display:flex;flex-wrap:wrap;gap:4px}.pop-c code{font-size:12.5px;font-weight:700;padding:0 6px;border-radius:3px;background:var(--sunken);color:var(--ink)}
.pop pre{margin:0;max-height:220px;padding:8px 10px;border-left:0;font-size:12.5px;line-height:1.55;overflow-wrap:anywhere}
.pop mark{background:var(--crit-soft);color:var(--crit-ink);font-weight:700;border-radius:2px;padding:0 2px}
.pop dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 12px;margin:0}.pop dt{color:var(--muted)}.pop dd{margin:0;min-width:0;overflow-wrap:anywhere}
.pop dd code{font-size:12.5px;color:var(--crit-ink)}
.pop-f{color:var(--muted);font-size:12px}.pop .pin-on,.mv-pop.is-pinned .pin-off{display:none}.mv-pop.is-pinned .pin-on{display:inline}
.term{border-bottom:1px dotted var(--accent);cursor:help}.term:hover,.term.is-on{color:var(--accent-ink)}
th small{display:block;font-weight:400;font-size:11.5px;color:var(--muted)}
td.mdl{font-size:13px;white-space:nowrap}td.mdl code{font-size:12.5px;font-weight:700}td.mdl .eff{display:block;color:var(--ink-2)}td.mdl small{display:block}
.mdl-s{font-size:12.5px;color:var(--ink-2);padding:0 8px;border-radius:3px;background:var(--sunken)}
.fk{font:inherit;font-size:13.5px;display:inline-flex;gap:8px;align-items:center;padding:2px 10px 2px 6px;border:1px dashed transparent;border-radius:4px;
background:none;color:var(--ink-2);cursor:pointer;transition:opacity .2s}
.fk:hover{border-color:var(--line-2);color:var(--ink)}.fk[aria-pressed="true"]{border-style:solid;border-color:var(--accent);background:var(--accent-soft);color:var(--ink)}
.fk.is-dim{opacity:.45}.fk .sw{margin-right:0}
.mv .s1,.mv .s2,.mv .s3,.mv .s4,.mv .s5,.mv .s6,.ch .s1,.ch .s2,.ch .s3,.ch .s4,.ch .s5,.ch .s6{transition:opacity .22s}
.mv .is-dim,.ch .is-dim{opacity:.1}
.ch-line.is-lit{stroke-width:3.4}.ch-end.is-lit{fill:var(--ink)}.mv-link.is-lit{opacity:1;stroke-width:1.8}
.fx{position:fixed;inset:0;z-index:60;pointer-events:none}
.tabs button.is-pop{animation:tab-pop .46s cubic-bezier(.3,1.7,.5,1)}
.tabs button.is-pop::before{animation:dot-spin .46s cubic-bezier(.3,1.6,.5,1)}
.tabs button.is-pop::after{animation:line-grow .4s cubic-bezier(.3,1.5,.5,1) both}
.seg button.is-pop,.fk.is-pop{animation:squish .48s cubic-bezier(.3,1.7,.5,1)}
.seg button.is-pop .cnt{display:inline-block;animation:hop .55s ease-out}
.pane.is-in{animation:pane-in .34s steps(5,end)}
@keyframes tab-pop{0%{transform:none}30%{transform:translateY(-2px) scale(1.08)}60%{transform:translateY(1px) scale(.97)}100%{transform:none}}
@keyframes dot-spin{0%{transform:none}50%{transform:rotate(135deg) scale(1.8)}100%{transform:rotate(360deg)}}
@keyframes line-grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes squish{0%{transform:none}25%{transform:scale(1.15,.8)}55%{transform:scale(.93,1.1)}80%{transform:scale(1.03,.98)}100%{transform:none}}
@keyframes hop{30%{transform:translateY(-7px) rotate(-10deg)}60%{transform:translateY(1px) rotate(4deg)}100%{transform:none}}
@keyframes pane-in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
div.is-target,details.is-target,section.is-target,td.is-target{animation:target-flash 1.8s ease-out}
tr.is-target > td{animation:row-flash 1.8s ease-out}
g.is-target .wf-card{animation:card-flash 1.8s ease-out}
@keyframes target-flash{0%,36%,72%{outline:3px dashed var(--accent);outline-offset:3px;background-color:var(--accent-soft)}
18%,54%{outline:3px dashed transparent;outline-offset:7px}100%{outline:3px dashed transparent;outline-offset:3px}}
@keyframes row-flash{0%,50%{background-color:var(--accent-soft);box-shadow:inset 0 2px 0 var(--accent),inset 0 -2px 0 var(--accent)}100%{box-shadow:none}}
@keyframes card-flash{0%,25%,50%{stroke:var(--accent);stroke-width:4}12%,37%{stroke-width:1}100%{stroke-width:1}}
""" + SERIES_CSS + """
@media (max-width:1180px){.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}.charts{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:860px){.app{grid-template-columns:minmax(0,1fr)}.rail{position:static;height:auto;border-right:0;border-bottom:1px dashed var(--line-2);
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}.nv-sub{display:none}
main{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:18px 40px}
.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.charts{grid-template-columns:minmax(0,1fr)}.card{padding:16px}
.top{grid-template-columns:auto minmax(0,1fr);padding:16px}.theme{grid-column:1/-1;justify-self:start}
.top h1{font-size:22px}.sk-head h2{font-size:30px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

SCRIPT = """
(function(){
var root=document.documentElement,KEY='skill-catalog-theme';
function setTheme(v){if(v==='light'||v==='dark'){root.setAttribute('data-theme',v)}else{root.removeAttribute('data-theme');v='auto'}
document.querySelectorAll('[data-theme-set]').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.themeSet===v))});
try{localStorage.setItem(KEY,v)}catch(e){}}
var saved='auto';try{saved=localStorage.getItem(KEY)||'auto'}catch(e){}
setTheme(saved);
document.querySelectorAll('[data-theme-set]').forEach(function(b){b.addEventListener('click',function(){setTheme(b.dataset.themeSet)})});
var reduce=!!(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches),ready=false;
function bounce(el){if(reduce)return;el.classList.remove('is-pop');void el.offsetWidth;el.classList.add('is-pop')}
document.addEventListener('animationend',function(e){if(['tab-pop','squish','pane-in'].indexOf(e.animationName)>=0)e.target.classList.remove('is-pop','is-in')});
function show(group,id){document.querySelectorAll('[data-pane]').forEach(function(p){if(p.dataset.pane!==group)return;var was=p.hidden;p.hidden=p.id!==id;
if(ready&&was&&!p.hidden&&!reduce){p.classList.remove('is-in');void p.offsetWidth;p.classList.add('is-in')}});
document.querySelectorAll('[data-for]').forEach(function(b){if(b.dataset.for!==group)return;var on=b.dataset.show===id;
b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1})}
var groups=[];
document.querySelectorAll('[data-for]').forEach(function(b){if(groups.indexOf(b.dataset.for)<0){groups.push(b.dataset.for);show(b.dataset.for,b.dataset.show)}
b.addEventListener('click',function(){show(b.dataset.for,b.dataset.show);bounce(b);if(b.hasAttribute('data-hash'))history.replaceState(null,'','#'+b.dataset.show)})});
/* 飛び先を見せる: 囲んでいるタブ・ラウンドを開き、閉じた details を開いて、真ん中に出して点滅させる */
function reveal(el){for(var p=el.parentElement;p;p=p.parentElement){if(p.dataset&&p.dataset.pane&&p.hidden)show(p.dataset.pane,p.id);if(p.tagName==='DETAILS')p.open=true}}
function go(id,quiet){var el=document.getElementById(id);if(!el)return false;reveal(el);
if(el.dataset&&el.dataset.pane){show(el.dataset.pane,id);var bar=el.parentElement.querySelector('.tabs');(bar||el).scrollIntoView({block:'start'});return true}
el.scrollIntoView({block:'center',behavior:reduce||quiet?'auto':'smooth'});settle(el,function(){
el.classList.remove('is-target');void el.getBoundingClientRect();el.classList.add('is-target');setTimeout(function(){el.classList.remove('is-target')},1900);
if(!quiet){var r=el.getBoundingClientRect(),x=r.left+Math.min(r.width,64)/2,y=r.top+r.height/2;burst(x,y,26,true);say(x+10,y-16,'ここ!')}});return true}
function settle(el,fn){var last=null,n=0;setTimeout(function check(){var top=el.getBoundingClientRect().top;  /* スクロールが止まってから知らせる */
if(last!==null&&Math.abs(top-last)<1||++n>40){fn();return}last=top;setTimeout(check,70)},120)}
function fromHash(){var id=decodeURIComponent(location.hash.slice(1));if(id)go(id,true)}
window.addEventListener('hashchange',fromHash);fromHash();ready=true;
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href^="#"]');if(!a)return;
var id=decodeURIComponent(a.getAttribute('href').slice(1));if(!document.getElementById(id))return;e.preventDefault();history.replaceState(null,'','#'+id);go(id)});
/* 系列を浮かび上がらせる: 凡例に重ねると仮に、押すと固定。ほかの系列を薄くし、選んだ系列を前に描き直す */
var SER=[1,2,3,4,5,6].map(function(i){return 'svg.mv .s'+i+',svg.ch .s'+i}).join(',');
function lit(scope,key){scope.querySelectorAll(SER).forEach(function(el){var on=!key||el.classList.contains(key);
el.classList.toggle('is-dim',!on);el.classList.toggle('is-lit',!!key&&on);if(key&&on)el.parentNode.appendChild(el)});
scope.querySelectorAll('.fk').forEach(function(b){b.classList.toggle('is-dim',!!key&&b.dataset.focus!==key)})}
document.querySelectorAll('[data-focus-scope]').forEach(function(scope){scope.querySelectorAll('.fk').forEach(function(b){
b.addEventListener('pointerenter',function(){lit(scope,b.dataset.focus)});
b.addEventListener('pointerleave',function(){lit(scope,scope.dataset.pinned||'')});
b.addEventListener('click',function(){var k=scope.dataset.pinned===b.dataset.focus?'':b.dataset.focus;scope.dataset.pinned=k;
scope.querySelectorAll('.fk').forEach(function(x){x.setAttribute('aria-pressed',String(!!k&&x.dataset.focus===k))});lit(scope,k);bounce(b)})})});
/* クリックで点が弾ける。続けて押すと数が増え、まれに輪になる */
var cv=null,ctx=null,dots=[],words=[],raf=0,combo=0,last=0;
function fit(){var d=window.devicePixelRatio||1;cv.width=innerWidth*d;cv.height=innerHeight*d;cv.style.width=innerWidth+'px';cv.style.height=innerHeight+'px';ctx.setTransform(d,0,0,d,0,0)}
function layer(){if(cv)return true;cv=document.createElement('canvas');ctx=cv.getContext&&cv.getContext('2d');if(!ctx)return false;
cv.className='fx';cv.setAttribute('aria-hidden','true');document.body.appendChild(cv);fit();window.addEventListener('resize',fit);return true}
function palette(){var s=getComputedStyle(root);return ['--accent','--s1','--s2','--s3','--s4','--s5','--warn','--good'].map(function(k){return s.getPropertyValue(k).trim()||'#d97757'})}
function tick(){ctx.clearRect(0,0,innerWidth,innerHeight);
dots=dots.filter(function(p){p.t++;p.vy+=.24;p.vx*=.98;p.x+=p.vx;p.y+=p.vy;var k=1-p.t/p.max;if(k<=0)return false;
var s=p.wob?p.s*(.55+.45*Math.abs(Math.sin(p.t/3))):p.s;ctx.globalAlpha=Math.min(1,k*1.7);ctx.fillStyle=p.c;ctx.fillRect(Math.round(p.x-s/2),Math.round(p.y-s/2),s,s);return true});
words=words.filter(function(w){w.t++;var k=1-w.t/w.max;if(k<=0)return false;var x=w.x+(w.t<10?Math.sin(w.t*1.7)*2.5:0),y=w.y-w.t*.7;
ctx.globalAlpha=Math.min(1,k*2);ctx.textAlign='center';ctx.font='18px DotGothic16, monospace';ctx.lineWidth=5;ctx.lineJoin='round';
ctx.strokeStyle=w.bg;ctx.strokeText(w.text,x,y);ctx.fillStyle=w.c;ctx.fillText(w.text,x,y);return true});
ctx.globalAlpha=1;raf=dots.length||words.length?requestAnimationFrame(tick):0}
function burst(x,y,n,ring){if(reduce||!layer())return;var pal=palette();
for(var i=0;i<n;i++){var a=ring?i/n*Math.PI*2:Math.random()*Math.PI*2,v=ring?4.6+(i%2)*1.4:1.4+Math.random()*4.6;
dots.push({x:x,y:y,vx:Math.cos(a)*v,vy:Math.sin(a)*v-(ring?1:2.4),s:[3,4,5,6][i%4],c:pal[(i+combo)%pal.length],t:0,max:34+Math.random()*26,wob:Math.random()<.35})}
if(!raf)raf=requestAnimationFrame(tick)}
function say(x,y,text){if(reduce||!layer())return;var bg=getComputedStyle(root).getPropertyValue('--panel').trim()||'#fff';
words.push({x:x,y:y,text:text,c:palette()[0],bg:bg,t:0,max:56});if(!raf)raf=requestAnimationFrame(tick)}
document.addEventListener('click',function(e){if(reduce)return;var sel=window.getSelection&&getSelection();if(sel&&!sel.isCollapsed&&String(sel))return;
var x=e.clientX,y=e.clientY;if(!e.detail&&e.target.getBoundingClientRect){var r=e.target.getBoundingClientRect();x=r.left+r.width/2;y=r.top+r.height/2}
var now=Date.now();combo=now-last<650?combo+1:1;last=now;burst(x,y,10+Math.min(combo,8)*3,false);
if(combo>=3)say(x,y-14,'×'+combo);if(Math.random()<1/24){burst(x,y,30,true);say(x,y-34,'✻ ラッキー')}},true);
document.querySelectorAll('[role=tablist]').forEach(function(list){list.addEventListener('keydown',function(e){
if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;var tabs=Array.prototype.slice.call(list.querySelectorAll('[role=tab]'));
var i=tabs.indexOf(document.activeElement);if(i<0)return;var n=tabs[(i+(e.key==='ArrowRight'?1:tabs.length-1))%tabs.length];n.focus();n.click()})});
document.querySelectorAll('[data-filter-for]').forEach(function(bar){var table=document.getElementById(bar.dataset.filterFor);
bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){var v=b.dataset.filter,head=null,any=false;bounce(b);
bar.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',String(x===b))});
table.querySelectorAll('tbody tr').forEach(function(r){if(r.classList.contains('grp')){if(head)head.hidden=!any;head=r;any=false;return}
var on=v==='all'||r.dataset.group===v;r.hidden=!on;if(on)any=true});if(head)head.hidden=!any})})});
var box=document.getElementById('filter');
if(box)box.addEventListener('input',function(){var q=box.value.trim().toLowerCase();
document.querySelectorAll('[data-search]').forEach(function(el){el.hidden=q!==''&&el.dataset.search.indexOf(q)<0})});
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
function pick(){var code=b.previousElementSibling,r=document.createRange();r.selectNodeContents(code);var s=getSelection();s.removeAllRanges();s.addRange(r)}
function done(){b.textContent='コピーした';setTimeout(function(){b.textContent='コピー'},1600)}
if(navigator.clipboard){navigator.clipboard.writeText(b.dataset.copy).then(done,pick)}else{pick()}})});
var pop=null,cur=null,pinned=false;
function near(e){return e.target&&e.target.closest?e.target.closest('[data-pop]'):null}
function place(){if(!cur)return;var r=cur.getBoundingClientRect(),vw=document.documentElement.clientWidth,vh=window.innerHeight;
var w=pop.offsetWidth,h=pop.offsetHeight,x=Math.max(8,Math.min(r.left+r.width/2-w/2,vw-w-8)),y=r.bottom+10;
if(y+h>vh-8)y=Math.max(8,r.top-h-10);pop.style.left=x+'px';pop.style.top=y+'px'}
function openPop(el,pin){if(!pop){pop=document.createElement('div');pop.id='mv-pop';pop.className='mv-pop';pop.setAttribute('role','tooltip');document.body.appendChild(pop)}
if(cur!==el){if(cur){cur.classList.remove('is-on');cur.removeAttribute('aria-describedby')}cur=el;pop.innerHTML=el.getAttribute('data-pop')}
pinned=pin;pop.hidden=false;pop.classList.toggle('is-pinned',pin);el.classList.add('is-on');el.setAttribute('aria-describedby','mv-pop');place()}
function closePop(){if(!cur)return;pop.hidden=true;cur.classList.remove('is-on');cur.removeAttribute('aria-describedby');cur=null;pinned=false}
document.addEventListener('pointerover',function(e){var el=near(e);if(el&&!pinned)openPop(el,false)});
document.addEventListener('pointerout',function(e){var el=near(e);if(el&&!pinned&&!(e.relatedTarget&&el.contains(e.relatedTarget)))closePop()});
document.addEventListener('focusin',function(e){var el=near(e);if(el&&!pinned)openPop(el,false)});
document.addEventListener('focusout',function(e){if(!pinned&&cur&&e.target===cur)closePop()});
document.addEventListener('click',function(e){var el=near(e);if(el){if(pinned&&cur===el)closePop();else openPop(el,true);return}if(pinned&&!pop.contains(e.target))closePop()});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){closePop();return}
var el=document.activeElement;if((e.key==='Enter'||e.key===' ')&&el&&el.hasAttribute&&el.hasAttribute('data-pop')){e.preventDefault();openPop(el,true)}});
window.addEventListener('scroll',function(){if(pinned)place();else closePop()},true);
window.addEventListener('resize',place);
})();
"""

GENERATOR = '<meta name="generator" content="skill-foundation catalog.py">'  # 書いたページの印。今は無いスキルのページは、印のあるものだけを消す


def page_slugs(skills: list[dict]) -> list[str]:
    """ページのファイル名（.html の前）。同じ名前のスキルは、2つ目から置き場のパスを名前にする。"""
    used, slugs = set(), []
    for skill in skills:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", skill["name"])
        if slug in used:
            slug = re.sub(r"[^a-z0-9]+", "-", skill["path"].lower()).strip("-")
        while slug in used:
            slug += "-2"
        used.add(slug)
        slugs.append(slug)
    return slugs


def search_text(skill: dict) -> str:
    spec = skill["spec"]
    return " ".join([skill["name"], spec.get("title", ""), spec.get("purpose", ""), " ".join(skill["decisions"])]).lower()


def skill_marks(sm: dict) -> str:
    return (badge(sm["probe"][0], "違反の検出") + badge(sm["conv"][0], "収束テスト")
            + badge(sm["seal"][0] if sm["seal"][0] != "none" else "warn", "改変チェック"))


def rail(project: Path, entries: list[tuple], others: list[dict], here: str | None, to_pages: str, to_index: str) -> str:
    """左の一覧。here は開いているページ（一覧なら None）。to_pages・to_index はページ・一覧へのリンクの前に付ける相対パス。"""
    names = Counter(skill["name"] for skill, _, _ in entries)
    nav = []
    for skill, slug, sm in entries:
        name = esc(skill["name"])
        current = slug == here
        place = f'<span class="pl">{esc(skill["path"])}</span>' if names[skill["name"]] > 1 else ""
        subs = ('<ul class="nv-sub">' + "".join(f'<li><a href="#skill-{name}-{key}">{label}</a></li>' for key, label in TABS) + "</ul>"
                if current else "")
        mark = ' aria-current="page"' if current else ""
        nav.append(f'<li data-search="{esc(search_text(skill))}"><a class="nv-skill" href="{esc(to_pages + slug)}.html"{mark}>'
                   f'<span class="nm">{name}</span><span class="tl">{esc(skill["spec"].get("title", ""))}</span>'
                   f'{place}<span class="marks">{skill_marks(sm)}</span></a>{subs}</li>')
    nav_others = "".join(f'<li class="nv-other" data-search="{esc(o["name"].lower())}"><a href="{esc(to_index)}#others">{esc(o["name"])}</a></li>'
                         for o in others)
    others_html = f'<p class="nv-h">skill-foundation で作っていないスキル</p><ul class="nv">{nav_others}</ul>' if others else ""
    home = f'<a class="nv-home" href="{esc(to_index)}">← スキルの一覧</a>' if here else ""
    return (f'<aside class="rail"><div class="brand">{pixel_mark(3)}<span><b>スキルのカタログ</b><span>{esc(project.name)}</span></span></div>'
            '<input id="filter" class="search" type="search" placeholder="名前・目的・ルールID で絞る" aria-label="スキルを絞る">'
            f'{home}<nav aria-label="スキル"><ul class="nv">{"".join(nav)}</ul>{others_html}</nav></aside>')


def page(title: str, project: Path, when: str, side: str, body: str) -> str:
    command = f"python3 {rel_to(_lib.FOUNDATION_DIR / 'scripts/catalog.py', project)} --project ."
    themes = "".join(f'<button type="button" data-theme-set="{v}" aria-pressed="{str(v == "auto").lower()}">{label}</button>'
                     for v, label in (("auto", "自動"), ("light", "ライト"), ("dark", "ダーク")))
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{GENERATOR}
<title>{esc(title)}</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}"><style>{CSS}</style></head>
<body><div class="app">
{side}
<main><div class="wrap">
<header class="top">{pixel_mark(4)}<div><h1>スキルのカタログ</h1><p class="when"><code>{esc(project.as_posix())}</code>・書いた日時 {esc(when)}</p>
<p class="regen">最新の記録で作り直す: <code>{esc(command)}</code><button type="button" class="btn" data-copy="{esc(command)}">コピー</button>
<span class="muted">スキルのファイルと検証の記録を読み直し、一覧とすべてのページを作る。skill-foundation の run.py finish も、終えるたびに同じことをする</span></p></div>
<div class="theme" role="group" aria-label="表示の色">{themes}</div></header>
{body}
<footer>skill-foundation の scripts/catalog.py が書いた。内容はすべてスキルのファイルと検証の記録から集計している。</footer>
</div></main></div><script>{SCRIPT}</script></body></html>
"""


def index_card(skill: dict, slug: str, sm: dict, to_pages: str) -> str:
    counts = Counter(lv for lv, *_ in attention_items(skill, sm))
    attn = ("・".join(f'<span class="{lv}">{ATTN_LEVELS[lv]} {counts[lv]} 件</span>' for lv in ATTN_LEVELS if counts[lv])
            or '<span class="good">問題なし</span>')
    return (f'<a class="card sk-card" href="{esc(to_pages + slug)}.html" data-search="{esc(search_text(skill))}">'
            f'<span class="nm">{esc(skill["name"])}</span><span class="tl">{esc(skill["spec"].get("title", ""))}</span>'
            f'<span class="pl"><code>{esc(skill["path"])}</code></span><span class="marks">{skill_marks(sm)}</span>'
            f'<span class="at"><b>先に見るもの</b>{attn}</span></a>')


def render_index(project: Path, when: str, entries: list[tuple], others: list[dict], broken: list[tuple[str, str]], to_pages: str) -> str:
    cards = "".join(index_card(skill, slug, sm, to_pages) for skill, slug, sm in entries)
    skills_html = (f'<section class="idx" id="skills"><h2>skill-foundation で作ったスキル</h2>'
                   f'<p class="muted">スキルごとのページに、ワークフロー図と独立検証の記録を載せる。カードを押すとページを開く。</p>'
                   f'<div class="idx-grid">{cards}</div></section>' if entries else
                   '<p class="muted">skill-foundation で作ったスキル（dev/spec.json がある）が無い。</p>')
    other_cards = "".join(f'<div class="card" data-search="{esc(o["name"].lower())}"><b>{esc(o["name"])}</b><div class="muted"><code>{esc(o["path"])}</code></div>'
                          f'<p>{inline(o["description"])}</p></div>' for o in others)
    others_html = (f'<section class="others" id="others"><h2>skill-foundation で作っていないスキル</h2>'
                   f'<p class="muted">dev/spec.json が無いため、SKILL.md の name と description だけを載せる。</p><div class="others-grid">{other_cards}</div></section>'
                   if others else "")
    broken_items = "".join(f"<li><code>{esc(n)}</code>: {esc(why)}</li>" for n, why in broken)
    broken_html = f'<section class="card" id="broken"><h3>読めなかったスキル</h3><ul>{broken_items}</ul></section>' if broken else ""
    side = rail(project, entries, others, None, to_pages, "")
    return page("スキルのカタログ", project, when, side, skills_html + broken_html + others_html)


def render_skill_page(project: Path, when: str, entries: list[tuple], others: list[dict], skill: dict, slug: str, to_index: str) -> str:
    side = rail(project, entries, others, slug, "", to_index)
    return page(f"{skill['name']} | スキルのカタログ", project, when, side, section_skill(skill))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="プロジェクトのルート")
    parser.add_argument("--out", help=f"一覧の HTML のパス（既定: <プロジェクト>/{_lib.CATALOG_REL}）。スキルごとのページは、隣の同じ名前のディレクトリに書く")
    parser.add_argument("--skill", action="append", default=[], help="載せるスキルのディレクトリ（.claude/skills と .agents/skills の外にあるもの）")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"プロジェクトがありません: {project}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else project / _lib.CATALOG_REL
    if out.suffix != ".html":
        print(f"--out は .html で終わるパスにしてください: {out}", file=sys.stderr)
        return 2
    pages = out.with_suffix("")  # catalog.html なら catalog/
    skills, others, broken = [], [], []
    for directory in find_skills(project, [Path(p).resolve() for p in args.skill]):
        if (directory / _lib.SPEC_REL).is_file():
            try:
                skills.append(load_skill(directory, project))
            except Exception as exc:  # 1つのスキルが読めなくても、ほかのスキルのカタログは書く
                broken.append((directory.name, f"{type(exc).__name__}: {exc}"))
            continue
        fm, _ = _lib.parse_frontmatter((directory / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        others.append({"name": (fm or {}).get("name") or directory.name, "path": rel_to(directory, project),
                       "description": (fm or {}).get("description", "")})
    skills.sort(key=lambda s: s["name"])
    others.sort(key=lambda o: o["name"])
    places: dict[str, list[str]] = {}
    for item in skills + others:  # Codex 用の置き場に複製を置くと、同じスキルが2つ載る
        places.setdefault(item["name"], []).append(item["path"])
    for skill in skills:
        skill["twins"] = [p for p in places[skill["name"]] if p != skill["path"]]
    entries = list(zip(skills, page_slugs(skills), [summary(s) for s in skills]))
    when = rt.now()
    files = {pages / f"{slug}.html": render_skill_page(project, when, entries, others, skill, slug, f"../{out.name}") for skill, slug, _ in entries}
    files[out] = render_index(project, when, entries, others, broken, f"{pages.name}/")
    removed = []
    try:
        pages.mkdir(parents=True, exist_ok=True)
        if out.parent == project / rt.RUNS_DIRNAME and not (out.parent / ".gitignore").exists():
            (out.parent / ".gitignore").write_text("*\n", encoding="utf-8")  # 実行記録と同じく git から外す
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")
        for old in sorted(pages.glob("*.html")):
            if old not in files and GENERATOR in old.read_text(encoding="utf-8", errors="replace")[:1000]:
                old.unlink()
                removed.append(old.name)
    except OSError as exc:
        print(f"## カタログ\n\n- 書けなかった（`{rel_to(out, project)}`: {exc}）")
        return 1
    lines = ["## カタログ", "", f"- `{rel_to(out, project)}` に一覧を書いた。ブラウザで開いて見る"]
    if entries:
        listed = "、".join(f"`{skill['name']}`（`{rel_to(pages / (slug + '.html'), project)}`）" for skill, slug, _ in entries)
        lines.append(f"- スキル {len(entries)} 個のワークフロー図と独立検証の記録は、スキルごとのページに書いた: {listed}")
    if others:
        other_names = "、".join(f"`{o['name']}`" for o in others)
        lines.append(f"- skill-foundation の形でないスキル {len(others)} 個（{other_names}）は、一覧に名前と説明だけを載せた")
    if removed:
        lines.append(f"- 今は無いスキルのページ {len(removed)} 個を消した: " + "、".join(f"`{n}`" for n in removed))
    lines += [f"- 読めなかったスキル: `{n}`（{why}）" for n, why in broken]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
