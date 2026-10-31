const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');

const digest = data => createHash('sha256').update(data).digest('hex');
const ignoredDirectories = new Set(['.git', 'node_modules', '__pycache__']);

function collectFiles(root, ignoreCaches = false) {
  const files = [];
  function visit(relative) {
    for (const entry of fs.readdirSync(path.join(root, relative), {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
      const file = relative ? `${relative}/${entry.name}` : entry.name;
      if (ignoreCaches && (ignoredDirectories.has(entry.name) || entry.name.endsWith('.pyc'))) continue;
      // These local evaluation records are excluded from Git by the skill workflow.
      // Artifact inventories still include every file; only source inventories omit them.
      if (ignoreCaches && /(?:^|\/)dev\/(?:results(?:\/|$)|convergence-report\.md$)/.test(file)) continue;
      if (entry.isSymbolicLink()) throw new Error(`シンボリックリンクは登録できません: ${file}`);
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) files.push(file);
      else throw new Error(`通常ファイル以外は登録できません: ${file}`);
    }
  }
  visit('');
  return files.sort();
}

function sourceManifest(skillDir) {
  const source_files = collectFiles(skillDir, true).map(file => ({file, sha256: digest(fs.readFileSync(path.join(skillDir, file)))}));
  return {source_files, source_sha256: digest(JSON.stringify(source_files))};
}

function discoverSkills(root = 'utils/skills') {
  const result = [];
  function visit(dir) {
    if (fs.existsSync(path.join(dir, 'SKILL.md'))) {
      result.push({name: path.basename(dir), dir, source: path.join(dir, 'SKILL.md')});
      return;
    }
    for (const entry of fs.readdirSync(dir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
      if (entry.isDirectory() && !ignoredDirectories.has(entry.name)) visit(path.join(dir, entry.name));
    }
  }
  visit(root);
  const names = result.map(skill => skill.name);
  if (new Set(names).size !== names.length) throw new Error('スキル名が重複しています');
  return result;
}

function verifyExampleSkillSource({record, currentSource, migrationBaselines = require('./example-migration-baselines.json')}) {
  if (record.skill_snapshot || record.skill_version_note) throw new Error('旧版の保管による免除は廃止しました。サブエージェントで再実行してください');
  const current = sourceManifest(path.dirname(currentSource));
  if (!Array.isArray(record.source_files) || !record.source_sha256) throw new Error('スキル全体のsource_filesとsource_sha256が必要です');
  if (JSON.stringify(current.source_files) !== JSON.stringify(record.source_files) || current.source_sha256 !== record.source_sha256) {
    throw new Error('正本または同梱資料が変わっています。成果物を全削除し、サブエージェントで再実行してください');
  }
  if (record.skill_sha256 !== digest(fs.readFileSync(currentSource))) throw new Error('SKILL.mdが実行時と一致しません');
  if (record.source_baseline) {
    const name = path.basename(path.dirname(currentSource));
    if (migrationBaselines[name] !== record.source_sha256) throw new Error('初回移行時の基準ではありません。サブエージェントで再実行してください');
    if (!record.source_baseline.reason?.trim() || !record.source_baseline.recorded_at || Number.isNaN(Date.parse(record.source_baseline.recorded_at))) {
      throw new Error('移行基準には理由と記録日時が必要です');
    }
    return 'baseline';
  }
  if (record.runner?.kind !== 'subagent' || !record.runner.agent_id?.trim() || !record.runner.task?.trim()) {
    throw new Error('サブエージェントの実行記録が必要です');
  }
  return 'current';
}

function safeArtifactPath(relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || path.posix.isAbsolute(relative) || relative.split('/').some(part => !part || part === '.' || part === '..')) {
    throw new Error(`成果物は安全な相対パスで登録してください: ${relative}`);
  }
  return relative;
}

function verifyArtifacts({record, exampleDir}) {
  const actual = collectFiles(exampleDir);
  if (!Array.isArray(record.artifacts)) throw new Error('artifacts一覧が必要です');
  const registered = new Set(['execution.json']);
  for (const artifact of record.artifacts) {
    const file = safeArtifactPath(artifact.file);
    if (registered.has(file)) throw new Error(`成果物の重複登録: ${file}`);
    registered.add(file);
    if (!actual.includes(file)) throw new Error(`登録された成果物がありません: ${file}`);
    if (digest(fs.readFileSync(path.join(exampleDir, file))) !== artifact.sha256) throw new Error(`原本が記録と一致しません: ${file}`);
  }
  for (const file of actual) if (!registered.has(file)) throw new Error(`未登録の成果物があります: ${file}`);
  for (const file of ['input.md', ...(record.downloads || []).map(item => item.file), record.input, record.preview, record.text_output, record.html_output].filter(Boolean)) {
    safeArtifactPath(file);
    if (!registered.has(file) || file === 'execution.json') throw new Error(`参照先を成果物に登録してください: ${file}`);
  }
}

function verifySkillInventory(root, skills) {
  const expected = new Set(skills.map(skill => skill.name));
  const actual = fs.readdirSync(root, {withFileTypes: true});
  for (const entry of actual) {
    if (!entry.isDirectory() || !expected.has(entry.name)) throw new Error(`対応するスキルのない成果物: ${entry.name}`);
    expected.delete(entry.name);
  }
  if (expected.size) throw new Error(`成果物がないスキル: ${[...expected].join(', ')}`);
}

module.exports = {verifyExampleSkillSource, sourceManifest, discoverSkills, verifyArtifacts, verifySkillInventory};
