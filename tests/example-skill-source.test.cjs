const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {verifyExampleSkillSource} = require('../scripts/example-skill-source.cjs');

function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'context-example-source-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  const exampleDir = path.join(dir, 'example');
  fs.mkdirSync(exampleDir);
  const currentSource = path.join(dir, 'SKILL.md');
  fs.writeFileSync(currentSource, 'original skill\n');
  const hash = createHash('sha256').update('original skill\n').digest('hex');
  const record = {skill_sha256: hash, artifacts: []};
  return {record, exampleDir, currentSource};
}

function archive(f) {
  fs.copyFileSync(f.currentSource, path.join(f.exampleDir, 'run-SKILL.md'));
  f.record.skill_snapshot = 'run-SKILL.md';
  f.record.skill_version_note = '旧手順で実行した例です。';
  f.record.artifacts.push({file: 'run-SKILL.md', sha256: f.record.skill_sha256});
  fs.writeFileSync(f.currentSource, 'updated skill\n');
}

test('実行版と現在版が同じ例を検証する', t => {
  assert.equal(verifyExampleSkillSource(fixture(t)), 'current');
});
test('保管版がない場合は正本の変更を引き続き拒否する', t => {
  const f = fixture(t);
  fs.writeFileSync(f.currentSource, 'updated skill\n');
  assert.throws(() => verifyExampleSkillSource(f), /正本が実行時/);
});
test('元のハッシュを保持した実行版と明示した説明がある旧例を検証する', t => {
  const f = fixture(t); archive(f);
  assert.equal(verifyExampleSkillSource(f), 'historical');
});
test('保管した実行版の改変を拒否する', t => {
  const f = fixture(t); archive(f);
  fs.writeFileSync(path.join(f.exampleDir, 'run-SKILL.md'), 'changed after the run\n');
  assert.throws(() => verifyExampleSkillSource(f), /元のハッシュ/);
});
test('旧版の説明や原本登録がない記録を拒否する', t => {
  const f = fixture(t); archive(f);
  delete f.record.skill_version_note;
  assert.throws(() => verifyExampleSkillSource(f), /説明が必要/);
  f.record.skill_version_note = '旧手順の例'; f.record.artifacts = [];
  assert.throws(() => verifyExampleSkillSource(f), /原本一覧/);
});
test('実例の外側を保管版として指定することを拒否する', t => {
  const f = fixture(t); archive(f);
  f.record.skill_snapshot = '../SKILL.md';
  assert.throws(() => verifyExampleSkillSource(f), /実例外/);
});
