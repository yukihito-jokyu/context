#!/usr/bin/env python3
"""Portable plugin entry; delegate hook behavior to the bundled skill runtime."""
from pathlib import Path
import runpy

plugin=Path(__file__).resolve().parents[1]
hook=plugin/'skills/generate-domain-model/scripts/hook.py'
if not hook.is_file():
    hook=plugin.parents[1]/'skills/design/generate-domain-model/scripts/hook.py'
runpy.run_path(str(hook),run_name='__main__')
