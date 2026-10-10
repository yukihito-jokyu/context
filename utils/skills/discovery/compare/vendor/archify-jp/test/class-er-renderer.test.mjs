import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(here, '..');
const cli = path.join(skillRoot, 'bin', 'archify.mjs');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-class-er-'));

function run(args) {
  return spawnSync(process.execPath, [cli, ...args], { cwd: skillRoot, encoding: 'utf8' });
}

function renderTwice(type, fixture) {
  const first = path.join(tmp, `${type}-first.html`);
  const second = path.join(tmp, `${type}-second.html`);
  for (const output of [first, second]) {
    const result = run(['render', type, path.join(skillRoot, 'examples', fixture), output]);
    assert.equal(result.status, 0, result.stderr);
  }
  const html = fs.readFileSync(first, 'utf8');
  assert.equal(html, fs.readFileSync(second, 'utf8'), `${type} render must be deterministic`);
  assert.match(html, new RegExp(`data-diagram-type="${type}"`));
  assert.match(html, /data-focus-camera="node"/);
  assert.match(html, /data-node-id="[^"]+"[^>]*>\s*<g transform="translate\(/,
    'the focus target must wrap translated geometry');
  assert.doesNotMatch(html, /data-node-id="[^"]+"[^>]*transform="translate\(/,
    'getBBox must resolve the node in diagram coordinates');
  return html;
}

test('class renderer emits deterministic UML compartments and relationship markers', () => {
  const html = renderTwice('class', 'domain-model.class.json');
  assert.match(html, /&lt;&lt;aggregate root&gt;&gt;/);
  assert.match(html, /− id: UUID/);
  assert.match(html, /\+ addLine\(/);
  assert.match(html, /class-diamond-filled/);
  assert.match(html, /class-triangle/);
  assert.match(html, /class-arrow-open/);
});

test('ER renderer emits deterministic column metadata and Crow’s Foot markers', () => {
  const html = renderTwice('er', 'ecommerce.er.json');
  assert.match(html, />PK</);
  assert.match(html, />FK</);
  assert.match(html, />UQ</);
  assert.match(html, /cf-zero-or-many/);
  assert.match(html, /cf-one-or-many/);
  assert.match(html, /cf-zero-or-one/);
  assert.match(html, /non-identifying/);
});

test('class and ER renderers reject unresolved semantic references without publishing output', () => {
  const cases = [
    {
      type: 'class', fixture: 'domain-model.class.json',
      mutate(source) { source.relationships[0].to = 'missing_class'; },
      message: /不明なクラス/,
    },
    {
      type: 'er', fixture: 'ecommerce.er.json',
      mutate(source) { source.entities[1].columns[1].foreign_key.column = 'missing_column'; },
      message: /不明な列/,
    },
  ];

  for (const item of cases) {
    const source = JSON.parse(fs.readFileSync(path.join(skillRoot, 'examples', item.fixture), 'utf8'));
    item.mutate(source);
    const input = path.join(tmp, `invalid-${item.type}.json`);
    const output = path.join(tmp, `invalid-${item.type}.html`);
    fs.writeFileSync(input, JSON.stringify(source));
    const result = run(['render', item.type, input, output]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, item.message);
    assert.equal(fs.existsSync(output), false);
  }
});

test('shared camera policy opts class/ER into node-only focus', () => {
  const template = fs.readFileSync(path.join(skillRoot, 'assets', 'template.html'), 'utf8');
  assert.match(template, /svg\.getAttribute\('data-focus-camera'\) === 'node'/);
  assert.match(template, /\['focus', 'focus-sync', 'relationship', 'radar', 'finder'\]/);
  assert.match(template, /options\.includeNeighbors = false/);
});
