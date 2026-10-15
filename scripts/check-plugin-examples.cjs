const fs = require('node:fs');
const path = require('node:path');
const {sourceManifest, verifyArtifacts, verifySkillInventory} = require('./example-skill-source.cjs');

function checkPluginExamples({pluginRoot = 'utils/plugins', artifactRoot = 'docs/artifacts/plugins'} = {}) {
  const plugins = fs.readdirSync(pluginRoot, {withFileTypes: true}).filter(entry => entry.isDirectory()).map(entry => ({name: entry.name}));
  verifySkillInventory(artifactRoot, plugins);
  for (const {name} of plugins) {
    const dir = path.join(pluginRoot, name);
    const exampleDir = path.join(artifactRoot, name);
    const record = JSON.parse(fs.readFileSync(path.join(exampleDir, 'execution.json'), 'utf8'));
    if (record.name !== name || record.kind !== 'plugin') throw new Error(`${name}: pluginの識別情報が一致しません`);
    if (record.source_baseline || record.runner?.kind !== 'subagent' || !record.runner.agent_id?.trim() || !record.runner.task?.trim()) throw new Error(`${name}: サブエージェントの実行記録が必要です`);
    const current = sourceManifest(dir);
    if (record.source_sha256 !== current.source_sha256 || JSON.stringify(record.source_files) !== JSON.stringify(current.source_files)) throw new Error(`${name}: pluginの正本が変わっています`);
    const bundle = JSON.parse(fs.readFileSync(path.join(dir, 'bundle.json'), 'utf8'));
    // build.py bundles one full skill directory, declared by bundle.json.
    const skillDir = path.resolve(dir, bundle.skill);
    const expected = [{file: path.relative(process.cwd(), skillDir).split(path.sep).join('/'), ...sourceManifest(skillDir)}];
    if (JSON.stringify(record.skill_sources) !== JSON.stringify(expected)) throw new Error(`${name}: 同梱スキルの正本が変わっています`);
    verifyArtifacts({record, exampleDir});
  }
}

if (require.main === module) {
  checkPluginExamples();
  console.log('pluginの成果物・正本・同梱スキルが一致しています');
}
module.exports = {checkPluginExamples};
