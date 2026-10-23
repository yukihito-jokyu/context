#!/usr/bin/env python3
"""manifest から基盤の骨組み（文書、スキル、hooks、検査用スクリプト）を生成する。

既にあるファイルは上書きしない。同じ manifest からは常に同じ内容を生成する。

使い方:
  python3 init_foundation.py --root <基盤のディレクトリ> [--dry-run] [--update-bin]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "assets" / "templates"
BIN_SCRIPTS = ["_lib.py", "rules_check.py", "violation_probe.py", "guard.py", "hooks.py", "convergence.py"]
REQUIRED_KEYS = ["name", "status", "mode", "domain", "stack", "tools", "skills.impl", "skills.review", "language",
                 "commands.check", "commands.fix"]
TOOL_ROLES = ["runtime", "package-manager", "formatter", "linter", "typecheck", "test", "structure", "build", "other"]
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")


def lookup(manifest: dict, dotted: str):
    value = manifest
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


EXAMPLE_PLACEHOLDER = re.compile(r"<[^<>]*(?:[^\x00-\x7f]|commands\.)[^<>]*>")


def find_placeholders(value):
    """manifest.example.json の `<…>`（日本語の説明か commands.* を含むもの）を探す。"""
    if isinstance(value, str):
        yield from EXAMPLE_PLACEHOLDER.findall(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from find_placeholders(item)
    elif isinstance(value, list):
        for item in value:
            yield from find_placeholders(item)


def validate(manifest: dict) -> list[str]:
    errors = []
    for key in REQUIRED_KEYS:
        value = lookup(manifest, key)
        if value in (None, "", [], {}):
            errors.append(f"manifest の {key} が空です")
    if manifest.get("mode") not in ("new", "retrofit"):
        errors.append("manifest の mode は new か retrofit にしてください")
    if manifest.get("status") not in ("building", "ready"):
        errors.append("manifest の status は building（作成中）か ready（フェーズ5の終わり以降）にしてください")
    if not isinstance(manifest.get("domain"), list):
        errors.append("manifest の domain は配列にしてください（例: [\"frontend\"]）")
    for key in ("stack", "tools"):
        items = manifest.get(key)
        if not isinstance(items, list) or not all(isinstance(i, dict) and i.get("name") for i in items):
            errors.append(f"manifest の {key} は、name を持つオブジェクトの配列にしてください")
    for tool in manifest.get("tools", []) if isinstance(manifest.get("tools"), list) else []:
        if isinstance(tool, dict) and tool.get("role") not in TOOL_ROLES:
            errors.append(f"manifest の tools の {tool.get('name')} の role は {TOOL_ROLES} のどれかにしてください")
    for item in manifest.get("stack", []) if isinstance(manifest.get("stack"), list) else []:
        if isinstance(item, dict) and not isinstance(item.get("pinned"), bool):
            errors.append(f"manifest の stack の {item.get('name')} に pinned（true: 指示で名指し / false: 調査で追加）がありません")
    leftovers = sorted(set(find_placeholders(manifest)))
    if leftovers:
        errors.append(f"manifest に例のプレースホルダが残っています: {', '.join(leftovers[:5])}"
                      + (f" ほか {len(leftovers) - 5} 件" if len(leftovers) > 5 else ""))
    name = manifest.get("name", "")
    if name and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("manifest の name は kebab-case（小文字・数字・ハイフン）にしてください")
    for key in ("skills.impl", "skills.review"):
        value = lookup(manifest, key) or ""
        if value and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            errors.append(f"manifest の {key} は kebab-case にしてください")
    return errors


def render(template: str, manifest: dict, source: str) -> str:
    def replace(match: re.Match) -> str:
        value = lookup(manifest, match.group(1))
        if value is None or isinstance(value, (dict, list)):
            raise KeyError(f"{source}: プレースホルダ {{{{{match.group(1)}}}}} に対応する manifest の値がありません")
        return str(value)
    return PLACEHOLDER.sub(replace, template)


def plan_files(manifest: dict) -> list[tuple[str, str]]:
    impl = manifest["skills"]["impl"]
    review = manifest["skills"]["review"]
    return [
        ("AGENTS.md", "AGENTS.md.tmpl"),
        ("CLAUDE.md", "CLAUDE.md.tmpl"),
        ("README.md", "README.md.tmpl"),
        ("docs/design/overview.md", "overview.md.tmpl"),
        ("docs/design/architecture.md", "architecture.md.tmpl"),
        ("docs/design/research.md", "research.md.tmpl"),
        ("docs/design/rules.md", "rules.md.tmpl"),
        ("docs/design/convergence-report.md", "convergence-report.md.tmpl"),
        ("docs/design/adr/0001-machine-enforced-rules.md", "adr-0001.md.tmpl"),
        ("docs/design/adr/_template.md", "adr.md.tmpl"),
        (f".claude/skills/{impl}/SKILL.md", "impl-SKILL.md.tmpl"),
        (f".claude/skills/{impl}/references/patterns.md", "impl-patterns.md.tmpl"),
        (f".claude/skills/{review}/SKILL.md", "review-SKILL.md.tmpl"),
        (".claude/settings.json", "settings.json.tmpl"),
        (".foundation/probes.json", "probes.json.tmpl"),
        (".foundation/convergence/tasks.json", "tasks.json.tmpl"),
        (".foundation/convergence/review-seeds.json", "review-seeds.json.tmpl"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="基盤のディレクトリ（.foundation/manifest.json を置いておく）")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに、作るファイルの一覧だけを出す")
    parser.add_argument("--update-bin", action="store_true",
                        help=".foundation/bin/ の検査用スクリプトを、スキルの最新版で上書きする")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = root / _lib.MANIFEST_REL
    if not manifest_path.is_file():
        _lib.fail(f"{manifest_path} がありません。フェーズ0で manifest を書いてから実行してください")
    manifest = _lib.load_json(manifest_path)
    errors = validate(manifest)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    created, skipped, differs = [], [], []
    try:
        rendered = [(dest, render((TEMPLATES / tmpl).read_text(encoding="utf-8"), manifest, tmpl))
                    for dest, tmpl in plan_files(manifest)]
    except KeyError as exc:
        _lib.fail(str(exc.args[0]))

    for dest, content in rendered:
        target = root / dest
        if target.exists():
            skipped.append(dest)
            continue
        created.append(dest)
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    for script in BIN_SCRIPTS:
        dest = f".foundation/bin/{script}"
        source = SKILL_DIR / "scripts" / script
        target = root / dest
        if target.exists():
            if target.read_bytes() == source.read_bytes():
                skipped.append(dest)
                continue
            if not args.update_bin:
                differs.append(dest)
                continue
        created.append(dest)
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    verb = "作る予定" if args.dry_run else "作成"
    for dest in created:
        print(f"{verb}  {dest}")
    for dest in skipped:
        print(f"既存    {dest}")
    for dest in differs:
        print(f"差分あり {dest}（--update-bin で最新版に置き換えられる）")
    if any(d == ".claude/settings.json" for d in skipped):
        print("注意: .claude/settings.json は既にあるため変更していない。"
              "assets/templates/settings.json.tmpl の hooks を手で統合すること")
    print(f"\n{len(created)} 件{verb}、{len(skipped)} 件は既存のため変更なし、{len(differs)} 件は差分あり")
    print("次: フェーズ2（調査）へ進む。各フェーズで文書とスキルの "
          f"{_lib.TODO_MARKER} を埋め、最後に rules_check.py --final で残りが無いことを確かめる")
    return 0


if __name__ == "__main__":
    sys.exit(main())
