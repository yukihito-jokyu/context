#!/usr/bin/env python3
"""違反例（probe）を一時プロジェクトで1件ずつ流し、出力の検査と hooks が本当に AI を止めることを証明する。

元のスキルとプロジェクトには触れない。一時ディレクトリにプロジェクトを作り、スキルを写して install.py で
置き場所と hooks を登録してから、次を確かめる。
  baseline : dev/probes.json の baseline の出力で、check と finish が通る（通らなければ何も証明しない）。
             baseline.setup は start の前に1回（{skill} は元のスキル、{lab} は一時ディレクトリ）、
             baseline.files と baseline.commands は start の後に毎回（{skill} は写したスキル、{root} はプロジェクト）
  probe    : baseline を probe の内容で壊すと、check が落ち、出力が expect に一致する。出力に別のルールIDの指摘が
             出たら others に記録し、注意を出す（1つの違反例は1つのルールだけを破る。skill_lint.py --final が警告にする）
             （files の mode: create・append・delete・sub。sub は pattern を replacement に置き換える。
             create の中身は content か、from に書いたスキルの見本 assets/examples/<ファイル>）。
             fixed を持つ probe（段 format）は、check が通り、出力が expect に一致し、files の1つ目に fixed が残らない
  review   : dev/probes.json の reviews の見本は、機械の検査（check）を通る（通らないなら review でなく validate にする）
  標準     : 出力が無いと finish が落ちる・スキル自身（SKILL.md と契約）を変えた後も start・check・finish が通り、
             違反例は変わらず check で落ちる（CTL-01）、wait 中は stop が止めない（CTL-03）、実行していないと hooks は
             何もしない・発言は止めない・スキル自身の編集は止めない（CTL-04）、finish が報告の本文を出し、
             notes.md が箇条書きでないと check が落ちる、abort が中断の本文を出し、次の start が前の中断を残す・
             前の実行の後に契約を変えると報告の「検証」に出る（RPT-01）
  hooks の動作: targets のうち hooks を登録する製品（契約の control.hook_targets。無ければ全部）ごとに、登録した hooks の
             コマンドを製品の形の入力で実行し、編集の後・終える前に AI を止める
             出力が出て、実行記録（state.json）の編集の前に拒否が出る。スキル自身（SKILL.md）の編集の前は何もしない（CTL-04）。
             契約の control.feedback が false でなければ、完了の後の発言を記録して分類の方法を返し、利用中の指摘の記録
             （.skill-feedback/）の編集の前に拒否が出ることも確かめる（references/feedback.md）
結果は dev/results/probe-results.json に書く（skill_lint.py --final が読む）。--only のときは書かない。

使い方:
  python3 probe.py <スキルのディレクトリ> [--only OUT-02-a,OUT-03-a,OUT-03-r1] [--keep-temp]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
import skill_lint  # noqa: E402

EDIT_EVENT = {
    "claude": lambda root, rel: {"cwd": str(root), "hook_event_name": "PostToolUse", "session_id": "probe",
                                 "tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": ""}},
    "codex": lambda root, rel: {"cwd": str(root), "hook_event_name": "PostToolUse", "session_id": "probe", "turn_id": "probe",
                                "tool_name": "apply_patch",
                                "tool_input": {"command": f"*** Begin Patch\n*** Update File: {rel}\n@@\n+x\n*** End Patch\n"}},
}
EDIT_TOOL = {"claude": "Write", "codex": "apply_patch"}
PLACES = {"claude": ".claude/skills", "codex": ".agents/skills"}
CONFIGS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
FEEDBACK_REL = ".skill-feedback"  # feedback.py の DIRNAME と同じ


class Lab:
    """一時プロジェクトと、そこに置いたスキルの写し。"""

    def __init__(self, skill_dir: Path, spec: dict, probes_doc: dict, keep: bool):
        self.spec, self.doc, self.keep = spec, probes_doc, keep
        self.name = spec["name"]
        self.temp = Path(tempfile.mkdtemp(prefix=f"{self.name}-probe-")).resolve()
        self.root = self.temp / "proj"
        baseline = probes_doc.get("baseline", {})
        if baseline.get("fixture"):
            shutil.copytree(skill_dir / baseline["fixture"], self.root)
        else:
            self.root.mkdir()
        _lib.git_init(self.root)
        for command in baseline.get("setup", []):
            command = command.replace("{skill}", rt.shell_quote(str(skill_dir))).replace("{lab}", rt.shell_quote(str(self.temp)))
            code, out = _lib.run(command, self.root, timeout=900)
            if code != 0:
                _lib.fail(f"baseline.setup の `{command}` が失敗しました: {_lib.tail(out, 5)}")
        self.skill = self.root / PLACES[spec["targets"][0]] / self.name
        self.skill.parent.mkdir(parents=True, exist_ok=True)
        _lib.copy_tree(skill_dir, self.skill, exclude=("__pycache__", ".skill-runs", ".DS_Store", "dev"))
        args = [sys.executable, str(self.skill / "scripts/install.py"), "--project", str(self.root),
                "--targets", ",".join(spec["targets"])]
        code, out = _lib.run(args, self.root)
        if code != 0:
            _lib.fail(f"install.py が失敗しました: {_lib.tail(out, 10)}")
        self.values: dict = {}

    def close(self) -> None:
        if self.keep:
            print(f"一時プロジェクトを残しました: {self.root}")
        else:
            shutil.rmtree(self.temp, ignore_errors=True)

    def run_py(self, *args: str, stdin: str | None = None) -> tuple[int, str]:
        return _lib.run([sys.executable, str(self.skill / "scripts/run.py"), *args], self.root, timeout=300, stdin=stdin)

    def start(self, *extra: str, fresh: bool = True) -> tuple[int, str]:
        if fresh:
            shutil.rmtree(self.root / rt.RUNS_DIRNAME, ignore_errors=True)
        baseline = self.doc.get("baseline", {})
        args = ["start", *extra, "--json", "--input-json", json.dumps(baseline.get("input", {}), ensure_ascii=False)]
        if baseline.get("text"):
            args.append(baseline["text"])
        code, out = self.run_py(*args)
        if code == 0:
            try:
                self.values = json.loads(out).get("input", {})
            except json.JSONDecodeError:
                self.values = {}
        return code, out

    def path(self, raw: str) -> Path:
        return self.root / rt.expand(raw, self.name, self.values)

    def apply(self, changes: list[dict]) -> list[tuple[Path, bytes | None]]:
        undo = []
        for change in changes:
            target = self.path(change["path"])
            original = target.read_bytes() if target.exists() else None
            undo.append((target, original))
            mode = change.get("mode", "create")
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == "delete":
                if target.exists():
                    target.unlink()
            elif mode == "append":
                with target.open("a", encoding="utf-8") as fh:
                    fh.write(change.get("content", ""))
            elif mode == "sub":
                text, count = re.subn(change["pattern"], change.get("replacement", ""), target.read_text(encoding="utf-8"),
                                      flags=re.M)
                if count == 0:
                    _lib.fail(f"{change['path']} に /{change['pattern']}/ が見つかりません（probe の mode: sub）")
                target.write_text(text, encoding="utf-8")
            elif change.get("from"):
                target.write_bytes((self.skill / change["from"]).read_bytes())  # 見本をそのまま使う
            else:
                target.write_text(change.get("content", ""), encoding="utf-8")
        return undo

    def tree(self) -> dict[Path, bytes | None]:
        """プロジェクトのファイル（中身）、シンボリックリンクとディレクトリ（None）。.git と実行記録は除く。"""
        found = {}
        for dirpath, dirnames, filenames in os.walk(self.root):
            base = Path(dirpath)
            for d in list(dirnames):
                if d in (".git", rt.RUNS_DIRNAME) or (base / d).is_symlink():
                    dirnames.remove(d)
                    if d not in (".git", rt.RUNS_DIRNAME):
                        found[base / d] = None
                else:
                    found[base / d] = None
            for f in filenames:
                path = base / f
                found[path] = None if path.is_symlink() else path.read_bytes()
        return found

    def baseline(self) -> list[tuple[Path, bytes | None]]:
        """baseline の files を書き、commands を実行する。commands が作った・変えたものも元に戻せるようにする。"""
        doc = self.doc.get("baseline", {})
        undo = self.apply(doc.get("files", []))
        commands = doc.get("commands", [])
        if not commands:
            return undo
        before = self.tree()
        for command in commands:
            command = (command.replace("{skill}", rt.shell_quote(str(self.skill))).replace("{root}", rt.shell_quote(str(self.root)))
                       .replace("{lab}", rt.shell_quote(str(self.temp))))
            code, out = _lib.run(command, self.root, timeout=900)
            if code != 0:
                _lib.fail(f"baseline.commands の `{command}` が失敗しました: {_lib.tail(out, 10)}")
        after = self.tree()
        created = sorted((p for p in after if p not in before), key=lambda p: len(p.parts))
        undo += [(p, None) for p in created]
        undo += [(p, before[p]) for p in after if p in before and before[p] is not None and after[p] != before[p]]
        return undo

    @staticmethod
    def revert(undo: list[tuple[Path, bytes | None]]) -> None:
        for target, original in reversed(undo):
            if original is None:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
            else:
                target.write_bytes(original)

    def hook_commands(self, platform: str) -> dict[str, tuple[str, str | None]]:
        """登録された hooks のうち、このスキルのもの（イベント → (コマンド, matcher)）。"""
        config = self.root / CONFIGS[platform]
        data = json.loads(config.read_text(encoding="utf-8")) if config.is_file() else {}
        found = {}
        for event, groups in data.get("hooks", {}).items():
            for group in groups:
                for handler in group.get("hooks", []):
                    if f"/{self.name}/scripts/hook.py" in handler.get("command", ""):
                        found[event] = (handler["command"], group.get("matcher"))
        return found

    def hook(self, platform: str, command: str, event: dict) -> tuple[int, str]:
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        if platform == "claude":
            env["CLAUDE_PROJECT_DIR"] = str(self.root)
        return _lib.run(["/bin/sh", "-c", command], self.root, timeout=300, env=env, stdin=json.dumps(event))


def matcher_hits(matcher: str | None, tool: str) -> bool:
    if not matcher or matcher == "*":
        return True
    if re.fullmatch(r"[A-Za-z0-9_|, -]+", matcher):
        return tool in [m.strip() for m in re.split(r"[|,]", matcher)]
    return re.search(matcher, tool) is not None


def decision_of(output: str) -> dict:
    for line in reversed(output.strip().splitlines()):
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir")
    parser.add_argument("--only", help="カンマ区切りの probe ID（結果ファイルは書かない）")
    parser.add_argument("--keep-temp", action="store_true", help="一時プロジェクトを消さずに残す（見終えたら消す）")
    args = parser.parse_args()

    skill_dir = Path(args.dir).resolve()
    spec = _lib.load_spec(skill_dir)
    doc = _lib.load_json(skill_dir / "dev/probes.json")
    probes, reviews = doc.get("probes", []), doc.get("reviews", [])
    if args.only:
        wanted = {p.strip() for p in args.only.split(",")}
        probes = [p for p in probes if p.get("id") in wanted]
        reviews = [x for x in reviews if x.get("id") in wanted]
    contract = _lib.load_json(skill_dir / "assets/contract.json")
    lab = Lab(skill_dir, spec, doc, args.keep_temp)
    results, wiring = [], []

    def record(pid: str, rule: str, passed: bool, detail: str, output: str = "", others: list[str] | None = None) -> None:
        results.append({"id": pid, "rule": rule, "passed": passed, "detail": detail,
                        "output_tail": "" if passed else _lib.tail(output, 12), "others": others or []})
        print(f"{'成功' if passed else '失敗'}  {pid}  {detail}")
        if others:
            print(f"    注意: 別のルール {', '.join(others)} の指摘も出ました。1つの違反例は1つのルールだけを破るようにする")
        if not passed and output:
            print("    " + _lib.tail(output, 12).replace("\n", "\n    "))

    try:
        code, out = lab.start()
        if code != 0:
            print(f"baseline: start が終了コード {code} で終わりました。baseline.input を見直してください\n{_lib.tail(out, 15)}")
            return 2
        undo = lab.baseline()
        code, out = lab.run_py("check")
        if code != 0:
            print(f"baseline: 見本の出力が check に通りません。先に見本か契約を直してください\n{_lib.tail(out, 20)}")
            return 2
        code, out = lab.run_py("finish")
        report_ok = code == 0 and all(re.search(p, out, re.M) for p in (r"^## (結果|Result)$", r"^## (補足|Notes)$"))
        record("RPT-01-builtin", "RPT-01", report_ok, "finish が報告の本文（## 結果 から ## 補足 まで）を出す", out)
        lab.revert(undo)
        print("baseline  見本の出力で check と finish が通る")

        for probe in probes:
            lab.start()
            undo = lab.baseline()
            undo += lab.apply(probe.get("files", []))
            code, out = lab.run_py("check")
            matched = re.search(probe.get("expect", "^$"), out) is not None
            others = sorted(set(re.findall(r"^([A-Z]+-\d{2}) ", out, re.M)) - {probe.get("rule")})
            if probe.get("fixed") is not None:
                target = lab.path(probe["files"][0]["path"])
                gone = re.search(probe["fixed"], target.read_text(encoding="utf-8") if target.is_file() else "", re.M) is None
                record(probe["id"], probe.get("rule", ""), code == 0 and matched and gone,
                       f"check の終了コード {code}、expect 一致 {'あり' if matched else 'なし'}、自動で直った {'はい' if gone else 'いいえ'}",
                       out, others)
            else:
                record(probe["id"], probe.get("rule", ""), code == 1 and matched,
                       f"check の終了コード {code}、expect 一致 {'あり' if matched else 'なし'}", out, others)
            lab.revert(undo)

        for sample in reviews:
            lab.start()
            undo = lab.baseline()
            undo += lab.apply(sample.get("files", []))
            code, out = lab.run_py("check")
            record(sample["id"], sample.get("rule", ""), code == 0,
                   f"レビューの見本が機械の検査を通る（終了コード {code}。通らないなら review でなく validate にする）", out)
            lab.revert(undo)

        if not args.only:
            lab.start()
            code, out = lab.run_py("finish")
            record("CTL-01-builtin", "CTL-01", code == 1, f"出力が無いと finish が落ちる（終了コード {code}）", out)
            # スキル自身（SKILL.md と契約）は実行の前にも途中にも直せる。直しても出力の検査は変わらず働く（CTL-01、CTL-04）
            skill_md, contract_json = lab.skill / "SKILL.md", lab.skill / rt.CONTRACT_REL
            original, original_contract = skill_md.read_bytes(), contract_json.read_bytes()
            edited_contract = json.dumps({**contract, "x-probe": "edited"}, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
            skill_md.write_bytes(original + b"\n")
            contract_json.write_bytes(edited_contract)
            start_code, start_out = lab.start()
            undo = lab.baseline()
            skill_md.write_bytes(original + b"\n\n")  # 実行の途中にも直す
            code, out = lab.run_py("check")
            finish_code, finish_out = lab.run_py("finish")
            lab.revert(undo)
            record("CTL-01-builtin-edited", "CTL-01", start_code == 0 and code == 0 and finish_code == 0,
                   f"SKILL.md と契約を変えた後も start・check・finish が通る（終了コード start {start_code}、check {code}、"
                   f"finish {finish_code}）", start_out + "\n" + out + "\n" + finish_out)
            failing = next((p for p in probes if p.get("fixed") is None and any(r["id"] == p["id"] and r["passed"] for r in results)), None)
            if failing:
                lab.start()
                undo = lab.baseline()
                undo += lab.apply(failing.get("files", []))
                code, out = lab.run_py("check")
                lab.revert(undo)
                record("CTL-01-builtin-edited-probe", "CTL-01", code == 1 and re.search(failing.get("expect", "^$"), out) is not None,
                       f"スキル自身を変えた後も、違反例 {failing['id']} は check で落ちる（終了コード {code}）", out)
            skill_md.write_bytes(original)
            contract_json.write_bytes(original_contract)

            lab.start()
            lab.run_py("abort", "--reason", "probe-contract")
            contract_json.write_bytes(edited_contract)
            lab.start(fresh=False)
            undo = lab.baseline()
            code, out = lab.run_py("finish")
            contract_json.write_bytes(original_contract)
            lab.revert(undo)
            shown = re.search(r"^- (前の実行の後に契約|The contract \(`assets/contract\.json`\) changed)", out, re.M)
            record("RPT-01-builtin-contract", "RPT-01", code == 0 and shown is not None,
                   f"前の実行の後に契約を変えると、止めずに報告の「検証」に出す（終了コード {code}）", out)

            lab.start()
            undo = lab.baseline()
            undo += lab.apply([{"path": rt.notes_rel(lab.name), "content": "## 補足\n自由に書いた補足\n"}])
            code, out = lab.run_py("check")
            record("RPT-01-builtin-notes", "RPT-01", code == 1 and "RPT-01" in out,
                   f"notes.md が箇条書きでないと check が落ちる（終了コード {code}）", out)
            lab.revert(undo)

            lab.start()
            code, out = lab.run_py("abort", "--reason", "probe-abort")
            report_ok = code == 0 and all(re.search(p, out, re.M) for p in (r"^## (結果|Result)$", r"probe-abort", r"^## (補足|Notes)$"))
            lab.start(fresh=False)
            _, status = lab.run_py("status")
            record("RPT-01-builtin-abort", "RPT-01", report_ok and "probe-abort" in status,
                   "abort が中断の本文を出し、次の start が前の中断を記録に残す", out + "\n" + status)

            asks = [i for i in contract.get("inputs", []) if i.get("ask")]
            if asks:
                shutil.rmtree(lab.root / rt.RUNS_DIRNAME, ignore_errors=True)
                code, out = lab.run_py("start")
                record("CTL-03-builtin-ask", "CTL-03", code == 3, f"聞くべき入力が無いと start が止まる（終了コード {code}）", out)

            hooks_on = contract.get("control", {}).get("hooks", True)
            hooked = contract.get("control", {}).get("hook_targets", spec.get("targets", []))  # hooks の方針で選んだ製品
            for platform in [p for p in spec.get("targets", []) if p in hooked] if hooks_on else []:
                commands = lab.hook_commands(platform)
                missing = [e for e in ("PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit") if e not in commands]

                def wire(check: str, passed: bool, detail: str, output: str = "") -> None:
                    wiring.append({"platform": platform, "check": check, "passed": passed, "detail": detail})
                    print(f"{'成功' if passed else '失敗'}  hooks の動作 {platform} {check}  {detail}")
                    if not passed and output:
                        print("    " + _lib.tail(output, 8).replace("\n", "\n    "))

                if missing:
                    wire("registered", False, f"{CONFIGS[platform]} に {missing} の hook がありません")
                    continue
                wire("registered", True, f"{CONFIGS[platform]} に4つの hook がある")
                tool = EDIT_TOOL[platform]
                wire("matcher", matcher_hits(commands["PostToolUse"][1], tool) and matcher_hits(commands["PreToolUse"][1], tool),
                     f"matcher が編集ツール {tool} に当たる")
                shutil.rmtree(lab.root / rt.RUNS_DIRNAME, ignore_errors=True)
                code, out = lab.hook(platform, commands["Stop"][0], {"cwd": str(lab.root), "hook_event_name": "Stop"})
                wire("inactive", code == 0 and not out.strip(), "実行していないセッションでは何もしない（CTL-04）", out)

                # 編集の後の検査を試す。ファイルを消す probe（件数の違反）と、stage: finish の検査でしか
                # 見つからない probe は編集の直後には検出されないので、検出されるものを順に探す
                candidates = [p for p in probes if any(r["id"] == p["id"] and r["passed"] for r in results)
                              and all(c.get("mode", "create") != "delete" for c in p.get("files", []))]
                found, out = None, ""
                for candidate in candidates:
                    lab.start()
                    undo = lab.baseline()
                    undo += lab.apply(candidate.get("files", []))
                    rel = rt.expand(candidate["files"][0]["path"], lab.name, lab.values)
                    code, out = lab.hook(platform, commands["PostToolUse"][0], EDIT_EVENT[platform](lab.root, rel))
                    lab.revert(undo)
                    if decision_of(out).get("decision") == "block":
                        found = candidate
                        break
                wire("post-tool", found is not None,
                     f"{found['id']} の出力を編集した後に指摘を返す" if found else
                     "編集の直後に検出される probe がありません（stage: finish でない検査の違反例を足す）", out)
                lab.start()
                undo = lab.baseline()
                code, out = lab.hook(platform, commands["UserPromptSubmit"][0],
                                     {"cwd": str(lab.root), "hook_event_name": "UserPromptSubmit", "prompt": "どんな書き方でも"})
                wire("prompt", code == 0 and not out.strip(), "ユーザーの発言は止めない（CTL-04）", out)
                code, out = lab.hook(platform, commands["Stop"][0],
                                     {"cwd": str(lab.root), "hook_event_name": "Stop", "stop_hook_active": False})
                wire("stop", decision_of(out).get("decision") == "block", "finish の前に応答を終えようとすると差し戻す", out)
                lab.run_py("wait", "--question", "probe")
                code, out = lab.hook(platform, commands["Stop"][0], {"cwd": str(lab.root), "hook_event_name": "Stop"})
                wire("wait", code == 0 and decision_of(out).get("decision") != "block", "wait 中は応答の終了を止めない（CTL-03）", out)
                lab.run_py("resume")
                for check, rel, wanted, what in (
                        ("pre-tool-skill", f"{PLACES[platform]}/{lab.name}/SKILL.md", None, "スキル自身（SKILL.md）の編集の前は止めない"),
                        ("pre-tool", f"{rt.run_rel(lab.name)}/state.json", "deny", "実行記録（state.json）の編集の前に拒否する")):
                    event = {**EDIT_EVENT[platform](lab.root, rel), "hook_event_name": "PreToolUse"}
                    code, out = lab.hook(platform, commands["PreToolUse"][0], event)
                    got = decision_of(out).get("hookSpecificOutput", {}).get("permissionDecision")
                    wire(check, code == 0 and got == wanted, f"{what}（結果 {got or '何もしない'}。CTL-04）", out)
                lab.revert(undo)
                if contract.get("control", {}).get("feedback", True) is not False:
                    # 利用中の指摘の収集（hooks の追加機能。references/feedback.md）。完了の後の発言を記録して分類を頼み、記録の編集を拒否する
                    lab.start()
                    undo = lab.baseline()
                    lab.run_py("finish")
                    session = f"probe-{platform}"
                    lab.hook(platform, commands["Stop"][0], {"cwd": str(lab.root), "hook_event_name": "Stop", "session_id": session})
                    code, out = lab.hook(platform, commands["UserPromptSubmit"][0],
                                         {"cwd": str(lab.root), "hook_event_name": "UserPromptSubmit", "session_id": session,
                                          "prompt": "ここが違う"})
                    context = decision_of(out).get("hookSpecificOutput", {}).get("additionalContext", "")
                    wire("feedback-prompt", code == 0 and "feedback --event" in context and decision_of(out).get("decision") != "block",
                         "完了の後の発言を記録し、分類の方法を返す（発言は止めない）", out)
                    rel = f"{FEEDBACK_REL}/{lab.name}/feedback.json"
                    code, out = lab.hook(platform, commands["PreToolUse"][0], {**EDIT_EVENT[platform](lab.root, rel), "hook_event_name": "PreToolUse"})
                    got = decision_of(out).get("hookSpecificOutput", {}).get("permissionDecision")
                    wire("feedback-pre-tool", code == 0 and got == "deny", f"利用中の指摘の記録（{FEEDBACK_REL}/）の編集の前に拒否する（結果 {got or '何もしない'}）", out)
                    shutil.rmtree(lab.root / FEEDBACK_REL, ignore_errors=True)
                    lab.revert(undo)
    finally:
        lab.close()

    failed = [r for r in results if not r["passed"]]
    failed_wiring = [w for w in wiring if not w["passed"]]
    if not args.only:
        _lib.write_json(skill_dir / "dev/results/probe-results.json",
                        {"hash": skill_lint.probes_hash(skill_dir), "results": results, "wiring": wiring})
    print(f"\nprobe {len(results)} 件中 失敗 {len(failed)} 件／hooks の動作 {len(wiring)} 件中 失敗 {len(failed_wiring)} 件")
    return 1 if failed or failed_wiring else 0


if __name__ == "__main__":
    sys.exit(main())
