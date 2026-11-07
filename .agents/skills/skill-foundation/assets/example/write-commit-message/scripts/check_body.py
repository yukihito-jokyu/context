#!/usr/bin/env python3
"""コミットメッセージの本文の箇条書きを、ステージされたファイルと突き合わせる（STEP-02）。

本文の単位は、ステージされたファイルの数で決まる。1 → 本文なし、2〜5 → ファイルごと、6以上 → ディレクトリごと。
箇条書きは `- `<パス>`: <要約>`（ディレクトリは `- `<ディレクトリ>/`: <要約>`）の形にする。

出力: 違反ごとに `STEP-02 <ファイル>:<行> <説明>`。終了コード: 0 合格、1 違反あり

使い方:
  python3 <skill>/scripts/check_body.py <メッセージのファイル> [--root <リポジトリのルート>]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

BULLET = re.compile(r"^- `([^`]+)`: \S")


def staged(root: Path) -> list[str]:
    proc = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True)
    return [line for line in proc.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    lines = Path(args.file).read_text(encoding="utf-8").splitlines()
    files = staged(root)
    if len(files) <= 1:
        expected = []
    elif len(files) <= 5:
        expected = sorted(files)
    else:
        expected = sorted({(str(Path(f).parent) if str(Path(f).parent) != "." else ".") + "/" for f in files})
    errors = []
    found = []
    for number, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        match = BULLET.match(line)
        if not match:
            errors.append(f"STEP-02 {args.file}:{number} 本文の行は「- `<パス>`: <要約>」の形にしてください")
            continue
        found.append(match.group(1))
    if sorted(found) != expected:
        errors.append(f"STEP-02 {args.file} 箇条書きの対象は {expected or '無し（本文を書かない）'} にしてください（今: {sorted(found)}）")
    if found != sorted(found):
        errors.append(f"STEP-02 {args.file} 箇条書きはパスの昇順に並べてください")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
