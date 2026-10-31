#!/usr/bin/env python3
"""Build and exercise the current example without fabricating user approval.

Requires the complete Context Repository and a new work directory. No external
posting, model sessions or installation into an actual user project is performed.
Only the isolated work project receives generated skill placements and hooks.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

REQUEST = ('最新の同梱 write-commit-message の仕様と手順から、ステージ済みの差分とチケットIDを受け取り、'
           '日本語のコミットメッセージを書くスキルを作成してください。Claude CodeとCodexの両方を対象とし、'
           '1行目は「チケットID 要約」、本文は変更ファイルの数に応じた箇条書きにします。'
           'コミット・プッシュは行いません。公開作例の隔離実行なので、実ユーザーとの価値の確認が必要なEvalと、'
           '独立AIによる収束テストは省きます。指摘収集hooks・確認画面・共通形式は追加機能として必ず同梱し、生成スキルの本文やルールに収集指示を加えないでください。hooksなしでも本来の価値が機能することを確かめてください。')
SKIP = '公開作例の隔離実行で、実ユーザーとの価値の確認と独立AIの実行を行わないため'


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--workdir', type=Path, required=True)
    args = parser.parse_args()
    repo, work = args.repo_root.resolve(), args.workdir.resolve()
    if work.exists():
        parser.error('--workdir must not exist')
    source = repo / 'utils/skills/authoring/skill-foundation'
    before = inventory(source)
    example = source / 'assets/example/write-commit-message'
    project = work / 'project'
    results = work / 'results'
    project.mkdir(parents=True)
    results.mkdir()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_CONFIG_NOSYSTEM': '1'}
    logs = []

    def run(stage, command, expected=0, stdin=None):
        result = subprocess.run(list(map(str, command)), cwd=project, env=env, input=stdin,
                                text=True, capture_output=True, timeout=180)
        logs.append({'stage': stage, 'cwd': str(project), 'command': list(map(str, command)),
                     'exit_code': result.returncode, 'output': result.stdout + result.stderr})
        assert result.returncode == expected, stage + '\n' + result.stdout + result.stderr
        return result.stdout + result.stderr

    def foundation(stage, name, *args, **kwargs):
        return run(stage, ['python3', source / 'scripts' / name, *args], **kwargs)

    def json_write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    run('init-temporary-project', ['git', 'init', '-q'])
    foundation('foundation-start', 'run.py', 'start', '--set', 'name=write-commit-message',
               '--set', 'targets=claude,codex', '--set', 'base=.claude/skills', '--set', 'language=ja',
               '--set', 'measure=skip', '--set', 'eval=skip', REQUEST)
    generated = project / '.claude/skills/write-commit-message'
    dev = generated / 'dev'
    dev.mkdir(parents=True)
    spec = json.loads((example / 'spec.json').read_text())
    json_write(dev / 'spec.json', spec)
    json_write(dev / 'eval/eval.json', {'skip_reason': SKIP})
    foundation('eval-check', 'eval_check.py', generated)
    foundation('init-skill', 'init_skill.py', '--dir', generated)
    foundation('phase-1', 'skill_lint.py', generated, '--phase', '1')
    shutil.copyfile(example / 'research.md', dev / 'research.md')
    foundation('phase-3', 'skill_lint.py', generated, '--phase', '3')
    shutil.copytree(example / 'scripts', generated / 'scripts', dirs_exist_ok=True)
    shutil.copytree(example / 'examples', generated / 'assets/examples', dirs_exist_ok=True)
    text = (generated / 'SKILL.md').read_text()
    procedure = (example / 'procedure.md').read_text().strip()
    pattern = re.compile(r'(^## 2\. 手順\n.*?\n)(1\. .*?)(?=\n\n## )', re.S | re.M)
    text, count = pattern.subn(lambda m: m.group(1) + procedure, text)
    assert count == 1
    (generated / 'SKILL.md').write_text(text)
    foundation('render-phase-4', 'render_skill.py', '--dir', generated)
    foundation('phase-4', 'skill_lint.py', generated, '--phase', '4')
    shutil.copyfile(example / 'probes.json', dev / 'probes.json')
    shutil.copytree(example / 'fixtures', dev / 'fixtures', dirs_exist_ok=True)
    probe = foundation('probe', 'probe.py', generated)
    foundation('phase-5', 'skill_lint.py', generated, '--phase', '5')
    shutil.copyfile(example / 'evals.json', dev / 'evals.json')
    spec = json.loads((dev / 'spec.json').read_text())
    spec['status'] = 'ready'
    spec['convergence']['skip_reason'] = SKIP
    json_write(dev / 'spec.json', spec)
    (dev / 'convergence-report.md').write_text('# write-commit-message 収束テストの記録\n\n## 結論\n\n' + SKIP + '。出力の一致率や改善効果は測定していない。\n')
    foundation('render-ready', 'render_skill.py', '--dir', generated)
    run('install-temporary-only', ['python3', generated / 'scripts/install.py', '--project', project])
    lint = foundation('final-lint', 'skill_lint.py', generated, '--final', '--project', project)
    contract = json.loads((generated / 'assets/contract.json').read_text())
    assert 'feedback' not in contract
    for path in ('SKILL.md', 'references/decisions.md'):
        prompt = (generated / path).read_text()
        assert all(marker not in prompt for marker in ('FBK-01', 'feedback.py', '.skill-feedback', 'references/feedback.md'))
    runtime_names = ['_skillrt.py', 'run.py', 'hook.py', 'install.py', 'feedback.py', 'feedback_review.py']
    assert all((generated / 'scripts' / name).read_bytes() == (source / 'scripts' / name).read_bytes() for name in runtime_names)
    assert (generated / 'assets/feedback.schema.json').read_bytes() == (source / 'assets/feedback.schema.json').read_bytes()
    assert (generated / 'references/feedback.md').read_bytes() == (source / 'references/feedback.md').read_bytes()
    hooks = {name: sorted(json.loads((project / path).read_text())['hooks'])
             for name, path in [('claude', '.claude/settings.json'), ('codex', '.codex/hooks.json')]}
    assert all(events == ['PostToolUse', 'PreToolUse', 'Stop', 'UserPromptSubmit'] for events in hooks.values())

    def use(stage, *args, **kwargs):
        return run(stage, ['python3', generated / 'scripts/run.py', *args], **kwargs)

    use('usage-empty-start', 'start', '--set', 'ticket=ABC-12', 'ABC-12 のコミットメッセージを書いて')
    run('usage-empty-diff', ['python3', generated / 'scripts/collect_diff.py'], expected=4)
    use('usage-empty-abort', 'abort', '--reason', 'ステージされた変更が無い')
    (project / 'src').mkdir()
    (project / 'src/app.py').write_text('from src.util import add\n\nprint("1 + 2 =", add(1, 2))\n')
    (project / 'src/util.py').write_text('def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n')
    run('fixture-stage-two-files', ['git', 'add', 'src/app.py', 'src/util.py'])
    use('usage-start', 'start', '--set', 'ticket=abc-12', 'ABC-12 のコミットメッセージを書いて')
    diff = run('usage-diff', ['python3', generated / 'scripts/collect_diff.py'])
    # Authored against the collected staged patch, not copied from a saved public output.
    message = ('ABC-12 足し算の実行例と引き算の関数を追加する\n\n'
               '- `src/app.py`: 足し算の式と結果を表示する実行例を追加する\n'
               '- `src/util.py`: 足し算と引き算の関数を追加する\n')
    output = project / '.skill-runs/write-commit-message/out/commit-message.txt'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(message)
    use('usage-check', 'check')
    use('usage-finish', 'finish')
    assert not (project / '.skill-feedback').exists(), 'Core-only execution must not collect or inject guidance'
    run('usage-stop-hook', ['python3', generated / 'scripts/hook.py', '--platform', 'codex', 'stop'],
        stdin=json.dumps({'cwd': str(project), 'session_id': 'public-example-synthetic-session'}))
    run('feedback-record-validate', ['python3', generated / 'scripts/feedback.py', 'validate'])
    feedback = json.loads((project / '.skill-feedback/write-commit-message/feedback.json').read_text())
    assert len(feedback['deliveries']) == 1 and not feedback['cases'] and not feedback['messages']
    foundation('foundation-check', 'run.py', 'check')
    foundation('foundation-finish', 'run.py', 'finish')
    assert inventory(source) == before

    def redact(value):
        return value.replace(str(repo), '<repository>').replace(str(work), '<workdir>').replace(str(Path.home()), '<user-home>')

    (results / 'execution-log.jsonl').write_text(''.join(redact(json.dumps(item, ensure_ascii=False)) + '\n' for item in logs))
    (results / 'input.md').write_text(REQUEST + '\n\n作成元: 最新の正本に同梱した assets/example/write-commit-message。\n'
        '題材のstaged差分は src/app.py と src/util.py の新規2ファイル、入力チケットは abc-12。\n'
        '生成後はhooksを発火させずにスキルを使ってメッセージを作成し、収集記録が無いことを確認する。その後、合成Stopイベントを直接渡し、追加機能の提示版保存を検証する。コミット・プッシュは実行しない。\n'
        '指摘や確認画面での実ユーザー承認はこの作例では発生していない。会話による承認や合成承認を収集実績に混ぜない。\n')
    for name, content in [('commit-message.txt', output.read_text()), ('usage-diff.patch', diff),
                          ('usage-report.md', (project / '.skill-runs/write-commit-message/report.md').read_text()),
                          ('output.md', (project / '.skill-runs/skill-foundation/report.md').read_text()),
                          ('final-lint.txt', lint), ('probe.log', probe)]:
        (results / name).write_text(redact(content))
    shutil.copyfile(dev / 'results/probe-results.json', results / 'probe-results.json')
    shutil.copyfile(project / '.skill-runs/catalog.html', results / 'catalog.html')
    shutil.copytree(project / '.skill-runs/catalog', results / 'catalog')
    # Rebase links from .skill-runs to this public artifact directory.
    for html in [results / 'catalog.html', *list((results / 'catalog').glob('*.html'))]:
        html.write_text(redact(html.read_text()))
    with zipfile.ZipFile(results / 'write-commit-message.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(generated.rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                archive.write(file, file.relative_to(generated).as_posix())
    shutil.copyfile(Path(__file__), results / 'reproduce_skill.py')
    validation = {'status': 'passed', 'checked_at': datetime.now(timezone.utc).isoformat(),
                  'canonical_source_unchanged': True, 'commands': len(logs), 'rules': len(spec['decisions']),
                  'feedback_extension': {'bundled': True, 'default_registered': True, 'activation': 'hooks_only',
                      'core_prompt_has_no_collection_duties': True, 'core_only_execution_created_no_store': True,
                      'schema_version': 1, 'runtime_files': runtime_names,
                      'runtime_matches_source': True, 'schema_matches_source': True, 'reference_matches_source': True,
                      'registered_hooks': hooks, 'stored_deliveries': len(feedback['deliveries']),
                      'real_user_feedback_cases': 0, 'real_user_approvals': 0},
                  'eval_skipped': SKIP, 'independent_ai_convergence_skipped': SKIP,
                  'not_verified': ['製品内でのhooks自動発火', 'Codex hooks信頼UI', '実ユーザーによる確認画面の承認',
                                   '一般化したEvalのユーザー確認', '独立AIによる改善効果と収束の測定'],
                  'source_materials': 'Current bundled write-commit-message example; research.md retains its original source checks.',
                  'redactions': ['repository absolute path → <repository>', 'work directory → <workdir>', 'user home → <user-home>']}
    json_write(results / 'validation.json', validation)
    print(json.dumps({'status': 'passed', 'results': str(results), 'commands': len(logs), 'rules': len(spec['decisions'])}))


if __name__ == '__main__':
    main()
