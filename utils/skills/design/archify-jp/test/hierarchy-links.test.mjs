import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateSchema } from '../renderers/shared/validator.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(__dirname, '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-links-'));

// One example per type and the path to its focusable node collection.
const CASES = {
  architecture: ['web-app.architecture.json', ['components']],
  workflow: ['agent-tool-call.workflow.json', ['nodes']],
  sequence: ['cache-miss-request.sequence.json', ['participants']],
  dataflow: ['product-analytics.dataflow.json', ['nodes']],
  lifecycle: ['agent-run.lifecycle.json', ['states']],
  class: ['domain-model.class.json', ['classes']],
  er: ['ecommerce.er.json', ['entities']],
  'sequence-er': ['join-update-delete.sequence-er.json', ['sequence', 'participants']],
  'workflow-er': ['task-operations.workflow-er.json', ['workflow', 'nodes']],
};

function example(type) {
  const diagram = JSON.parse(fs.readFileSync(path.join(skillRoot, 'examples', CASES[type][0]), 'utf8'));
  delete diagram.meta.output;
  return diagram;
}

function nodesOf(type, diagram) {
  return CASES[type][1].reduce((value, key) => value[key], diagram);
}

function render(type, diagram, name = type) {
  const input = path.join(tmp, `${name}.json`);
  const output = path.join(tmp, `${name}.html`);
  fs.writeFileSync(input, JSON.stringify(diagram));
  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'bin/archify.mjs'), 'render', type, input, output,
    // The composite examples cite SQL evidence relative to the skill root.
    ...(type.endsWith('-er') ? ['--repo-root', skillRoot] : []),
  ], { encoding: 'utf8' });
  return { ...result, html: result.status === 0 ? fs.readFileSync(output, 'utf8') : '' };
}

test('every diagram type accepts node links and meta.hierarchy in its schema', () => {
  for (const type of Object.keys(CASES)) {
    const diagram = example(type);
    nodesOf(type, diagram)[0].link = { href: '../detail/child.html', focus: 'step', view: 'main', label: '詳細' };
    diagram.meta.hierarchy = { parent: { href: '../root.html', label: '全体図' }, map: { href: 'map.html' }, require_links: false };
    assert.doesNotThrow(() => validateSchema(type, diagram), type);
  }
});

test('node link href must be a relative .html path', () => {
  for (const href of ['https://example.com/a.html', '/abs/a.html', 'javascript:alert(1).html', 'detail.json', 'a b.html']) {
    const diagram = example('architecture');
    diagram.components[0].link = { href };
    assert.throws(() => validateSchema('architecture', diagram), undefined, href);
  }
});

test('every renderer carries node links into the viewer as data attributes', () => {
  for (const type of Object.keys(CASES)) {
    const diagram = example(type);
    const node = nodesOf(type, diagram)[0];
    node.link = { href: 'detail/child.html', focus: 'step', view: 'main', label: '子 & 詳細' };
    const { status, stderr, html } = render(type, diagram);
    assert.equal(status, 0, `${type}: ${stderr}`);
    const tag = html.match(/<g\b[^>]*data-node-link-href="detail\/child\.html"[^>]*>/)?.[0];
    assert.ok(tag, `${type} must emit data-node-link-href`);
    assert.match(tag, /data-node-link-focus="step"/, type);
    assert.match(tag, /data-node-link-view="main"/, type);
    assert.match(tag, /data-node-link-label="子 &amp; 詳細"/, type);
  }
});

test('parent and map navigation is embedded only when authored', () => {
  const plain = render('architecture', example('architecture'), 'plain');
  assert.equal(plain.status, 0, plain.stderr);
  assert.doesNotMatch(plain.html, /id="archify-hierarchy-data"/);

  const diagram = example('architecture');
  diagram.meta.hierarchy = { parent: { href: '../root.html', label: '全体図' }, map: { href: '../map.html', label: 'マップ' } };
  const { status, stderr, html } = render('architecture', diagram, 'with-parent');
  assert.equal(status, 0, stderr);
  const payload = JSON.parse(html.match(/<script id="archify-hierarchy-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
  assert.deepEqual(payload, {
    parent: { href: '../root.html', label: '全体図' },
    map: { href: '../map.html', label: 'マップ' },
    trail: [],
    siblings: [],
    incoming: [],
    level: 0,
    title: diagram.meta.title,
    role: null,
  });

  diagram.meta.hierarchy.trail = [{ href: '../root.html', label: '全体図' }, { href: '../map.html', label: 'events', focus: 'c-events' }];
  diagram.components[0].link = { href: 'detail/a.html', onward: 3 };
  const synced = render('architecture', diagram, 'with-trail');
  assert.equal(synced.status, 0, synced.stderr);
  const trailPayload = JSON.parse(synced.html.match(/<script id="archify-hierarchy-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
  assert.equal(trailPayload.level, 2);
  assert.deepEqual(trailPayload.trail[1], { href: '../map.html', label: 'events', focus: 'c-events' });
  assert.match(synced.html, /data-node-link-onward="3"/);
});

test('require_links fails the render for nodes without a destination', () => {
  const diagram = example('architecture');
  diagram.meta.hierarchy = { require_links: true };
  diagram.components.forEach((component, index) => {
    if (index > 0) component.link = { href: `detail/${component.id}.html` };
  });
  const missing = render('architecture', diagram, 'missing-link');
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /hierarchy\/missing-link|遷移先がありません/);
  assert.match(missing.stderr, new RegExp(diagram.components[0].id));

  diagram.meta.hierarchy.leaf_nodes = [{ id: diagram.components[0].id, reason: '外部システムで詳細図を持たない' }];
  const leaf = render('architecture', diagram, 'leaf-ok');
  assert.equal(leaf.status, 0, leaf.stderr);
});

test('leaf_nodes must name existing nodes without links', () => {
  const unknown = example('architecture');
  unknown.meta.hierarchy = { leaf_nodes: [{ id: 'ghost', reason: 'なし' }] };
  const first = render('architecture', unknown, 'leaf-unknown');
  assert.notEqual(first.status, 0);
  assert.match(first.stderr, /ghost/);

  const linked = example('architecture');
  linked.components[0].link = { href: 'a.html' };
  linked.meta.hierarchy = { leaf_nodes: [{ id: linked.components[0].id, reason: '矛盾' }] };
  const second = render('architecture', linked, 'leaf-linked');
  assert.notEqual(second.status, 0);
  assert.match(second.stderr, /leaf_nodes に含められません/);
});

test('an architecture boundary links its members as one group', () => {
  const grouped = () => {
    const diagram = example('architecture');
    const sg = diagram.boundaries.find((boundary) => boundary.wraps.includes('api') && boundary.wraps.length === 2);
    sg.id = 'sg';
    sg.link = { href: 'detail/sg.html', label: 'API 層' };
    return diagram;
  };
  // The frame carries the same link attributes as a node.
  const { status, stderr, html } = render('architecture', grouped(), 'group-link');
  assert.equal(status, 0, stderr);
  assert.match(html, /<rect[^>]*data-boundary-id="sg"[^>]*data-node-link-href="detail\/sg\.html"/);

  // A member cannot carry its own link as well.
  const conflict = grouped();
  conflict.components.find((component) => component.id === 'api').link = { href: 'detail/api.html' };
  const rejected = render('architecture', conflict, 'group-link-conflict');
  assert.notEqual(rejected.status, 0);
  assert.match(rejected.stderr, /hierarchy\/group-link|中のノード "api" には link を書けません/);

  // require_links counts the members as linked.
  const required = grouped();
  required.meta.hierarchy = {
    require_links: true,
    leaf_nodes: required.components.filter((c) => !['lb', 'api'].includes(c.id)).map((c) => ({ id: c.id, reason: 'テスト' })),
  };
  const covered = render('architecture', required, 'group-link-required');
  assert.equal(covered.status, 0, covered.stderr);
});

test('a boundary with an id can be a connection endpoint', () => {
  const diagram = example('architecture');
  delete diagram.meta.quality_profile;
  const sg = diagram.boundaries.find((boundary) => boundary.wraps.includes('api') && boundary.wraps.length === 2);
  sg.id = 'sg';
  diagram.connections.push({ id: 'to-group', from: 'worker', to: 'sg', label: 'グループへ' });
  const { status, stderr, html } = render('architecture', diagram, 'group-endpoint');
  assert.equal(status, 0, stderr);
  assert.match(html, /data-edge-from="worker" data-edge-to="sg"/);
});
