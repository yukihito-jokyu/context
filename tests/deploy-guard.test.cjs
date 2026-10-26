const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function runGuard(t, {sha = 'current', latest = 'current', apiStatus = 0} = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'deploy-guard-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  fs.writeFileSync(path.join(dir, 'gh'), [
    '#!/usr/bin/env bash',
    '[[ "$*" == "api repos/example/context/git/ref/heads/main --jq .object.sha" ]] || exit 2',
    'printf "%s\\n" "$MOCK_MAIN_SHA"',
    'exit "$MOCK_API_STATUS"',
    '',
  ].join('\n'), {mode: 0o755});
  return spawnSync('bash', [path.resolve('.github/scripts/check-main-revision.sh')], {
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: `${dir}${path.delimiter}${process.env.PATH}`,
      REPOSITORY: 'example/context',
      SHA: sha,
      MOCK_MAIN_SHA: latest,
      MOCK_API_STATUS: String(apiStatus),
    },
  });
}

test('公開するコミットが最新のmainなら公開を許可する', t => {
  const result = runGuard(t);
  assert.equal(result.status, 0, result.stderr);
});

test('古いコミットの公開はエラーにする', t => {
  const result = runGuard(t, {sha: 'old'});
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stdout, /::error::main has advanced/);
});

test('mainの取得に失敗したときは一致する値が出力されても公開しない', t => {
  const result = runGuard(t, {apiStatus: 7});
  assert.equal(result.status, 7, result.stderr);
});
