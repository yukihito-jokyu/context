#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["numpy>=2.0"]
# ///
"""設計図(TOML)からループBGMを書き出す。使い方: uv run render.py songs/曲名.toml [--style gameboy]"""

from bgm.__main__ import main

if __name__ == "__main__":
    main()
