#!/usr/bin/env python3
"""ステージ済みの差分を集め、コミットメッセージの材料を出す（IN-02、STEP-01）。

出力: ステージされたファイルの一覧（状態とパス）、ファイルの数、本文の単位（STEP-02 の決定表）、差分の先頭 400 行
終了コード: 0 材料あり、4 ステージされた変更が無い（IN-01）、2 git が使えない（STEP-04）

使い方:
  python3 <skill>/scripts/collect_diff.py [--root <リポジトリのルート>]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

MAX_DIFF_LINES = 400


def git(args: list[str], root: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"git {' '.join(args)} が失敗しました: {proc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return proc.stdout


def body_unit(count: int) -> str:
    if count == 1:
        return "なし"
    if count <= 5:
        return "ファイル"
    return "ディレクトリ"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    entries = [line.split("\t") for line in git(["diff", "--cached", "--name-status"], root).splitlines() if line]
    if not entries:
        print("ステージされた変更がありません（IN-01）")
        return 4
    print(f"ファイルの数: {len(entries)}")
    print(f"本文の単位: {body_unit(len(entries))}")
    print("ファイル:")
    for entry in entries:
        print(f"  {entry[0]}\t{entry[-1]}")
    diff = git(["diff", "--cached"], root).splitlines()
    print(f"差分（先頭 {MAX_DIFF_LINES} 行）:")
    print("\n".join(diff[:MAX_DIFF_LINES]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
