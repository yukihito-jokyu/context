import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkHierarchy, clipLabel, syncHierarchy } from '../renderers/shared/hierarchy-graph.mjs';
import { readGeometry } from '../renderers/shared/hierarchy-locator.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(__dirname, '..');
const cli = path.join(skillRoot, 'bin/archify.mjs');

function architecture(title, components, hierarchy) {
  return {
    schema_version: 1,
    diagram_type: 'architecture',
    meta: { title, ...(hierarchy ? { hierarchy } : {}) },
    components: components.map((component, index) => ({
      type: 'backend',
      pos: [40 + index * 240, 80],
      size: [160, 64],
      ...component,
    })),
    connections: components.length > 1 ? [{ from: components[0].id, to: components[1].id }] : [],
  };
}

function write(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2));
}

function render(spec) {
  const html = spec.replace(/\.architecture\.json$/, '.html');
  execFileSync(process.execPath, [cli, 'render', 'architecture', spec, html], { stdio: 'pipe' });
}

// root.html ── api ──▶ child/child.html#focus=handler
//           └─ db: leaf_nodes（理由付き）
function fixture(mutate = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-check-hierarchy-'));
  const root = path.join(dir, 'root.architecture.json');
  const child = path.join(dir, 'child', 'child.architecture.json');
  const rootSpec = architecture('全体図', [
    { id: 'api', label: 'API', link: { href: 'child/child.html', focus: 'handler', label: 'API の詳細' } },
    { id: 'db', label: 'DB' },
  ], { map: { href: 'map.html' }, require_links: true, leaf_nodes: [{ id: 'db', reason: 'マネージドDBで内部構造を描かない' }] });
  const childSpec = architecture('API の詳細', [
    { id: 'router', label: 'Router' },
    { id: 'handler', label: 'Handler' },
  ], { parent: { href: '../root.html', label: '全体図' }, map: { href: '../map.html' } });
  childSpec.meta.views = [{ id: 'flow', label: '処理', focus: ['router', 'handler'] }];
  mutate.root?.(rootSpec);
  mutate.child?.(childSpec);
  write(root, rootSpec);
  write(child, childSpec);
  // Breadcrumbs and onward counts are derived facts; sync before rendering.
  syncHierarchy(root);
  render(root);
  render(child);
  fs.writeFileSync(path.join(dir, 'map.html'), '<!doctype html>');
  return { dir, root, child };
}

const codes = (result) => result.diagnostics.map((d) => d.code);

// hierarchy-sync fills a missing parent, so drop it after the fixture is synced.
function withoutParent() {
  const made = fixture();
  const spec = JSON.parse(fs.readFileSync(made.child, 'utf8'));
  delete spec.meta.hierarchy.parent;
  fs.writeFileSync(made.child, JSON.stringify(spec, null, 2));
  render(made.child);
  return made;
}

test('a consistent two-level hierarchy passes with both diagrams reached', () => {
  const { root } = fixture();
  const result = checkHierarchy(root);
  assert.deepEqual(result.diagnostics, []);
  assert.equal(result.ok, true);
  assert.deepEqual(result.diagrams.map((d) => d.title), ['全体図', 'API の詳細']);
  assert.equal(result.edges.length, 1);
});

test('a link to a diagram that does not exist yet is an error', () => {
  const { root } = fixture({ root: (spec) => { spec.components[1].link = { href: 'db/db.html' }; spec.meta.hierarchy.leaf_nodes = []; } });
  const result = checkHierarchy(root);
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes('hierarchy/link-target-missing'), codes(result).join());
});

test('focus and view anchors must exist in the rendered target', () => {
  const { root } = fixture({ root: (spec) => { spec.components[0].link = { href: 'child/child.html', focus: 'ghost', view: 'nope' }; } });
  const result = checkHierarchy(root);
  assert.ok(codes(result).includes('hierarchy/focus-missing'), codes(result).join());
  assert.ok(codes(result).includes('hierarchy/view-missing'), codes(result).join());
});

test('a parent that does not link back is a mismatch, a missing parent is a warning', () => {
  const mismatch = checkHierarchy(fixture({ child: (spec) => { spec.meta.hierarchy.parent = { href: '../other.html', label: '別の図' }; } }).root);
  assert.ok(codes(mismatch).includes('hierarchy/parent-mismatch'), codes(mismatch).join());

  const missing = checkHierarchy(withoutParent().root);
  const diagnostic = missing.diagnostics.find((d) => d.code === 'hierarchy/parent-missing');
  assert.equal(diagnostic?.severity, 'warning');
  assert.equal(missing.ok, true);
});

test('editing a spec without re-rendering is reported as stale HTML', () => {
  const { root } = fixture();
  const spec = JSON.parse(fs.readFileSync(root, 'utf8'));
  spec.components[0].link.focus = 'router';
  fs.writeFileSync(root, JSON.stringify(spec));
  const result = checkHierarchy(root);
  assert.ok(codes(result).includes('hierarchy/stale-html'), codes(result).join());
  render(root);
  assert.equal(checkHierarchy(root).ok, true);
});

test('require_links reports every node without a destination or leaf reason', () => {
  const { root } = fixture();
  const spec = JSON.parse(fs.readFileSync(root, 'utf8'));
  spec.meta.hierarchy.leaf_nodes = [];
  fs.writeFileSync(root, JSON.stringify(spec));
  const result = checkHierarchy(root);
  const missing = result.diagnostics.filter((d) => d.code === 'hierarchy/missing-link');
  assert.deepEqual(missing.map((d) => d.subject.node), ['db']);
});

test('missing map and unreachable diagrams are reported', () => {
  const { dir, root } = fixture();
  fs.rmSync(path.join(dir, 'map.html'));
  write(path.join(dir, 'stray', 'stray.architecture.json'), architecture('迷子', [{ id: 'x', label: 'X' }]));
  const result = checkHierarchy(root, { scanDir: dir });
  assert.ok(codes(result).includes('hierarchy/map-missing'), codes(result).join());
  const orphan = result.diagnostics.find((d) => d.code === 'hierarchy/orphan');
  assert.equal(orphan?.severity, 'warning');
  assert.match(orphan.message, /stray/);
});

test('CLI hierarchy-check returns a JSON receipt and fails on errors', () => {
  const { root } = fixture();
  const ok = spawnSync(process.execPath, [cli, 'hierarchy-check', root, '--json'], { encoding: 'utf8' });
  assert.equal(ok.status, 0, ok.stderr);
  const receipt = JSON.parse(ok.stdout);
  assert.equal(receipt.command, 'hierarchy-check');
  assert.equal(receipt.diagrams.length, 2);

  const broken = fixture({ root: (spec) => { spec.components[0].link.focus = 'ghost'; } });
  const failed = spawnSync(process.execPath, [cli, 'hierarchy-check', broken.root], { encoding: 'utf8' });
  assert.equal(failed.status, 1);
  assert.match(failed.stdout, /hierarchy\/focus-missing/);

  const usage = spawnSync(process.execPath, [cli, 'hierarchy-check'], { encoding: 'utf8' });
  assert.equal(usage.status, 2);
});

test('--strict turns warnings into a failing exit code', () => {
  const { root } = withoutParent();
  assert.equal(spawnSync(process.execPath, [cli, 'hierarchy-check', root], { encoding: 'utf8' }).status, 0);
  assert.equal(spawnSync(process.execPath, [cli, 'hierarchy-check', root, '--strict'], { encoding: 'utf8' }).status, 1);
});

test('archify map renders the hierarchy as an Archify architecture diagram', () => {
  const { dir, root } = fixture({ root: (spec) => {
    spec.components[1].link = { href: 'planned/planned.html' };
    spec.meta.hierarchy.leaf_nodes = [];
  } });
  fs.rmSync(path.join(dir, 'map.html'));
  const out = path.join(dir, 'map.html');
  const run = spawnSync(process.execPath, [cli, 'map', root, out, '--json'], { encoding: 'utf8' });
  const receipt = JSON.parse(run.stdout);
  assert.equal(receipt.delivery.ok, true, JSON.stringify(receipt.delivery));
  assert.equal(receipt.delivery.validation.checksPassed, receipt.delivery.validation.checkCount);
  // The broken link is a consistency error, so the command fails while the map still renders.
  assert.equal(run.status, 1);
  assert.ok(receipt.diagnostics.some((d) => d.code === 'hierarchy/link-target-missing'));

  const spec = JSON.parse(fs.readFileSync(path.join(dir, 'map.architecture.json'), 'utf8'));
  assert.equal(spec.diagram_type, 'architecture');
  assert.equal(spec.meta.title, '全体図 — 図のマップ');
  assert.deepEqual(spec.meta.hierarchy.parent, { href: 'root.html', label: '全体図' });
  const byLabel = Object.fromEntries(spec.components.map((c) => [c.label, c]));
  assert.equal(byLabel['全体図'].link.href, 'root.html');
  assert.equal(byLabel['API の詳細'].link.href, 'child/child.html');
  assert.equal(byLabel['planned.html'].type, 'external');
  assert.equal(byLabel['planned.html'].sublabel, '未作成');
  const edges = spec.connections.map((c) => [c.from, c.to, c.variant || 'solid']);
  assert.deepEqual(edges.map(([from]) => from), [byLabel['全体図'].id, byLabel['全体図'].id]);
  assert.ok(edges.some(([, to, variant]) => to === byLabel['planned.html'].id && variant === 'dashed'));

  const html = fs.readFileSync(out, 'utf8');
  assert.match(html, /data-node-link-href="child\/child\.html"/);
  assert.match(html, /<title>全体図 — 図のマップ 図<\/title>/);
});

test('the map spec is generated output, not an orphan diagram', () => {
  const { dir, root } = fixture();
  fs.rmSync(path.join(dir, 'map.html'));
  const run = spawnSync(process.execPath, [cli, 'map', root, path.join(dir, 'map.html')], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr + run.stdout);
  const result = checkHierarchy(root, { scanDir: dir });
  assert.deepEqual(result.diagnostics, []);
});

test('a child page carries a thumbnail of its parent and goes stale when the parent moves', () => {
  const { root, child } = fixture();
  const payload = JSON.parse(fs.readFileSync(child.replace(/\.architecture\.json$/, '.html'), 'utf8')
    .match(/<script id="archify-hierarchy-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
  const api = payload.locator.nodes.find((node) => node.id === 'api');
  assert.equal(api.to, 'child.html');
  assert.equal(payload.locator.nodes.find((node) => node.id === 'db').to, undefined);

  const rootSpec = JSON.parse(fs.readFileSync(root, 'utf8'));
  rootSpec.components[0].pos = [40, 240];
  fs.writeFileSync(root, JSON.stringify(rootSpec, null, 2));
  render(root);
  assert.ok(codes(checkHierarchy(root)).includes('hierarchy/stale-html'));
  render(child);
  assert.deepEqual(checkHierarchy(root).diagnostics, []);
});

test('hierarchy-sync derives breadcrumbs and onward counts, and the check enforces them', () => {
  const { dir, root, child } = fixture();
  const childSpec = JSON.parse(fs.readFileSync(child, 'utf8'));
  assert.deepEqual(childSpec.meta.hierarchy.trail, [{ href: '../root.html', label: '全体図' }]);
  const rootSpec = JSON.parse(fs.readFileSync(root, 'utf8'));
  assert.equal(rootSpec.components[0].link.onward, 0);
  assert.equal(rootSpec.components[0].link.title, 'API の詳細');
  assert.equal(rootSpec.meta.hierarchy.trail, undefined);

  // A grandchild changes the child's onward count; the check catches the drift.
  const grand = path.join(dir, 'child', 'deeper', 'deeper.architecture.json');
  write(grand, architecture('さらに詳細', [{ id: 'leaf', label: 'Leaf' }], { parent: { href: '../child.html', label: 'API の詳細' } }));
  childSpec.components[0].link = { href: 'deeper/deeper.html' };
  fs.writeFileSync(child, JSON.stringify(childSpec, null, 2));
  const stale = checkHierarchy(root);
  assert.ok(codes(stale).includes('hierarchy/sync-stale'), codes(stale).join());

  const check = spawnSync(process.execPath, [cli, 'hierarchy-sync', root, '--check'], { encoding: 'utf8' });
  assert.equal(check.status, 1, check.stdout);
  const sync = spawnSync(process.execPath, [cli, 'hierarchy-sync', root, '--json'], { encoding: 'utf8' });
  assert.equal(sync.status, 0, sync.stderr);
  assert.ok(JSON.parse(sync.stdout).changed.length >= 2);
  const grandSpec = JSON.parse(fs.readFileSync(grand, 'utf8'));
  assert.deepEqual(grandSpec.meta.hierarchy.trail.map((crumb) => crumb.label), ['全体図', 'API の詳細']);
  assert.equal(JSON.parse(fs.readFileSync(root, 'utf8')).components[0].link.onward, 1);
  for (const spec of [root, child, grand]) render(spec);
  assert.deepEqual(checkHierarchy(root).diagnostics, []);
});

test('the map adds a concern level for <concern>/<diagram>/ directories and marks itself as a map', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-map-concern-'));
  const root = path.join(dir, 'root.architecture.json');
  const specs = [
    [path.join(dir, 'events', 'start', 'start.architecture.json'), '開始'],
    [path.join(dir, 'events', 'stop', 'stop.architecture.json'), '停止'],
    [path.join(dir, 'state', 'mode', 'mode.architecture.json'), 'モード'],
  ];
  write(root, architecture('全体図', specs.map(([file], index) => ({
    id: `n${index}`, label: `N${index}`, link: { href: path.relative(dir, file).replace(/\.architecture\.json$/, '.html') },
  })), { map: { href: 'map.html' } }));
  for (const [file, title] of specs) write(file, architecture(title, [{ id: 'x', label: 'X' }], { parent: { href: '../../root.html', label: '全体図' }, map: { href: '../../map.html' } }));
  syncHierarchy(root);
  for (const file of [root, ...specs.map(([file]) => file)]) render(file);

  const start = JSON.parse(fs.readFileSync(specs[0][0], 'utf8'));
  assert.deepEqual(start.meta.hierarchy.trail, [
    { href: '../../root.html', label: '全体図' },
    { href: '../../map.html', label: 'events', focus: 'c-events' },
  ]);
  // Siblings are the diagrams of the same concern, in the root's link order;
  // a concern with a single diagram has none.
  assert.deepEqual(start.meta.hierarchy.siblings, [
    { href: 'start.html', label: '開始' },
    { href: '../stop/stop.html', label: '停止' },
  ]);
  assert.equal(JSON.parse(fs.readFileSync(specs[2][0], 'utf8')).meta.hierarchy.siblings, undefined);

  const run = spawnSync(process.execPath, [cli, 'map', root, path.join(dir, 'map.html'), '--json'], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
  const map = JSON.parse(fs.readFileSync(path.join(dir, 'map.architecture.json'), 'utf8'));
  assert.equal(map.meta.hierarchy.role, 'map');
  const concerns = map.components.filter((c) => c.type === 'cloud').map((c) => [c.id, c.label, c.sublabel]);
  assert.deepEqual(concerns, [['c-events', 'events', '図 2'], ['c-state', 'state', '図 1']]);
  assert.deepEqual(map.boundaries.map((b) => b.label), ['L0 全体図', 'L1 関心ごと', 'L2 詳細図']);
  const events = map.connections.filter((edge) => edge.from === 'c-events').length;
  assert.equal(events, 2);
  assert.deepEqual(checkHierarchy(root, { scanDir: dir }).diagnostics, []);
});

test('a cross link between detail diagrams must follow a line in their parent', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-cross-link-'));
  const root = path.join(dir, 'root.architecture.json');
  const child = (name) => path.join(dir, name, `${name}.architecture.json`);
  // root: na ─▶ nb, and nc with no line from na.
  const rootSpec = architecture('全体図', ['a', 'b', 'c'].map((name) => ({ id: `n${name}`, label: name.toUpperCase(), link: { href: `${name}/${name}.html` } })));
  write(root, rootSpec);
  write(child('a'), architecture('A', [
    { id: 'to-b', label: 'B へ', link: { href: '../b/b.html' } },
    { id: 'to-c', label: 'C へ', link: { href: '../c/c.html' } },
  ], { parent: { href: '../root.html', label: '全体図' } }));
  for (const name of ['b', 'c']) write(child(name), architecture(name.toUpperCase(), [{ id: 'x', label: 'X' }], { parent: { href: '../root.html', label: '全体図' } }));
  syncHierarchy(root);
  for (const file of [root, child('a'), child('b'), child('c')]) render(file);

  const unbacked = checkHierarchy(root).diagnostics.filter((d) => d.code === 'hierarchy/cross-link-unbacked');
  assert.deepEqual(unbacked.map((d) => d.subject.target), ['c/c.architecture.json']);

  rootSpec.connections.push({ from: 'na', to: 'nc', fromSide: 'bottom', toSide: 'bottom', via: [[120, 200], [600, 200]] });
  write(root, rootSpec);
  syncHierarchy(root);
  for (const file of [root, child('a'), child('b'), child('c')]) render(file);
  assert.deepEqual(codes(checkHierarchy(root)).filter((code) => code === 'hierarchy/cross-link-unbacked'), []);
});

test('one destination split over several nodes is flagged until a boundary links it once', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-split-destination-'));
  const root = path.join(dir, 'root.architecture.json');
  const detail = path.join(dir, 'state', 'state.architecture.json');
  const rootSpec = architecture('全体図', [
    { id: 'flag', label: 'フラグ', link: { href: 'state/state.html' } },
    { id: 'badge', label: '表示', link: { href: 'state/state.html' } },
  ]);
  write(root, rootSpec);
  write(detail, architecture('状態', [{ id: 'x', label: 'X' }], { parent: { href: '../root.html', label: '全体図' } }));
  syncHierarchy(root);
  render(root);
  render(detail);
  assert.ok(codes(checkHierarchy(root)).includes('hierarchy/split-destination'));

  for (const component of rootSpec.components) delete component.link;
  rootSpec.boundaries = [{ kind: 'region', id: 'state', label: '状態', wraps: ['flag', 'badge'], link: { href: 'state/state.html' } }];
  write(root, rootSpec);
  syncHierarchy(root);
  render(root);
  render(detail);
  const result = checkHierarchy(root);
  assert.ok(!codes(result).includes('hierarchy/split-destination'), codes(result).join());
  assert.equal(JSON.parse(fs.readFileSync(root, 'utf8')).boundaries[0].link.title, '状態');
});

test('a cross link names the node it lands on, and the target lists where links come from', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-cross-focus-'));
  const root = path.join(dir, 'root.architecture.json');
  const child = (name) => path.join(dir, name, `${name}.architecture.json`);
  write(root, architecture('全体図', ['a', 'b'].map((name) => ({ id: `n${name}`, label: name.toUpperCase(), link: { href: `${name}/${name}.html` } }))));
  const a = architecture('A', [{ id: 'to-b', label: 'B へ', link: { href: '../b/b.html' } }], { parent: { href: '../root.html', label: '全体図' } });
  write(child('a'), a);
  write(child('b'), architecture('B', [{ id: 'x', label: 'X' }, { id: 'y', label: 'Y' }], { parent: { href: '../root.html', label: '全体図' } }));
  syncHierarchy(root);
  for (const file of [root, child('a'), child('b')]) render(file);
  const unfocused = checkHierarchy(root).diagnostics.filter((d) => d.code === 'hierarchy/cross-link-unfocused');
  assert.deepEqual(unfocused.map((d) => [d.subject.diagram, d.subject.node]), [['a/a.architecture.json', 'to-b']]);

  a.components[0].link.focus = 'y';
  write(child('a'), a);
  syncHierarchy(root);
  // Cross-linked pages embed each other's thumbnails, so both render twice.
  for (const file of [root, child('a'), child('b'), child('a'), child('b')]) render(file);
  assert.deepEqual(JSON.parse(fs.readFileSync(child('b'), 'utf8')).meta.hierarchy.incoming, [
    { href: '../a/a.html', label: 'A', node: 'to-b', node_label: 'B へ', focus: 'y' },
  ]);
  // Links down from the root are tree links: no incoming entry, no warning.
  assert.equal(JSON.parse(fs.readFileSync(child('a'), 'utf8')).meta.hierarchy.incoming, undefined);
  assert.deepEqual(checkHierarchy(root).diagnostics, []);
});

// The bundled example is the template for new hierarchies: kept synced, and
// one hierarchy-build delivers it in order and checks it clean.
test('the bundled hierarchy example is synced and builds clean in one command', () => {
  const example = path.join(skillRoot, 'examples/hierarchy');
  const sync = spawnSync(process.execPath, [cli, 'hierarchy-sync', path.join(example, 'shop.architecture.json'), '--check', '--json'], { encoding: 'utf8' });
  assert.equal(sync.status, 0, sync.stdout + sync.stderr);

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-build-'));
  fs.cpSync(example, dir, { recursive: true, filter: (source) => !/\.html$|\.map\.architecture\.json$/.test(source) });
  const run = spawnSync(process.execPath, [cli, 'hierarchy-build', path.join(dir, 'shop.architecture.json'), '--strict', '--no-preview-check', '--no-visual-check', '--json'], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
  const report = JSON.parse(run.stdout);
  const name = (file) => path.basename(file);
  // Parents first: the root, then its children in link order.
  assert.equal(name(report.delivered[0].html), 'shop.html');
  assert.equal(report.delivered.length, 4);
  assert.ok(report.delivered.every((entry) => entry.ok && entry.errors === 0 && entry.warnings === 0));
  // order-api embeds checkout's thumbnail (an incoming link) delivered after it.
  assert.deepEqual(report.redelivered.map((entry) => name(entry.html)), ['order-api.html']);
  assert.equal(report.map.ok, true);
  assert.deepEqual(report.check.summary, { errors: 0, warnings: 0 });
  assert.equal(report.preview.status, 'skipped');
  assert.ok(fs.existsSync(path.join(dir, 'shop.map.html')));
});

test('hierarchy-build fails when a linked diagram is missing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-build-fail-'));
  const root = path.join(dir, 'root.architecture.json');
  write(root, architecture('全体図', [{ id: 'a', label: 'A', link: { href: 'a/a.html' } }, { id: 'b', label: 'B' }]));
  const run = spawnSync(process.execPath, [cli, 'hierarchy-build', root, '--quality', 'standard', '--no-preview-check', '--no-visual-check', '--json'], { encoding: 'utf8' });
  assert.equal(run.status, 1, run.stdout + run.stderr);
  const report = JSON.parse(run.stdout);
  assert.equal(report.ok, false);
  assert.ok(report.check.diagnostics.some((d) => d.code === 'hierarchy/link-target-missing'));
});

// Composite halves are namespaced in the SVG (seq-/flow-/er-); links on them
// must read back as fresh, and their evidence needs --repo-root.
test('a composite diagram with a link builds clean with its repository evidence', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-composite-'));
  const root = path.join(dir, 'root.sequence-er.json');
  fs.copyFileSync(path.join(skillRoot, 'test/fixtures/hierarchy-sequence-er.json'), root);
  write(path.join(dir, 'sub', 'sub.architecture.json'), architecture('Sub', [{ id: 'x', label: 'X' }], { parent: { href: '../root.html', label: '担当者とタスク' } }));
  const run = spawnSync(process.execPath, [cli, 'hierarchy-build', root, '--quality', 'standard', '--repo-root', skillRoot, '--no-preview-check', '--no-visual-check', '--json'], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
  assert.deepEqual(JSON.parse(run.stdout).check.summary, { errors: 0, warnings: 0 });
  const geometry = readGeometry(path.join(dir, 'root.html'));
  const app = geometry.nodes.find((node) => node.id === 'seq-app');
  assert.equal(app.href, 'sub/sub.html');
  // The ER half is translated right of the sequence half.
  assert.ok(geometry.nodes.find((node) => node.id.startsWith('er-')).box[0] > app.box[0] + app.box[2]);
});

test('class and ER nodes are read at their translated positions', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-geometry-'));
  for (const [type, example] of [['class', 'domain-model.class.json'], ['er', 'ecommerce.er.json']]) {
    const html = path.join(dir, `${type}.html`);
    execFileSync(process.execPath, [cli, 'render', type, path.join(skillRoot, 'examples', example), html], { stdio: 'pipe' });
    const boxes = readGeometry(html).nodes.map((node) => node.box);
    assert.ok(boxes.length >= 3, type);
    assert.ok(boxes.every((box) => box[0] > 0 && box[1] > 0), `${type}: ${JSON.stringify(boxes)}`);
    assert.equal(new Set(boxes.map((box) => box.join(','))).size, boxes.length, type);
  }
});

test('long diagram titles are shortened where sync writes them', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-long-title-'));
  const root = path.join(dir, 'root.architecture.json');
  const child = (name) => path.join(dir, 'c', name, `${name}.architecture.json`);
  const long = '長い題名'.repeat(35);
  write(root, architecture(long, ['a', 'b'].map((name) => ({ id: `n${name}`, label: name.toUpperCase(), link: { href: `c/${name}/${name}.html` } }))));
  write(child('a'), architecture(long, [{ id: 'to-b', label: 'B へ', link: { href: '../b/b.html', focus: 'x' } }], { parent: { href: '../../root.html', label: '全体図' } }));
  write(child('b'), architecture('B', [{ id: 'x', label: 'X' }, { id: 'y', label: 'Y' }], { parent: { href: '../../root.html', label: '全体図' } }));
  const run = spawnSync(process.execPath, [cli, 'hierarchy-build', root, '--quality', 'standard', '--no-preview-check', '--no-visual-check', '--json'], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
  const b = JSON.parse(fs.readFileSync(child('b'), 'utf8')).meta.hierarchy;
  assert.ok(b.incoming[0].label.length <= 120 && b.incoming[0].label.endsWith('…'));
  assert.ok([...b.trail, ...b.siblings].every((crumb) => crumb.label.length <= 80));
  // Emoji are counted whole and never split into a lone surrogate.
  assert.equal(clipLabel('😀'.repeat(90)), `${'😀'.repeat(79)}…`);
});

test('a missing focus into a composite names the rendered id prefixes', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-composite-focus-'));
  const target = path.join(dir, 'c', 'c.sequence-er.json');
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const composite = JSON.parse(fs.readFileSync(path.join(skillRoot, 'test/fixtures/hierarchy-sequence-er.json'), 'utf8'));
  delete composite.sequence.participants[0].link;
  composite.meta.hierarchy = { parent: { href: '../root.html', label: '全体図' } };
  fs.writeFileSync(target, JSON.stringify(composite));
  const root = path.join(dir, 'root.architecture.json');
  write(root, architecture('全体図', [{ id: 'a', label: 'A', link: { href: 'c/c.html', focus: 'app' } }, { id: 'b', label: 'B' }]));
  execFileSync(process.execPath, [cli, 'render', 'sequence-er', target, path.join(dir, 'c', 'c.html'), '--repo-root', skillRoot], { stdio: 'pipe' });
  const focus = checkHierarchy(root).diagnostics.find((d) => d.code === 'hierarchy/focus-missing');
  assert.match(focus.message, /seq-<id> または er-<id>/);
});
