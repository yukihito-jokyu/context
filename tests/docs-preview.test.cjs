const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

test('プレビューが全ガイドと全原本をリダイレクトせず配信する', {timeout: 30000}, async t => {
  const child = spawn(process.execPath, ['scripts/serve-docs.cjs', '--port', '0'], {stdio: ['ignore', 'pipe', 'pipe']});
  t.after(() => child.kill('SIGTERM'));
  const base = await new Promise((resolve, reject) => {
    let stdout = '', stderr = '';
    child.stderr.on('data', chunk => {stderr += chunk;});
    child.on('error', reject);
    child.on('exit', code => reject(new Error(`プレビュー起動失敗 (${code}): ${stderr}`)));
    child.stdout.on('data', chunk => {
      stdout += chunk;
      const match = stdout.match(/Preview: (http:\/\/127\.0\.0\.1:\d+\/context\/)/);
      if (match) resolve(match[1]);
    });
  });
  const {documents} = JSON.parse(fs.readFileSync('.docusaurus/context-search/default/search-index.json'));
  for (const doc of documents) {
    const relative = doc.permalink.slice('/context/'.length);
    const response = await fetch(base + relative, {redirect: 'error'});
    assert.equal(response.status, 200, doc.permalink);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), fs.readFileSync(path.join('build', relative, 'index.html')));
  }
  for (const skill of fs.readdirSync('docs/artifacts/examples')) {
    const root = `docs/artifacts/examples/${skill}`;
    const record = JSON.parse(fs.readFileSync(`${root}/execution.json`));
    for (const artifact of [...record.artifacts, {file: 'execution.json'}]) {
      const relative = `examples/${skill}/${artifact.file}`;
      const response = await fetch(base + relative, {redirect: 'error'});
      assert.equal(response.status, 200, relative);
      assert.deepEqual(Buffer.from(await response.arrayBuffer()), fs.readFileSync(`${root}/${artifact.file}`), relative);
    }
  }
});
