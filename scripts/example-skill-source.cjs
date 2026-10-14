const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');

const digest = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function verifyExampleSkillSource({record, exampleDir, currentSource}) {
  if (!record.skill_snapshot) {
    if (record.skill_sha256 !== digest(currentSource)) throw new Error('正本が実行時から変わっています');
    return 'current';
  }
  const root = fs.realpathSync(exampleDir);
  const relative = record.skill_snapshot;
  if (typeof relative !== 'string' || path.isAbsolute(relative)) throw new Error('実行版の保存先は実例内の相対パスが必要です');
  const saved = fs.realpathSync(path.resolve(root, relative));
  if (!saved.startsWith(root + path.sep)) throw new Error('実行版の保存先が実例外です');
  if (!record.skill_version_note?.trim()) throw new Error('実行版と現行版の説明が必要です');
  if (!record.artifacts?.some(file => file.file === relative && file.sha256 === record.skill_sha256)) throw new Error('実行版を原本一覧へ登録してください');
  if (digest(saved) !== record.skill_sha256) throw new Error('保存した実行版が元のハッシュと一致しません');
  return digest(currentSource) === record.skill_sha256 ? 'current' : 'historical';
}

module.exports = {verifyExampleSkillSource};
