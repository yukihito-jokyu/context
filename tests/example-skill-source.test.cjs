const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {verifyExampleSkillSource, sourceManifest, verifyArtifacts, verifySkillInventory, discoverSkills} = require('../scripts/example-skill-source.cjs');
const hash = text => createHash('sha256').update(text).digest('hex');

function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'context-example-source-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  const exampleDir = path.join(dir, 'example');
  const skillDir = path.join(dir, 'skills', 'category', 'demo');
  fs.mkdirSync(exampleDir, {recursive: true});
  fs.mkdirSync(path.join(skillDir, 'references'), {recursive: true});
  fs.mkdirSync(path.join(skillDir, 'scripts'), {recursive: true});
  const currentSource = path.join(skillDir, 'SKILL.md');
  fs.writeFileSync(currentSource, 'original skill\n');
  fs.writeFileSync(path.join(skillDir, 'references', 'guide.md'), 'reference\n');
  fs.writeFileSync(path.join(skillDir, 'scripts', 'run.py'), 'print(1)\n');
  fs.writeFileSync(path.join(exampleDir, 'input.md'), 'request');
  fs.writeFileSync(path.join(exampleDir, 'execution.json'), '{}');
  const record = {skill_sha256: hash('original skill\n'), ...sourceManifest(skillDir), runner: {kind: 'subagent', agent_id: 'test-agent', task: 'Run demo'}, artifacts: [{file: 'input.md', sha256: hash('request')}]};
  return {record, exampleDir, currentSource, skillDir, dir};
}

test('同梱資料全体と実行エージェントを確認する', t => {
  const f = fixture(t);
  assert.equal(verifyExampleSkillSource(f), 'current');
  verifyArtifacts(f);
});
for (const file of ['SKILL.md', 'references/guide.md', 'scripts/run.py']) {
  test(`${file}の更新を検出し、保管した旧版でも回避できない`, t => {
    const f = fixture(t);
    fs.writeFileSync(path.join(f.skillDir, file), 'updated\n');
    assert.throws(() => verifyExampleSkillSource(f), /全削除.*サブエージェント/);
  });
}
test('資料の追加・削除も検出する', t => {
  const f = fixture(t);
  fs.writeFileSync(path.join(f.skillDir, 'new.md'), 'new');
  assert.throws(() => verifyExampleSkillSource(f), /同梱資料/);
  fs.unlinkSync(path.join(f.skillDir, 'new.md'));
  fs.unlinkSync(path.join(f.skillDir, 'references', 'guide.md'));
  assert.throws(() => verifyExampleSkillSource(f), /同梱資料/);
});
test('実行キャッシュだけはスキルの変更として扱わない', t => {
  const f = fixture(t);
  fs.mkdirSync(path.join(f.skillDir, '__pycache__'));
  fs.writeFileSync(path.join(f.skillDir, '__pycache__', 'run.pyc'), 'cache');
  assert.equal(verifyExampleSkillSource(f), 'current');
});
test('移行時の基準は理由と日時が必須で、変更検出は免除しない', t => {
  const f = fixture(t);
  delete f.record.runner;
  assert.throws(() => verifyExampleSkillSource(f), /サブエージェントの実行記録/);
  f.migrationBaselines = {demo: f.record.source_sha256};
  f.record.source_baseline = {reason: '移行前の例。全資料の再実行は未確認。', recorded_at: '2026-10-15T00:00:00Z'};
  assert.equal(verifyExampleSkillSource(f), 'baseline');
  fs.writeFileSync(f.currentSource, 'updated');
  assert.throws(() => verifyExampleSkillSource(f), /同梱資料/);
});
test('未登録ファイルや登録済み出力の改変を拒否する', t => {
  const f = fixture(t);
  fs.writeFileSync(path.join(f.exampleDir, 'old-output.md'), 'old');
  assert.throws(() => verifyArtifacts(f), /未登録/);
  fs.unlinkSync(path.join(f.exampleDir, 'old-output.md'));
  fs.writeFileSync(path.join(f.exampleDir, 'input.md'), 'changed');
  assert.throws(() => verifyArtifacts(f), /原本が記録と一致/);
});
test('成果物のパストラバーサル、重複、未登録の参照先を拒否する', t => {
  const f = fixture(t);
  f.record.artifacts.push({file: '../SKILL.md', sha256: 'x'});
  assert.throws(() => verifyArtifacts(f), /安全な相対パス/);
  f.record.artifacts.pop();
  f.record.artifacts.push({...f.record.artifacts[0]});
  assert.throws(() => verifyArtifacts(f), /重複登録/);
  f.record.artifacts.pop();
  f.record.preview = 'missing.png';
  assert.throws(() => verifyArtifacts(f), /参照先を成果物に登録/);
});
test('成果物のシンボリックリンクで境界を越えられない', t => {
  const f = fixture(t);
  fs.symlinkSync(f.currentSource, path.join(f.exampleDir, 'external.md'));
  assert.throws(() => verifyArtifacts(f), /シンボリックリンク/);
});
test('対応するスキルのない成果物と成果物の欠落を拒否する', t => {
  const f = fixture(t);
  const skills = discoverSkills(path.join(f.dir, 'skills'));
  assert.equal(skills[0].name, 'demo');
  const root = path.join(f.dir, 'artifacts');
  fs.mkdirSync(root);
  assert.throws(() => verifySkillInventory(root, skills), /成果物がない/);
  fs.mkdirSync(path.join(root, 'demo'));
  verifySkillInventory(root, skills);
  fs.mkdirSync(path.join(root, 'orphan'));
  assert.throws(() => verifySkillInventory(root, skills), /対応するスキルのない/);
});
test('再生成コマンドは登録済みスキルの成果物だけを全削除する', t => {
  const {spawnSync} = require('node:child_process');
  const f = fixture(t);
  const sourceRoot = path.join(f.dir, 'utils', 'skills');
  fs.mkdirSync(sourceRoot, {recursive: true});
  fs.cpSync(f.skillDir, path.join(sourceRoot, 'demo'), {recursive: true});
  const artifactRoot = path.join(f.dir, 'docs', 'artifacts', 'skills');
  fs.mkdirSync(path.join(artifactRoot, 'demo', 'nested'), {recursive: true});
  fs.writeFileSync(path.join(artifactRoot, 'demo', 'nested', 'old.md'), 'old');
  fs.mkdirSync(path.join(artifactRoot, 'keep'));
  fs.writeFileSync(path.join(artifactRoot, 'keep', 'keep.md'), 'keep');
  const script = path.resolve(__dirname, '../scripts/reset-example.mjs');
  const run = name => spawnSync(process.execPath, [script, name], {cwd: f.dir, encoding: 'utf8'});
  assert.notEqual(run('../keep').status, 0);
  assert.notEqual(run('unknown').status, 0);
  assert.equal(run('demo').status, 0);
  assert.deepEqual(fs.readdirSync(path.join(artifactRoot, 'demo')), []);
  assert.equal(fs.readFileSync(path.join(artifactRoot, 'keep', 'keep.md'), 'utf8'), 'keep');
});

test('移行基準の付け替えで再実行を回避できない', t => {
  const f = fixture(t);
  f.migrationBaselines = {demo: f.record.source_sha256};
  f.record.source_baseline = {reason: 'initial migration', recorded_at: '2026-10-15T00:00:00Z'};
  fs.writeFileSync(path.join(f.skillDir, 'scripts', 'run.py'), 'changed');
  Object.assign(f.record, sourceManifest(f.skillDir));
  assert.throws(() => verifyExampleSkillSource(f), /初回移行時/);
});
test('旧版の保管情報や本文ハッシュの不一致を許さない', t => {
  const f = fixture(t);
  f.record.skill_snapshot = 'run-SKILL.md';
  assert.throws(() => verifyExampleSkillSource(f), /旧版の保管/);
  delete f.record.skill_snapshot;
  f.record.skill_sha256 = 'old';
  assert.throws(() => verifyExampleSkillSource(f), /SKILL.mdが実行時/);
});
test('pluginの検査はbundle.jsonが指す同梱スキルの変更も検出する', t => {
  const {checkPluginExamples} = require('../scripts/check-plugin-examples.cjs');
  const f = fixture(t);
  const pluginRoot = path.join(f.dir, 'plugins');
  const pluginDir = path.join(pluginRoot, 'demo');
  const artifactRoot = path.join(f.dir, 'plugin-artifacts');
  const exampleDir = path.join(artifactRoot, 'demo');
  fs.mkdirSync(pluginDir, {recursive: true});
  fs.mkdirSync(exampleDir, {recursive: true});
  fs.writeFileSync(path.join(pluginDir, 'bundle.json'), JSON.stringify({skill: path.relative(pluginDir, f.skillDir)}));
  fs.writeFileSync(path.join(exampleDir, 'input.md'), 'request');
  const record = {name: 'demo', kind: 'plugin', runner: f.record.runner, ...sourceManifest(pluginDir), skill_sources: [{file: path.relative(process.cwd(), f.skillDir).split(path.sep).join('/'), ...sourceManifest(f.skillDir)}], artifacts: f.record.artifacts};
  fs.writeFileSync(path.join(exampleDir, 'execution.json'), JSON.stringify(record));
  checkPluginExamples({pluginRoot, artifactRoot});
  fs.writeFileSync(path.join(f.skillDir, 'scripts', 'run.py'), 'changed');
  assert.throws(() => checkPluginExamples({pluginRoot, artifactRoot}), /同梱スキルの正本/);
  fs.writeFileSync(path.join(f.skillDir, 'scripts', 'run.py'), 'print(1)\n');
  fs.writeFileSync(path.join(pluginDir, 'build.py'), 'changed');
  assert.throws(() => checkPluginExamples({pluginRoot, artifactRoot}), /pluginの正本/);
});
