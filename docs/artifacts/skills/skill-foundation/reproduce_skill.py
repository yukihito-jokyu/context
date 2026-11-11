#!/usr/bin/env python3
"""Build and exercise the current example without fabricating user approval.

Requires the complete Context Repository and a new work directory. No external
posting, model sessions or installation into an actual user project is performed.
Only the isolated work project receives generated skill placements and hooks.
The user-scope (global) registration added in issue #111 is exercised only with a
fake HOME inside the work directory; the real ~/.claude and ~/.codex are untouched.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import zipfile

REQUEST = ('最新の同梱 write-commit-message の仕様と手順から、ステージ済みの差分とチケットIDを受け取り、'
           '日本語のコミットメッセージを書くスキルを作成してください。Claude CodeとCodexの両方を対象とし、'
           '1行目は「チケットID 要約」、本文は変更ファイルの数に応じた箇条書きにします。'
           'コミット・プッシュは行いません。公開作例の隔離実行なので、実ユーザーとの価値の確認が必要なEvalと、'
           '独立AIによる収束テストは省きます。hooksの方針は all（Claude CodeとCodexの両方で検査と指摘収集を使い、隔離プロジェクトの設定に登録）とします。'
           '指摘収集hooks・確認画面・共通形式は追加機能として同梱し、生成スキルの本文やルールに収集指示を加えないでください。hooksなしでも本来の価値が機能することを確かめてください。')
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
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_CONFIG_NOSYSTEM': '1',
           'SKILL_FEEDBACK_SYNTHETIC': '1'}
    logs = []

    def run(stage, command, expected=0, stdin=None, cwd=None, run_env=None, timeout=180):
        cwd = cwd or project
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=run_env or env, input=stdin,
                                text=True, capture_output=True, timeout=timeout)
        logs.append({'stage': stage, 'cwd': str(cwd), 'command': list(map(str, command)),
                     'exit_code': result.returncode, 'output': result.stdout + result.stderr})
        assert result.returncode == expected, stage + '\n' + result.stdout + result.stderr
        print(f'PASS {stage}', flush=True)
        return result.stdout + result.stderr

    def foundation(stage, name, *args, **kwargs):
        return run(stage, ['python3', source / 'scripts' / name, *args], **kwargs)

    def json_write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    run('init-temporary-project', ['git', 'init', '-q'])
    # The canonical selftest (including the user-scope stage added in #111) with its temp files inside the work dir.
    selftest_tmp = work / 'selftest-tmp'
    selftest_tmp.mkdir()
    selftest = foundation('foundation-selftest', 'selftest.py',
                          run_env={**env, 'TMPDIR': str(selftest_tmp)}, timeout=900)
    assert not [p for p in selftest_tmp.iterdir() if p.is_dir()], 'selftest must clean its temporary projects'
    foundation('foundation-start', 'run.py', 'start', '--set', 'name=write-commit-message',
               '--set', 'targets=claude,codex', '--set', 'base=.claude/skills', '--set', 'language=ja',
               '--set', 'measure=skip', '--set', 'eval=skip', '--set', 'hooks=all', REQUEST)
    generated = project / '.claude/skills/write-commit-message'
    dev = generated / 'dev'
    dev.mkdir(parents=True)
    json_write(dev / 'eval/eval.json', {'skip_reason': SKIP})
    foundation('eval-check', 'eval_check.py', generated)
    foundation('decide-hooks', 'hooks_plan.py', generated, '--decide', 'all', '--by', 'request',
               '--targets', 'claude,codex')
    foundation('phase-0', 'skill_lint.py', generated, '--phase', '0')
    spec = json.loads((example / 'spec.json').read_text())
    for key in ('hooks', 'feedback', 'hook_targets', 'hook_via'):
        spec.get('control', {}).pop(key, None)
    json_write(dev / 'spec.json', spec)
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
    runtime_names = runpy.run_path(str(source / 'scripts/_lib.py'))['RUNTIME_FILES']
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
    message = ('ABC-12 加減算の関数と足し算の実行例を追加する\n\n'
               '- `src/app.py`: add 関数を呼び、式と計算結果を表示する\n'
               '- `src/util.py`: 2つの値を足す add 関数と引く sub 関数を追加する\n')
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
    assert feedback['synthetic'] is True
    # User (global) scope of the generated skill, with a fake HOME inside the work directory.
    home = work / 'user-home'
    other = work / 'other-project'
    home.mkdir()
    other.mkdir()
    user_env = {**env, 'HOME': str(home), 'CLAUDE_CONFIG_DIR': str(home / '.claude'), 'CODEX_HOME': str(home / '.codex')}
    user_env.pop('CLAUDE_PROJECT_DIR', None)
    run('user-scope-other-project', ['git', 'init', '-q'], cwd=other, run_env=user_env)
    user_install = run('user-scope-install', ['python3', generated / 'scripts/install.py', '--scope', 'user'],
                       cwd=other, run_env=user_env)
    run('user-scope-check', ['python3', generated / 'scripts/install.py', '--scope', 'user', '--check'],
        cwd=other, run_env=user_env)
    places = {'claude': home / '.claude/skills/write-commit-message', 'codex': home / '.agents/skills/write-commit-message'}
    assert all(p.is_symlink() and p.resolve() == generated.resolve() for p in places.values())
    user_configs = {'claude': home / '.claude/settings.json', 'codex': home / '.codex/hooks.json'}
    user_hooks = {k: json.loads(v.read_text())['hooks'] for k, v in user_configs.items()}
    user_commands = {k: [h['command'] for groups in v.values() for g in groups for h in g['hooks']] for k, v in user_hooks.items()}
    assert all(sorted(v) == ['PostToolUse', 'PreToolUse', 'Stop', 'UserPromptSubmit'] for v in user_hooks.values())
    assert all('"$HOME/.claude/skills/write-commit-message/scripts/hook.py"' in c and c.startswith('[ ! -f ')
               for c in user_commands['claude'])
    assert all('"$HOME/.agents/skills/write-commit-message/scripts/hook.py"' in c for c in user_commands['codex'])
    assert not any('CLAUDE_PROJECT_DIR' in c or 'rev-parse' in c for v in user_commands.values() for c in v)
    assert not any((other / rel).exists() for rel in ('.claude', '.agents', '.codex')), 'user scope must not write into the project'
    stop_cmd = next(c for c in user_commands['claude'] if c.endswith(' stop'))
    event = json.dumps({'cwd': str(other), 'session_id': 'public-example-user-scope'})
    user_stop = run('user-scope-stop-other-project', ['sh', '-c', stop_cmd], cwd=other, run_env=user_env, stdin=event)
    assert not any((other / rel).exists() for rel in ('.skill-runs', '.skill-feedback'))
    assert not (generated / '.skill-runs').exists() and not (home / '.skill-runs').exists()
    places['claude'].unlink()
    missing_stop = run('user-scope-stop-missing-script', ['sh', '-c', stop_cmd], cwd=other, run_env=user_env, stdin=event)
    assert missing_stop == ''
    run('user-scope-uninstall', ['python3', generated / 'scripts/install.py', '--scope', 'user', '--uninstall'],
        cwd=other, run_env=user_env)
    assert not any(c for k, v in user_configs.items() if v.is_file()
                   for groups in json.loads(v.read_text()).get('hooks', {}).values() for g in groups for h in g['hooks']
                   for c in [h['command']] if '/write-commit-message/scripts/hook.py' in c)
    assert not places['codex'].exists()
    # The project-scope registration of the isolated project is untouched by the user-scope steps.
    assert {name: sorted(json.loads((project / path).read_text())['hooks'])
            for name, path in [('claude', '.claude/settings.json'), ('codex', '.codex/hooks.json')]} == hooks
    foundation('foundation-check', 'run.py', 'check')
    foundation('foundation-finish', 'run.py', 'finish')
    assert inventory(source) == before

    def redact(value):
        value = value.replace(str(repo), '<repository>').replace(str(work), '<workdir>')
        if str(work).startswith('/private/'):
            value = value.replace(str(work)[len('/private'):], '<workdir>')
        return value.replace(str(Path.home()), '<user-home>')

    (results / 'execution-log.jsonl').write_text(''.join(redact(json.dumps(item, ensure_ascii=False)) + '\n' for item in logs))
    (results / 'input.md').write_text(REQUEST + '\n\n作成元: 最新の正本に同梱した assets/example/write-commit-message。\n'
        '題材のstaged差分は src/app.py と src/util.py の新規2ファイル、入力チケットは abc-12。\n'
        '生成後はhooksを発火させずにスキルを使ってメッセージを作成し、収集記録が無いことを確認する。その後、合成Stopイベントを直接渡し、追加機能の提示版保存を検証する。コミット・プッシュは実行しない。\n'
        '指摘や確認画面での実ユーザー承認はこの作例では発生していない。会話による承認や合成承認を収集実績に混ぜない。\n')
    for name, content in [('commit-message.txt', output.read_text()), ('usage-diff.patch', diff),
                          ('usage-report.md', (project / '.skill-runs/write-commit-message/report.md').read_text()),
                          ('output.md', (project / '.skill-runs/skill-foundation/report.md').read_text()),
                          ('final-lint.txt', lint), ('probe.log', probe), ('selftest.log', selftest),
                          ('user-scope.log', '$ install.py --scope user\n' + user_install
                           + '\n$ Stop hook (other project)\n' + user_stop
                           + '\n$ Stop hook (script removed)\n' + (missing_stop or '(no output, exit 0)\n'))]:
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
                      'runtime_matches_source': True, 'schema_matches_source': True,
                      'reference_matches_source': True,
                      'registered_hooks': hooks, 'stored_deliveries': len(feedback['deliveries']),
                      'synthetic': feedback['synthetic'],
                      'real_user_feedback_cases': 0, 'real_user_approvals': 0},
                  'foundation_selftest': {'passed': True, 'tmpdir_inside_workdir': True},
                  'user_scope': {'fake_home_inside_workdir': True, 'real_home_touched': False,
                      'scope_flag': '--scope user', 'places': ['.claude/skills/write-commit-message', '.agents/skills/write-commit-message'],
                      'configs': ['.claude/settings.json', '.codex/hooks.json'],
                      'registered_hooks': {k: sorted(v) for k, v in user_hooks.items()},
                      'commands_point_to_home': True, 'other_project_untouched': True,
                      'stop_in_other_project_exit_code': 0, 'stop_with_missing_script_exit_code': 0,
                      'stop_with_missing_script_output': missing_stop, 'uninstall_removed_entries': True},
                  'eval_skipped': SKIP, 'independent_ai_convergence_skipped': SKIP,
                  'not_verified': ['製品内でのhooks自動発火', '実際のホーム（~/.claude、~/.codex）へのユーザー単位の導入', 'Codex hooks信頼UI', '実ユーザーによる確認画面の承認',
                                   '一般化したEvalのユーザー確認', '独立AIによる改善効果と収束の測定'],
                  'source_materials': 'Current bundled write-commit-message example; research.md retains its original source checks.',
                  'redactions': ['repository absolute path → <repository>', 'work directory → <workdir>', 'user home → <user-home>']}
    json_write(results / 'validation.json', validation)
    print(json.dumps({'status': 'passed', 'results': str(results), 'commands': len(logs), 'rules': len(spec['decisions'])}))


if __name__ == '__main__':
    main()
