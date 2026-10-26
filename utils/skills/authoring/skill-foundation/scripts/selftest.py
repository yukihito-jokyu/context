#!/usr/bin/env python3
"""自己テスト: 見本（assets/example/<名前>/）から一時プロジェクトにスキルを組み立て、作成用スクリプトが通しで動くことを確かめる。

  1. 見本の spec・probes・evals・research・fixtures・固有スクリプト・出力の見本を、一時プロジェクトのスキルの dev/、
     scripts/、assets/examples/ に置く
  2. init_skill.py で骨組みを作り、見本の procedure.md を SKILL.md の「2. 手順」に入れる
  3. render_skill.py --check、skill_lint.py --phase 5、probe.py を実行する
  4. convergence.py prepare で、全課題の fixture と setup が動くことを確かめる（エージェントは起動しない）

skill-foundation のスクリプトやひな形を変えたら、これを実行してから使う。

--build <ディレクトリ> を付けると、検証せずに見本をそのディレクトリ（プロジェクト）に組み立てるだけにする。
さらに --ready を付けると、probe を実行して status を ready にし、収束テストを省いた形（skill_lint.py --final が
通る形）に仕上げる。skill-foundation 自身の probe（dev/probes.json の baseline.setup）が使う。

使い方:
  python3 selftest.py [--example write-commit-message] [--keep]
  python3 selftest.py --build <プロジェクト> [--ready]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

EXAMPLES = _lib.FOUNDATION_DIR / "assets" / "example"
SCRIPTS = _lib.FOUNDATION_DIR / "scripts"
DEV_FILES = ["spec.json", "probes.json", "evals.json", "research.md"]
PROCEDURE = re.compile(r"(^## (?:2\. 手順|2\. Procedure)\n.*?\n)(1\. .*?)(?=\n\n## )", re.S | re.M)


def build(example: Path, project: Path) -> Path:
    spec = _lib.load_json(example / "spec.json")
    place = ".claude/skills" if spec["targets"][0] == "claude" else ".agents/skills"
    skill = project / place / spec["name"]
    (skill / "dev").mkdir(parents=True)
    for name in DEV_FILES:
        shutil.copy2(example / name, skill / "dev" / name)
    if (example / "fixtures").is_dir():
        _lib.copy_tree(example / "fixtures", skill / "dev" / "fixtures")
    if (example / "scripts").is_dir():
        _lib.copy_tree(example / "scripts", skill / "scripts")
    if (example / "examples").is_dir():
        _lib.copy_tree(example / "examples", skill / _lib.EXAMPLES_DIR)
    return skill


READY_REPORT = """# {name} 収束テストの記録

skill-foundation の自己テストのために見本から組み立てたスキルなので、収束テストを省いた（dev/spec.json の
convergence.skip_reason）。

## 結論

収束テストは実施していない。
"""


def assemble(example: Path, project: Path) -> Path | None:
    """見本を組み立て、SKILL.md の「2. 手順」を入れる。失敗したら None。"""
    skill = build(example, project)
    if not step("init_skill.py", [sys.executable, str(SCRIPTS / "init_skill.py"), "--dir", str(skill)], project):
        return None
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    procedure = (example / "procedure.md").read_text(encoding="utf-8").strip()
    replaced, count = PROCEDURE.subn(lambda m: m.group(1) + procedure, text)
    print(f"{'成功' if count == 1 else '失敗'}  SKILL.md の「2. 手順」に procedure.md を入れる")
    (skill / "SKILL.md").write_text(replaced, encoding="utf-8")
    return skill if count == 1 else None


def make_ready(skill: Path) -> bool:
    spec = _lib.load_spec(skill)
    spec["status"] = "ready"
    spec.setdefault("convergence", {})["skip_reason"] = "skill-foundation の自己テスト用に見本から組み立てたため"
    _lib.write_json(skill / _lib.SPEC_REL, spec)
    (skill / "dev/convergence-report.md").write_text(READY_REPORT.replace("{name}", spec["name"]), encoding="utf-8")
    return (step("render_skill.py", [sys.executable, str(SCRIPTS / "render_skill.py"), "--dir", str(skill)], skill)
            and step("probe.py", [sys.executable, str(SCRIPTS / "probe.py"), str(skill)], skill))


def step(title: str, command: list[str], cwd: Path, timeout: int = 900) -> bool:
    code, out = _lib.run(command, cwd, timeout=timeout)
    print(f"{'成功' if code == 0 else '失敗'}  {title}（終了コード {code}）")
    print("    " + _lib.tail(out, 3 if code == 0 else 25).replace("\n", "\n    "))
    return code == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--example", default="write-commit-message")
    parser.add_argument("--keep", action="store_true", help="一時プロジェクトを消さずに残す")
    parser.add_argument("--build", help="検証せずに、見本をこのプロジェクトに組み立てる")
    parser.add_argument("--ready", action="store_true", help="--build のとき、probe まで済ませて status を ready にする")
    args = parser.parse_args()

    example = EXAMPLES / args.example
    if not (example / "spec.json").is_file():
        _lib.fail(f"見本がありません: {example}")
    if args.build:
        project = Path(args.build).resolve()
        project.mkdir(parents=True, exist_ok=True)
        skill = assemble(example, project)
        ok = skill is not None and (not args.ready or make_ready(skill))
        return 0 if ok else 1
    temp = Path(tempfile.mkdtemp(prefix="skill-foundation-selftest-")).resolve()
    scripts, py = SCRIPTS, sys.executable
    try:
        (temp / "proj").mkdir()
        skill = assemble(example, temp / "proj")
        results = [skill is not None]
        if skill is not None:
            results.append(step("render_skill.py --check", [py, str(scripts / "render_skill.py"), "--dir", str(skill), "--check"], temp))
            results.append(step("skill_lint.py --phase 5", [py, str(scripts / "skill_lint.py"), str(skill), "--phase", "5"], temp))
            results.append(step("probe.py", [py, str(scripts / "probe.py"), str(skill)], temp))
            results.append(step("convergence.py prepare（全課題）",
                                [py, str(scripts / "convergence.py"), "prepare", str(skill), "--round", "1",
                                 "--include-holdout", "--agents", "1", "--workdir", str(temp / "conv")], temp))
        failed = results.count(False)
        print(f"\n自己テスト: {len(results)} 段階中 失敗 {failed} 件")
        return 1 if failed else 0
    finally:
        if args.keep:
            print(f"一時プロジェクトを残しました: {temp}")
        else:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
