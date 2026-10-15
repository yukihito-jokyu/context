import fs from 'node:fs';
import path from 'node:path';
import sourceVerification from './example-skill-source.cjs';

// This command deliberately deletes the complete saved run, including its record.
// A new run must be produced by a subagent; this command never invents outputs.
const name = process.argv[2];
if (process.argv.length !== 3 || !name || !/^[a-z0-9][a-z0-9-]*$/.test(name)) {
  throw new Error('使い方: node scripts/reset-example.mjs <skill-name>');
}
const skill = sourceVerification.discoverSkills().find(item => item.name === name);
if (!skill) throw new Error(`登録されたスキルではありません: ${name}`);
const root = path.resolve('docs/artifacts/skills');
const target = path.join(root, name);
if (fs.existsSync(target) && fs.lstatSync(target).isSymbolicLink()) throw new Error('成果物ディレクトリがシンボリックリンクです');
fs.rmSync(target, {recursive: true, force: true});
fs.mkdirSync(target, {recursive: true});
console.log(JSON.stringify({skill: name, skill_source: skill.source, ...sourceVerification.sourceManifest(skill.dir), next: 'サブエージェントでスキルを実行し、入力・実出力・検証結果とrunnerをexecution.jsonに記録してください。'}, null, 2));
