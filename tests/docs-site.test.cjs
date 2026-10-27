const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {searchDocuments} = require('../plugins/site-search/search-core');

test('公開ガイドが共通スキルの正本をすべて案内する', () => {
  function visit(directory, depth) {
    for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
      if (!entry.isDirectory()) continue;
      const skillDirectory = path.join(directory, entry.name);
      if (fs.existsSync(path.join(skillDirectory, 'SKILL.md'))) {
        const relative = path.relative('utils/skills', skillDirectory);
        const guide = path.join('docs/skills', `${relative}.md`);
        assert.ok(fs.existsSync(guide), `ガイドがないスキル: ${relative}`);
        const text = fs.readFileSync(guide, 'utf8');
        for (const section of ['依頼例', '進め方', '成果物の例', '確認するポイント', '正本を読む']) {
          assert.ok(text.includes(`## ${section}`), `${guide}: ${section}がない`);
        }
        assert.ok(text.includes(`utils/skills/${relative}/SKILL.md`), `${guide}: 正本への参照がない`);
      } else if (depth < 2) visit(skillDirectory, depth + 1);
    }
  }
  visit('utils/skills', 0);
});

test('Skillとpluginの全実例が原本と対応し、公開ガイドから取得できる', () => {
  const digest = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const {discoverSkills, verifyExampleSkillSource, verifyArtifacts, verifySkillInventory} = require('../scripts/example-skill-source.cjs');
  const {checkPluginExamples} = require('../scripts/check-plugin-examples.cjs');
  const skills = discoverSkills();
  verifySkillInventory('docs/artifacts/skills', skills);
  checkPluginExamples();
  const examples = [
    ...skills.map(skill => ({kind: 'skills', name: skill.name, skill, guide: `skills/${path.relative('utils/skills', skill.dir)}`})),
    ...fs.readdirSync('utils/plugins', {withFileTypes: true}).filter(entry => entry.isDirectory()).map(entry => ({kind: 'plugins', name: entry.name, guide: `plugins/${entry.name}`})),
  ];
  for (const example of examples) {
    const {kind, name, guide, skill} = example;
    const root = `docs/artifacts/${kind}/${name}`;
    const record = JSON.parse(fs.readFileSync(`${root}/execution.json`, 'utf8'));
    verifyArtifacts({record, exampleDir: root});
    assert.ok(record.stage && record.checks.length);
    assert.ok(fs.readFileSync(`${root}/input.md`, 'utf8').trim());
    const markdown = fs.readFileSync(`docs/${guide}.md`, 'utf8');
    if (skill) {
      const version = verifyExampleSkillSource({record, currentSource: skill.source});
      if (version === 'baseline') assert.ok(markdown.includes(record.source_baseline.reason), `${name}: 移行時の確認範囲がない`);
      if (record.text_output) {
        const excerpt = fs.readFileSync(`${root}/${record.text_output}`, 'utf8').trim().split('\n').slice(0, record.excerpt_lines || 16).join('\n');
        assert.ok(markdown.includes(excerpt), `${name}: 抜粋が原本と異なる`);
      }
    }
    const rendered = fs.readFileSync(`build/${guide}/index.html`, 'utf8');
    const anchors = rendered.match(/<a\b[^>]*>/g) || [];
    for (const artifact of [...record.artifacts, {file: 'execution.json', sha256: digest(`${root}/execution.json`)}]) {
      assert.equal(digest(`build/${kind}/${name}/${artifact.file}`), artifact.sha256, `${name}: 配信ファイルの不一致`);
    }
    for (const download of [...record.downloads, {file: 'input.md'}, {file: 'execution.json'}]) {
      const href = `/context/${kind}/${name}/${download.file}`;
      const filename = path.posix.basename(download.file);
      assert.ok(anchors.some(anchor => anchor.includes(`href="${href}"`) && anchor.includes(`download="${filename}"`)), `${name}: 原本取得リンクがない: ${download.file}`);
    }
    if (record.html_output) {
      assert.ok(anchors.some(anchor => anchor.includes(`href="/context/${kind}/${name}/${record.html_output}"`) && anchor.includes('target="_blank"')), `${name}: HTMLを開くリンクがない`);
    }
    if (record.preview) {
      const images = rendered.match(/<img\b[^>]*>/g) || [];
      const expected = digest(`${root}/${record.preview}`);
      assert.ok(images.some(tag => {
        const url = tag.match(/src="([^"]+)"/)?.[1];
        return url?.startsWith('/context/') && fs.existsSync(`build/${url.slice('/context/'.length)}`) && digest(`build/${url.slice('/context/'.length)}`) === expected;
      }), `${name}: 掲載画像が撮影原本と一致しない`);
    }
  }
});

test('公開ガイドがpluginの正本と導入方法をすべて案内する', () => {
  for (const plugin of fs.readdirSync('utils/plugins', {withFileTypes: true}).filter(entry => entry.isDirectory())) {
    const file = `docs/plugins/${plugin.name}.md`;
    const text = fs.readFileSync(file, 'utf8');
    for (const section of ['依頼例', '進め方', '成果物の例', '確認するポイント', '正本を読む']) {
      assert.ok(text.includes(`## ${section}`), `${file}: ${section}がない`);
    }
    assert.ok(text.includes(`utils/plugins/${plugin.name}`), `${file}: 正本への参照がない`);
    assert.ok(text.includes('getting-started.md'), `${file}: 導入案内への参照がない`);
  }
});

test('公開文書が検索索引に含まれ、公開ベースパスへ移動できる', () => {
  const {documents} = JSON.parse(fs.readFileSync('.docusaurus/context-search/default/search-index.json', 'utf8'));
  const markdown = fs.readdirSync('docs', {recursive: true}).filter(file => file.endsWith('.md') && !file.startsWith('artifacts/'));
  assert.equal(documents.length, markdown.length);
  assert.equal(new Set(documents.map(doc => doc.permalink)).size, documents.length);
  assert.ok(documents.every(doc => doc.permalink.startsWith('/context/')));
  for (const query of ['成果物', 'ワークフロー', 'ＩＳＳＵＥ－ＴＲＡＣＥ', '未割り当て 条件']) {
    assert.ok(searchDocuments(documents, query).length, `${query}: 検索結果がない`);
  }
});
