#!/usr/bin/env python3
"""Use the packaged tester while delegating convergence operations to the sealed runtime."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "runtime/skill-foundation/scripts"
sys.path.insert(0, str(CORE))
spec = importlib.util.spec_from_file_location("foundation_convergence", CORE / "convergence.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def packaged_tester(agents_dir):
    if agents_dir:
        raise SystemExit("plugin の専用エージェントを使うため --agents-dir は指定しません")
    return "専用のエージェント型: skill-foundation:skill-foundation-tester（plugin 同梱。プロジェクトには書き出さない）"


module.place_tester = packaged_tester
module.TESTER = "skill-foundation:skill-foundation-tester"

if __name__ == "__main__":
    sys.exit(module.main())
