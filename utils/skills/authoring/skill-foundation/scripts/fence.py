#!/usr/bin/env python3
"""収束テストの外への操作の停止: 独立エージェントの道具の呼び出しが、作業ディレクトリ（lab）の外に触れたら止める（PreToolUse の hook）。

skill-foundation だけが使う。作るスキルにはコピーしない（hook.py と違い、収束テストの一時プロジェクトのための hook）。
convergence.py prepare が各 lab に印（.skill-runs/_fence/lab.json）を置き、runner ごとに次のように登録する。

  subagent: 専用のエージェント型 skill-foundation-tester の frontmatter（--agent）。最初に触れた lab にエージェントを結びつける
  claude  : lab の .claude/settings.json の全道具（--lab <lab>）
  codex   : lab の .codex/hooks.json の Bash と apply_patch（--lab <lab>）

止める操作:
  - lab の外のパス（道具のパスと、Bash のコマンドに出る /…・~・$HOME・lab の外へ出る ..）。
    中身を書くだけのヒアドキュメント（cat・tee）の本文と URL は見ない
  - ほかのエージェントの lab
  - --agent だけ: `cd <lab> && ` で始まらない Bash、path を指定しない Glob・Grep（呼び出し元のプロジェクトで動く）、
    Skill（呼び出し元のプロジェクトのスキルを読む）
通す操作: システムのパス（/usr・/bin・/dev など）と、Claude Code が長い出力を逃がした tool-results
書き換え: --agent の Bash の先頭に `export TMPDIR=<lab>/.skill-runs/_fence/tmp &&` を足す（入力にパスが出ない一時ファイルを
          lab に入れる）。permissionDecision は付けず、書き換えた後のコマンドも、ふだんどおり権限の判定を受ける
止めた操作は <lab>/.skill-runs/_fence/log.jsonl に書く。止める理由の先頭の目印で、convergence.py が traces.json の操作に印を付ける。
判定に失敗したときも止める（Codex は hook の失敗で操作を進めるため、例外を受けて deny を返す）。

終了コード: 0（判定を標準出力に書いた。止めるときも 0）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

FENCE_REL = ".skill-runs/_fence"  # lab の中の fence.py の置き場。convergence.py diff は、変わったファイルに数えない
MARK = "lab.json"
SYSTEM = ("/usr", "/bin", "/sbin", "/opt", "/System", "/Library", "/dev", "/etc", "/private/etc")
TOOL_RESULTS = re.compile(r"/\.claude/projects/[^/]+/[^/]+/tool-results/")
URL = re.compile(r"\b[A-Za-z][\w+.-]*://\S*")
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][\w-]*)\1")
ABSOLUTE = re.compile(r"(?<![\w.$/~}\\^-])(~/[^\s'\"`;|&()<>]*|~(?![\w/])|\$\{?HOME\b\}?[^\s'\"`;|&()<>]*|/[^\s'\"`;|&()<>]+)")
WORD = re.compile(r"[^\s'\"`;|&()<>=]+")
UP = re.compile(r"(?:^|/)\.\.(?:/|$)")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", re.M)
CD = re.compile(r"^\s*cd\s+('[^']*'|\"[^\"]*\"|[^\s;&|]+)\s*&&")
TEXT = {
    "ja": {"tag": "[skill-foundation の fence.py] ", "known": "作業ディレクトリ {dir} ", "unknown": "依頼文にある作業ディレクトリ",
           "dir": "<作業ディレクトリ>",
           "outside": "{path} は{lab}の外です。作業ディレクトリの外は読まず、変えません。一時ファイルは {tmp} に"
                      "置いてください（パスでない文字列なら、ファイルの中身は Write、文字列の検索は Grep の道具で扱ってください）",
           "other": "{path} は、ほかのエージェントの作業ディレクトリです。あなたの作業ディレクトリは {dir} です",
           "cd": "Bash は毎回 `cd {dir} && ` を先頭に付けて実行してください（cd は次の Bash に残りません）",
           "where": "{tool} の path に、{lab}の中の絶対パスを指定してください（省くと作業ディレクトリの外を探します）",
           "skill": "Skill の道具は使いません。依頼文にある SKILL.md を Read で読み、書かれた手順に従ってください",
           "error": "fence.py の判定に失敗したので、この操作を止めました（{error}）"},
    "en": {"tag": "[skill-foundation fence] ", "known": "the working directory {dir}",
           "unknown": "the working directory given in the request", "dir": "<working directory>",
           "outside": "{path} is outside {lab}. Do not read or change anything outside it. Put temporary "
                      "files in {tmp} (if it is not a path, write file contents with Write and search text with Grep)",
           "other": "{path} is another agent's working directory. Your working directory is {dir}",
           "cd": "Prefix every Bash command with `cd {dir} && ` (cd does not carry over to the next Bash call)",
           "where": "Set the path of {tool} to an absolute path inside {lab} (without it, it searches outside)",
           "skill": "Do not use the Skill tool. Read the SKILL.md given in the request with Read and follow its steps",
           "error": "The fence could not judge this call, so it was blocked ({error})"},
}


def real(text: str, base: Path) -> Path:
    """コマンドや道具に出たパスを、シンボリックリンクを解いた絶対パスにする。glob の文字から後ろは見ない。"""
    text = re.sub(r"^(?:~|\$\{?HOME\}?)(?=/|$)", str(Path.home()), text.strip("'\""))
    text = re.sub(r"(?<=[^./])[.,:]+$", "", text)  # 文の終わりの句読点。`..` は残す
    text = re.split(r"[*?\[{]", text, maxsplit=1)[0] or "."
    return Path(os.path.realpath(os.path.normpath(os.path.join(str(base), text))))


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def allowed_anywhere(path: Path) -> bool:
    text = path.as_posix()
    return any(text == s or text.startswith(s + "/") for s in SYSTEM) or bool(TOOL_RESULTS.search(text + "/"))


def find_lab(path: Path) -> Path | None:
    """path を含む一番外側の lab。lab の中で収束テストを作り直したとき（入れ子の lab）も、外側を自分の lab にする。"""
    found = None
    for p in (path, *path.parents):
        if (p / FENCE_REL / MARK).is_file():
            found = p
    return found


def lab_info(lab: Path | None) -> dict:
    try:
        return json.loads((lab / FENCE_REL / MARK).read_text(encoding="utf-8")) if lab else {}
    except (OSError, ValueError):
        return {}


def tool_paths(tool: str, data: dict) -> tuple[list[str], str | None]:
    """道具の入力に出るパスの文字列と、Bash のコマンド（あれば）。"""
    if tool == "Bash":
        return [], str(data.get("command", ""))
    if tool == "apply_patch":
        return PATCH_FILE.findall(str(data.get("command") or data.get("patch") or data.get("input") or "")), None
    found = [str(data[k]) for k in ("file_path", "notebook_path", "path") if data.get(k)]
    if tool == "Glob" and str(data.get("pattern", "")).startswith(("/", "~")):
        found.append(str(data["pattern"]))
    return found, None


def command_paths(command: str) -> tuple[list[str], list[str]]:
    """コマンドに出る絶対パス（~・$HOME を含む）と、.. を含む相対パス。"""
    kept, ends, skip = [], [], False
    for line in command.splitlines():
        if ends:
            if line.strip() == ends[0]:
                ends.pop(0)
                skip = False
            elif skip:
                continue
            else:
                kept.append(line)
            continue
        kept.append(line)
        for m in HEREDOC.finditer(line):
            segment = re.split(r"&&|;", line[:m.start()])[-1].split()
            ends.append(m.group(2))
            # cat・tee で中身を書くだけの本文は、パスに触れない。インタープリタに渡す本文は、実行されるので見る
            skip = skip or bool(segment) and segment[0] in ("cat", "tee") and "|" not in line
    text = URL.sub(" ", "\n".join(kept))
    absolute = [m.group(1) for m in ABSOLUTE.finditer(text)]
    relative = [w for w in WORD.findall(text) if UP.search(w) and not w.startswith(("/", "~", "$"))]
    return absolute, relative


def binding(lab: Path, key: str) -> Path:
    rnd = Path(lab_info(lab).get("round") or lab.parent)
    return rnd / "_fence" / "agents" / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', key)}.json"


def decide(event: dict, lab: Path | None, agent: bool) -> tuple[str, str, Path | None]:
    """(allow・deny・rewrite, 理由または書き換えたコマンド, 自分の lab)。"""
    tool = str(event.get("tool_name", ""))
    data = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    raw, command = tool_paths(tool, data)
    base = lab or Path(str(event.get("cwd") or os.getcwd()))
    cd_to = None
    relative: list[str] = []
    if command is not None:
        m = CD.match(command)
        if m:
            cd_to = real(m.group(1), base)
            base = cd_to
        absolute, relative = command_paths(command)
        raw += absolute
    paths = [real(p, base) for p in raw] + [real(w, base) for w in relative] + ([cd_to] if cd_to else [])
    paths = [p for p in dict.fromkeys(paths) if not allowed_anywhere(p)]
    mine = lab
    if agent:
        touched = list(dict.fromkeys(x for x in (find_lab(p) for p in paths) if x))
        key = str(event.get("agent_id") or event.get("session_id") or "")
        for candidate in touched:
            try:
                mine = Path(json.loads(binding(candidate, key).read_text(encoding="utf-8"))["lab"])
                break
            except (OSError, ValueError, KeyError):
                continue
        if mine is None and len(touched) == 1 and key:
            mine = touched[0]
            target = binding(mine, key)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"lab": str(mine), "agent_type": event.get("agent_type")}, ensure_ascii=False),
                              encoding="utf-8")
    words = TEXT.get(lab_info(mine).get("language"), TEXT["ja"])
    folder = str(mine) if mine else words["dir"]
    where = words["known"].format(dir=mine) if mine else words["unknown"]
    tmp = f"{folder}/{FENCE_REL}/tmp/"
    for p in paths:
        if mine and inside(p, mine):
            continue
        other = find_lab(p)
        kind = "other" if other and other != mine else "outside"
        return "deny", words[kind].format(path=p, lab=where, dir=folder, tmp=tmp), mine
    if agent and tool == "Skill":
        return "deny", words["skill"], mine
    if agent and tool in ("Glob", "Grep") and not data.get("path") and not raw:
        return "deny", words["where"].format(tool=tool, lab=where), mine
    if agent and command is not None:
        if not (cd_to and mine and inside(cd_to, mine)):
            return "deny", words["cd"].format(dir=folder), mine
        return "rewrite", f"export TMPDIR={shlex.quote(tmp)} && {command}", mine
    return "allow", "", mine


def log(lab: Path | None, event: dict, reason: str) -> None:
    if not lab:
        return
    try:
        with (lab / FENCE_REL / "log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": event.get("tool_name"),
                                "tool_use_id": event.get("tool_use_id"), "agent_id": event.get("agent_id"),
                                "reason": reason}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def deny(reason: str) -> str:
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}}, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=["claude", "codex"], required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent", action="store_true", help="runner subagent（専用のエージェント型の frontmatter から呼ぶ）")
    group.add_argument("--lab", help="runner claude・codex の lab")
    args = parser.parse_args()
    try:
        event = json.loads(sys.stdin.read() or "{}")
        lab = Path(os.path.realpath(args.lab)) if args.lab else None
        verdict, text, mine = decide(event if isinstance(event, dict) else {}, lab, args.agent)
        words = TEXT.get(lab_info(mine).get("language"), TEXT["ja"])
        if verdict == "deny":
            log(mine, event, words["tag"] + text)
            print(deny(words["tag"] + text))
        elif verdict == "rewrite":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                     "updatedInput": {**event["tool_input"], "command": text}}}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001  判定できないときは止める
        print(deny(TEXT["ja"]["tag"] + TEXT["ja"]["error"].format(error=f"{type(exc).__name__}: {exc}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
