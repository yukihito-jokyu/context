#!/usr/bin/env python3
"""利用中の指摘の収集（feedback.py・feedback_review.py・hook.py の収集）を、合成データだけで確かめる。

一時ディレクトリに小さなスキル（共通ランタイムと、テキスト・HTML・画像の出力を持つ契約）を置き、hooks の入力を
直接渡して、次を確かめる（issue #7 の作業2の受け入れ条件）。記録には合成データの印（synthetic）を付け、実ユーザーの
承認と区別する。

  1. 完了後の指摘 → 修正 → 確認画面で承認、の流れで、cases[] に原文・修正前・修正後・承認がそろう
  2. 会話で「OK」と言っただけでは approval が null のまま
  3. 別の送信元・古い画面・表示後にファイルが変わった版・別の版への承認を拒否する
  4. 記録（.skill-feedback/）への直接の編集を拒否し、.skill-feedback/ が Git の管理外になる
  5. hooks を登録しない・収集だけ外す・収集だけ、の登録の形と、hooks が無くても start → check → finish が完了する
  6. feedback.py が例外で落ちても、出力の検査と完了が止まらない（故意に壊した feedback.py で確かめる）
  7. SKILL.md とルールの表に収集の指示を書くと、skill_lint.py が指摘する

使い方:
  python3 feedback_selftest.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

PY = sys.executable
NAME = "fb-demo"
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256))  # UTF-8 として読めない画像の代わり
CONTRACT = {
    "contract_version": 1, "skill": NAME, "language": "ja", "targets": ["claude", "codex"], "inputs": [],
    "outputs": [
        {"id": "notes", "label": "メモ", "path": "docs/notes.md", "rule": "OUT-01", "count": {"max": 1},
         "checks": [{"rule": "OUT-01", "type": "require", "pattern": "^# ", "lines": "first"}]},
        {"id": "page", "label": "ページ", "path": "docs/page.html", "rule": "OUT-01", "required": False, "count": {"max": 1}},
        {"id": "banner", "label": "画像", "path": "docs/banner.png", "rule": "OUT-01", "required": False, "count": {"max": 1},
         "binary": True, "checks": [{"rule": "OUT-01", "type": "require", "pattern": "x"}]},
    ],
    "together": [], "control": {"hooks": True, "max_stop_blocks": 3, "feedback": True},
    "report": {"include_output": None, "rule": "RPT-01", "sections": []},
}


class Lab:
    def __init__(self, temp: Path):
        self.root = temp / "proj"
        self.skill = self.root / ".claude/skills" / NAME
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "assets").mkdir()
        (self.skill / "references").mkdir()
        for script in _lib.RUNTIME_FILES:
            shutil.copy2(_lib.FOUNDATION_DIR / "scripts" / script, self.skill / "scripts" / script)
        for rel in _lib.RUNTIME_ASSETS:
            shutil.copy2(_lib.FOUNDATION_DIR / rel, self.skill / rel)
        (self.skill / "SKILL.md").write_text(f"---\nname: {NAME}\ndescription: 合成データのテスト用\n---\n", encoding="utf-8")
        _lib.write_json(self.skill / "assets/contract.json", CONTRACT)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.env = {**os.environ, "SKILL_FEEDBACK_SYNTHETIC": "1"}

    def run(self, script: str, *args: str) -> tuple[int, str]:
        proc = subprocess.run([PY, str(self.skill / "scripts" / script), *args], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=120)
        return proc.returncode, proc.stdout + proc.stderr

    def hook(self, action: str, event: dict, *flags: str) -> tuple[int, str]:
        proc = subprocess.run([PY, str(self.skill / "scripts/hook.py"), "--platform", "claude", *flags, action],
                              input=json.dumps({"cwd": str(self.root), **event}), cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=120)
        return proc.returncode, proc.stdout + proc.stderr

    def write(self, rel: str, data: str | bytes) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    def store(self) -> dict:
        return json.loads((self.root / ".skill-feedback" / NAME / "feedback.json").read_text(encoding="utf-8"))


def http(url: str, form: dict | None = None, origin: str | None = None) -> tuple[int, str]:
    headers = {"Origin": origin} if origin else {}
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=10) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def token(page: str) -> tuple[str, str]:
    found = re.search(r'name="delivery" value="([^"]+)"><input type="hidden" name="token" value="([^"]+)"', page)
    return (found.group(1), found.group(2)) if found else ("", "")


class Checks:
    def __init__(self):
        self.failed = 0

    def __call__(self, ok: bool, title: str, detail: str = "") -> bool:
        print(f"{'成功' if ok else '失敗'}  {title}")
        if not ok:
            self.failed += 1
            if detail:
                print("    " + detail.strip()[-1500:].replace("\n", "\n    "))
        return ok


def flow(lab: Lab, check: Checks) -> None:
    """1〜4: 提示 → 指摘 → 修正 → 確認画面で承認。"""
    check(lab.run("run.py", "start", "合成データの依頼")[0] == 0, "run.py start")
    lab.write("docs/notes.md", "# メモ\n- CSV に対応\n")
    lab.write("docs/page.html", "<h1>メモ</h1><p>CSV に対応</p>")
    lab.write("docs/banner.png", PNG)
    lab.run("run.py", "wait", "--question", "作成の途中の質問")
    lab.hook("stop", {"session_id": "s1"})
    store_file = lab.root / ".skill-feedback" / NAME / "feedback.json"
    check(not store_file.is_file() or not lab.store()["deliveries"], "作成の途中の質問待ちでは、成果物を版として保存しない")
    lab.run("run.py", "resume")
    code, out = lab.run("run.py", "finish")
    check(code == 0, "binary の出力（画像）を文字列として検査せずに finish が通る", out)
    lab.hook("stop", {"session_id": "s1"})
    lab.hook("stop", {"session_id": "s1"})
    store = lab.store()
    d1 = store["deliveries"][0] if store["deliveries"] else {}
    check(len(store["deliveries"]) == 1 and len(d1.get("files", [])) == 3, "完了の Stop で、提示した成果物を1つの版に保存する（2回目は足さない）",
          json.dumps(store["deliveries"], ensure_ascii=False)[:600])
    check(any(f["path"] == "docs/banner.png" and f["binary"] for f in d1.get("files", [])), "画像の成果物を binary として保存する")
    check((lab.root / ".skill-feedback/.gitignore").read_text() == "*\n", ".skill-feedback/ を Git の管理から外す")
    check(store["synthetic"] is True, "合成データの記録に synthetic の印が付く")

    code, out = lab.hook("prompt", {"session_id": "s1", "prompt": "日付が無い。見出しに日付を入れて"})
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip().startswith("{") else ""
    check("m-0001" in context and "feedback.py" in context and "承認ボタンを押さず" in context,
          "提示した後の発言を記録し、分類の方法を additionalContext で返す", out)
    check(lab.hook("prompt", {"session_id": "other", "prompt": "別のセッション"})[1].strip() == "", "別のセッションの発言は集めない")
    code, out = lab.run("feedback.py", "feedback", "--event", "m-0001", "--summary", "見出しに日付を入れる")
    check(code == 0 and "c-0001" in out, "feedback.py feedback が指摘 c-0001 を作る", out)
    lab.hook("prompt", {"session_id": "s1", "prompt": "OK"})
    check(lab.run("feedback.py", "ignore", "--event", "m-0002", "--reason", "相づち")[0] == 0, "feedback.py ignore が原文を残して分類する")
    case = lab.store()["cases"][0]
    check(case["approval"] is None and case["after"] is None, "会話で「OK」と言っただけでは approval が null のまま")

    lab.write("docs/notes.md", "# メモ（2026-11-04）\n- CSV に対応\n")
    lab.write("docs/page.html", "<h1>メモ（2026-11-04）</h1><p>CSV に対応</p><script>alert(1)</script>")
    lab.write("docs/banner.png", PNG + b"2026-11-04")
    lab.hook("stop", {"session_id": "s1"})
    case = lab.store()["cases"][0]
    check(case["revisions"] == ["d-0002"], "直した成果物を修正版として指摘に足す", json.dumps(case, ensure_ascii=False))
    lab.write("docs/input.csv", "a,b\n")
    check(lab.run("feedback.py", "context", "--file", "docs/input.csv")[0] == 0, "feedback.py context が入力ファイルを保存する")

    code, out = lab.run("feedback.py", "review", "--port", "0")
    url = re.search(r"http://127\.0\.0\.1:\d+/", out)
    if not check(code == 0 and url is not None, "feedback.py review が確認画面を起動して URL を出す", out):
        return
    base, origin = url.group(0), url.group(0).rstrip("/")
    try:
        status, page = http(base)
        check(status == 200 and "日付が無い。見出しに日付を入れて" in page and "この修正版を承認する" in page,
              "確認画面に指摘の原文と承認のボタンが出る", page[:300])
        check('<iframe sandbox' in page and "/object/" in page, "HTML はスクリプトを止めて、画像は実ファイルで並べる")
        delivery, t1 = token(page)
        status, _ = http(base + "approve", {"case": "c-0001", "delivery": delivery, "token": t1}, "http://evil.example")
        check(status == 403 and lab.store()["cases"][0]["approval"] is None, "別の送信元からの承認を拒否する")
        _, page = http(base)
        _, t2 = token(page)
        status, _ = http(base + "approve", {"case": "c-0001", "delivery": delivery, "token": t1}, origin)
        check(status == 409 and lab.store()["cases"][0]["approval"] is None, "古い画面からの承認を拒否する")
        lab.write("docs/notes.md", "# メモ（2026-11-04）\n- CSV に対応\n- 表示後に変えた\n")
        status, page = http(base + "approve", {"case": "c-0001", "delivery": delivery, "token": t2}, origin)
        check(status == 409 and "変わりました" in page and lab.store()["cases"][0]["approval"] is None,
              "表示した後にファイルが変わった版への承認を拒否する", page[-600:])
        _, page = http(base)
        newest, t3 = token(page)
        status, _ = http(base + "approve", {"case": "c-0001", "delivery": delivery, "token": t3}, origin)
        check(newest == "d-0003" and status == 409 and lab.store()["cases"][0]["approval"] is None,
              "画面に出した版と違う版への承認を拒否する")
        _, page = http(base)
        newest, t4 = token(page)
        status, page = http(base + "approve", {"case": "c-0001", "delivery": newest, "token": t4, "comment": "これでよい"}, origin)
        case = lab.store()["cases"][0]
        ok = (status == 200 and case["status"] == "approved" and case["after"] == "d-0003" and case["before"] == "d-0001"
              and case["issue"]["quotes"] == ["日付が無い。見出しに日付を入れて"] and case["approval"]["comment"] == "これでよい"
              and case["approval"]["synthetic"] is True)
        check(ok, "確認画面で承認すると、cases に原文・修正前・修正後・承認がそろう（合成データの印つき）",
              json.dumps(case, ensure_ascii=False))
        check(lab.run("feedback.py", "validate")[0] == 0, "feedback.py validate が記録の形と参照を通す", lab.run("feedback.py", "validate")[1])
        sha = next(f["sha256"] for f in lab.store()["deliveries"][0]["files"] if f["path"] == "docs/page.html")
        status, _ = http(base + f"object/{'0' * 64}?name=x.html")
        check(status == 404, "記録に無い実ファイルは出さない")
        req = urllib.request.urlopen(base + f"object/{sha}?name=page.html", timeout=10)
        check(req.headers.get("Content-Type", "").startswith("text/plain"), "成果物の HTML はこのサーバーの上で動かさない（text/plain）")
    finally:
        info = json.loads((lab.root / ".skill-feedback" / NAME / "review.json").read_text(encoding="utf-8"))
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except (OSError, KeyError):
            pass
    code, out = lab.hook("pre-tool", {"tool_name": "Write", "tool_input": {"file_path": str(lab.root / ".skill-feedback" / NAME / "feedback.json")}})
    check('"deny"' in out, "記録（.skill-feedback/）への直接の編集を拒否する", out)


def installs(lab: Lab, check: Checks) -> None:
    """5: 登録の形と、hooks が無くても完了すること。"""
    settings = lab.root / ".claude/settings.json"

    def commands() -> dict:
        data = json.loads(settings.read_text(encoding="utf-8")) if settings.is_file() else {}
        return {e: [h["command"] for g in gs for h in g["hooks"]] for e, gs in data.get("hooks", {}).items()}

    lab.run("install.py", "--project", str(lab.root), "--targets", "claude", "--no-hooks")
    check(not settings.exists(), "--no-hooks では .claude/settings.json に何も書かない")
    lab.run("run.py", "start", "--restart", "hooks なし")
    lab.write("docs/notes.md", "# hooks なし\n")
    check(lab.run("run.py", "check")[0] == 0 and lab.run("run.py", "finish")[0] == 0, "hooks が無くても start → check → finish が完了する")
    lab.run("install.py", "--project", str(lab.root), "--targets", "claude")
    full = commands()
    check(len(full) == 4 and all(c[0].endswith(f"--platform claude {a}") for c, a in
                                 zip((full["PreToolUse"], full["PostToolUse"], full["Stop"], full["UserPromptSubmit"]),
                                     ("pre-tool", "post-tool", "stop", "prompt"))),
          "既定の登録は4つで、文字列は機能を足す前と同じ（Codex の信頼が外れない）", json.dumps(full, ensure_ascii=False))
    lab.run("install.py", "--project", str(lab.root), "--targets", "claude", "--no-feedback")
    only = commands()
    check(len(only) == 4 and all("--no-feedback" in c[0] for c in only.values()), "--no-feedback では収集だけを外して4つを登録し直す")
    lab.run("install.py", "--project", str(lab.root), "--targets", "claude", "--features", "feedback")
    gather = commands()
    check(set(gather) == {"PreToolUse", "Stop", "UserPromptSubmit"} and all("--no-check" in c[0] for c in gather.values()),
          "収集だけなら PostToolUse を外し、3つを登録する", json.dumps(gather, ensure_ascii=False))
    code, out = lab.run("install.py", "--project", str(lab.root), "--targets", "claude", "--features", "feedback", "--check")
    check(code == 0, "install.py --check が収集だけの登録を確かめる", out)
    lab.hook("stop", {"session_id": "s9"})
    code, out = lab.hook("prompt", {"session_id": "s9", "prompt": "収集しない"}, "--no-feedback")
    check(out.strip() == "", "--no-feedback の hook は発言を集めない", out)
    lab.run("install.py", "--project", str(lab.root), "--targets", "claude", "--uninstall")


def broken(lab: Lab, check: Checks) -> None:
    """6: feedback.py が例外で落ちても、本来の検査と完了が止まらない。"""
    script = lab.skill / "scripts/feedback.py"
    saved = script.read_bytes()
    script.write_text("raise RuntimeError('故意の失敗')\n", encoding="utf-8")
    try:
        check(lab.run("run.py", "start", "--restart", "壊れた収集")[0] == 0, "壊れた feedback.py のまま run.py start が動く")
        lab.write("docs/notes.md", "見出しが無い\n")
        code, out = lab.hook("post-tool", {"session_id": "s2", "tool_name": "Write", "tool_input": {"file_path": str(lab.root / "docs/notes.md")}})
        check('"block"' in out and "OUT-01" in out, "壊れた feedback.py のまま、編集の後の検査が指摘を返す", out)
        code, out = lab.hook("stop", {"session_id": "s2"})
        check(code == 0 and '"block"' in out, "壊れた feedback.py のまま、応答を終える前の検査が差し戻す", out)
        code, out = lab.hook("pre-tool", {"tool_name": "Edit", "tool_input": {"file_path": str(lab.root / f".skill-runs/{NAME}/state.json")}})
        check('"deny"' in out, "壊れた feedback.py のまま、実行記録の編集を拒否する", out)
        lab.write("docs/notes.md", "# 直した\n")
        check(lab.run("run.py", "finish")[0] == 0, "壊れた feedback.py のまま finish が完了する")
        code, out = lab.hook("stop", {"session_id": "s2"})
        code2, out2 = lab.hook("prompt", {"session_id": "s2", "prompt": "違う"})
        check(code == 0 and code2 == 0 and "Traceback" not in out + out2, "壊れた feedback.py の失敗を hooks が外に出さない", out + out2)
    finally:
        script.write_bytes(saved)


def lint(lab: Lab, check: Checks) -> None:
    """7: 収集の指示を SKILL.md とルールの表に書くと、skill_lint.py が指摘する。"""
    import skill_lint
    (lab.skill / "references").mkdir(exist_ok=True)
    (lab.skill / "SKILL.md").write_text("# fb-demo\n\n1. 出力を書く\n", encoding="utf-8")
    (lab.skill / "references/decisions.md").write_text("# ルール\n", encoding="utf-8")
    clean = skill_lint.Report()
    skill_lint.check_collect(lab.skill, clean)
    check(not clean.errors, "収集の指示が無ければ指摘しない", json.dumps(clean.errors, ensure_ascii=False))
    (lab.skill / "SKILL.md").write_text("# fb-demo\n\n1. 出力を書く\n2. python3 <skill>/scripts/feedback.py review を実行する\n",
                                        encoding="utf-8")
    (lab.skill / "references/decisions.md").write_text("# ルール\n\n- 記録は .skill-feedback/ に置く\n", encoding="utf-8")
    dirty = skill_lint.Report()
    skill_lint.check_collect(lab.skill, dirty)
    where = sorted(e.split(" ")[0] for _, e in dirty.errors)
    check(where == ["SKILL.md", "references/decisions.md"], "SKILL.md とルールの表の収集の指示を、行ごとに指摘する",
          json.dumps(dirty.errors, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep", action="store_true", help="一時ディレクトリを消さずに残す")
    args = parser.parse_args()
    temp = Path(tempfile.mkdtemp(prefix="skill-feedback-selftest-")).resolve()
    check = Checks()
    try:
        lab = Lab(temp)
        flow(lab, check)
        installs(lab, check)
        broken(lab, check)
        lint(lab, check)
    finally:
        if args.keep:
            print(f"一時ディレクトリを残しました: {temp}")
        else:
            shutil.rmtree(temp, ignore_errors=True)
    print(f"\n収集の自己テスト: 失敗 {check.failed} 件")
    return 1 if check.failed else 0


if __name__ == "__main__":
    sys.exit(main())
