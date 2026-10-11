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
        const guide = path.join('docs', `${relative}.md`);
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

test('全スキルの実例が入力・正本・実出力と対応し、原本を取得できる', () => {
  const digest = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  let count = 0;
  for (const category of fs.readdirSync('utils/skills', {withFileTypes: true}).filter(entry => entry.isDirectory())) {
    for (const skill of fs.readdirSync(`utils/skills/${category.name}`, {withFileTypes: true}).filter(entry => entry.isDirectory())) {
      const source = `utils/skills/${category.name}/${skill.name}/SKILL.md`;
      if (!fs.existsSync(source)) continue;
      count++;
      const root = `docs/artifacts/examples/${skill.name}`;
      const record = JSON.parse(fs.readFileSync(`${root}/execution.json`, 'utf8'));
      assert.equal(record.skill_sha256, digest(source));
      assert.ok(record.stage && record.checks.length);
      assert.ok(fs.readFileSync(`${root}/input.md`, 'utf8').trim());
      const markdown = fs.readFileSync(`docs/${category.name}/${skill.name}.md`, 'utf8');
      assert.ok(!markdown.includes('以下は架空の題材による説明用の抜粋'));
      if (record.text_output) {
        const excerpt = fs.readFileSync(`${root}/${record.text_output}`, 'utf8').trim().split('\n').slice(0, record.excerpt_lines || 16).join('\n');
        assert.ok(markdown.includes(excerpt), `${skill.name}: 抜粋が原本と異なる`);
      }
      const rendered = fs.readFileSync(`build/${category.name}/${skill.name}/index.html`, 'utf8');
      const anchors = rendered.match(/<a\b[^>]*>/g) || [];
      for (const artifact of record.artifacts) {
        assert.equal(digest(`${root}/${artifact.file}`), artifact.sha256, `${skill.name}: 原本の不一致`);
        assert.equal(digest(`build/examples/${skill.name}/${artifact.file}`), artifact.sha256, `${skill.name}: 配信ファイルの不一致`);
      }
      for (const download of [...record.downloads, {file: 'input.md'}, {file: 'execution.json'}]) {
        const href = `/context/examples/${skill.name}/${download.file}`;
        assert.ok(anchors.some(anchor => anchor.includes(`href="${href}"`) && anchor.includes(`download="${download.file}"`)), `${skill.name}: 原本取得リンクがない: ${download.file}`);
      }
      if (record.html_output) {
        assert.ok(anchors.some(anchor => anchor.includes(`href="/context/examples/${skill.name}/${record.html_output}"`) && anchor.includes('target="_blank"')), `${skill.name}: HTMLを開くリンクがない`);
      }
      if (record.preview) {
        const images = rendered.match(/<img\b[^>]*>/g) || [];
        const expected = digest(`${root}/${record.preview}`);
        assert.ok(images.some(tag => {
          const url = tag.match(/src="([^"]+)"/)?.[1];
          return url?.startsWith('/context/') && fs.existsSync(`build/${url.slice('/context/'.length)}`) && digest(`build/${url.slice('/context/'.length)}`) === expected;
        }), `${skill.name}: 掲載画像が撮影原本と一致しない`);
      }
    }
  }
  assert.equal(count, 24);
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
