import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { validateSchema } from '../renderers/shared/validator.mjs';
import { lifecycleProblems } from '../renderers/lifecycle/model.mjs';
import { layoutLifecycle } from '../renderers/lifecycle/layout.mjs';
import { lifecycleLegendEntries, lifecycleElementColorType } from '../renderers/lifecycle/legend.mjs';
import { extractSvgs, parseXml } from './helpers/xml.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const load = name => JSON.parse(fs.readFileSync(path.join(root, 'examples', `${name}.lifecycle.json`), 'utf8'));
const order = () => load('order');
const invalid = (change, pattern) => {
  const doc = order(); change(doc);
  assert.match(lifecycleProblems(doc).join('\n'), pattern);
};

test('complete lifetime requires reachable ends and forbids continuing after an end', () => {
  invalid(doc => { doc.terminal = []; }, /終端を指定/);
  invalid(doc => { doc.terminal = ['paid']; }, /全体の終端/);
  invalid(doc => { doc.transitions = doc.transitions.filter(edge => edge.id !== 'delivery'); }, /終端.*到達できません/);
  invalid(doc => { doc.transitions = doc.transitions.filter(edge => edge.id !== 'dispatch'); doc.terminal = ['cancelled']; }, /paid.*終端へ到達/);
});

test('partial lifecycle can omit its end without inventing a final state', () => {
  const doc = order(); doc.subject.coverage = 'partial'; doc.subject.ending = '運用継続。終了は範囲外'; doc.terminal = [];
  assert.deepEqual(lifecycleProblems(doc), []);
});

test('events and activities cannot masquerade as state transitions', () => {
  invalid(doc => { doc.states[0].kind = 'event'; }, /両端は状態またはフェーズ/);
  invalid(doc => { doc.states[0].kind = 'phase'; }, /粒度を混在/);
  invalid(doc => { delete doc.transitions[0].event; delete doc.transitions[0].condition; }, /eventまたはcondition/);
});

test('associations cannot make a disconnected progression reachable', () => {
  invalid(doc => {
    doc.states.push({ id: 'notice', kind: 'event', label: '通知', lane: 'lifetime', row: 2, col: 0 });
    doc.transitions.push({ id: 'attach', kind: 'association', from: 'awaiting', to: 'notice' });
    doc.transitions[1].from = 'notice';
    doc.transitions = doc.transitions.filter(edge => edge.id !== 'payment');
  }, /paid.*到達できず/);
  invalid(doc => { doc.transitions[0].kind = 'association'; }, /関連.*event\/condition\/action/);
});

test('unknown and duplicate node, lane, relation and boundary references fail', () => {
  invalid(doc => { doc.initial = ['missing']; }, /開始.*存在しません/);
  invalid(doc => { doc.initial.push(doc.initial[0]); }, /開始.*重複/);
  invalid(doc => { doc.states[0].lane = 'missing'; }, /レーン.*存在しません/);
  invalid(doc => { doc.states.push(doc.states[0]); }, /要素IDが重複/);
  invalid(doc => { doc.transitions[1].id = doc.transitions[0].id; }, /関係IDが重複/);
});

test('a local end can continue outside its scope but not inside it', () => {
  const doc = order();
  doc.groups = [{ id: 'payment-scope', kind: 'scope', label: '決済', members: ['awaiting', 'paid'], note: '決済が完了しても注文は続く', initial: ['awaiting'], terminal: ['paid'] }];
  assert.deepEqual(lifecycleProblems(doc), []);
  doc.groups[0].terminal = ['awaiting'];
  assert.match(lifecycleProblems(doc).join('\n'), /囲み.*終端.*処理が続いて/);
});

test('group nesting requires explicit containment and an acyclic parent chain', () => {
  const doc = load('claude-hooks');
  doc.groups[0].members = ['prompt', 'stop'];
  assert.match(lifecycleProblems(doc).join('\n'), /親.*含めて/);
  const cyclic = load('claude-hooks'); cyclic.groups[0].parent = cyclic.groups[1].id;
  assert.match(lifecycleProblems(cyclic).join('\n'), /親子関係が循環/);
});

test('a repeat needs its condition and an actual cycle', () => {
  const doc = load('react-effect');
  doc.transitions = doc.transitions.filter(edge => edge.id !== 'resync');
  assert.match(lifecycleProblems(doc).join('\n'), /戻り関係がありません/);
  const noCondition = load('react-effect'); delete noCondition.groups[0].condition;
  assert.match(lifecycleProblems(noCondition).join('\n'), /conditionが必要/);
});

test('a self transition is a legitimate retry, not a duplicate endpoint reference', () => {
  const doc = order();
  doc.transitions.push({ id: 'retry', kind: 'transition', from: 'awaiting', to: 'awaiting', event: '入金失敗', condition: '再試行可能', labelAt: [390, 258] });
  doc.groups = [{ id: 'retry-scope', kind: 'repeat', label: '再試行', members: ['awaiting'], note: '支払待ちを継続する', condition: '再試行可能' }];
  assert.deepEqual(lifecycleProblems(doc), []);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lifecycle-retry-'));
  const input = path.join(tmp, 'input.json');
  fs.writeFileSync(input, JSON.stringify(doc));
  const result = spawnSync(process.execPath, [path.join(root, 'bin/archify.mjs'), 'validate', 'lifecycle', input, '--json'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test('parallel branch representatives need a completion condition and no serial link', () => {
  const doc = order();
  doc.groups = [{ id: 'parallel', kind: 'parallel', label: '独立枝', members: ['cancelled', 'delivered'], note: '構造検証用', completion: 'いずれか完了' }];
  assert.deepEqual(lifecycleProblems(doc), []);
  delete doc.groups[0].completion;
  assert.match(lifecycleProblems(doc).join('\n'), /completion/);
  doc.groups[0].members = ['paid', 'shipping'];
  assert.match(lifecycleProblems(doc).join('\n'), /直列化/);
});

test('layout order and status colors do not change domain validity', () => {
  const doc = order();
  doc.lanes[0].id = 'not-a-reserved-word';
  doc.states.forEach((node, index) => { node.lane = doc.lanes[0].id; node.col = 7 - index; node.type = 'failure'; });
  doc.states.reverse(); doc.transitions.reverse();
  assert.deepEqual(lifecycleProblems(doc), []);
  assert.equal(layoutLifecycle(doc).states.size, 5);
});

test('v1 and v2 contracts stay separate', () => {
  const legacy = load('agent-run');
  validateSchema('lifecycle', legacy);
  const doc = order(); delete doc.subject;
  assert.throws(() => validateSchema('lifecycle', doc));
  const mixed = order(); mixed.schema_version = 1;
  assert.throws(() => validateSchema('lifecycle', mixed));
});

test('v2 legends explain semantics without inventing a neutral state or a color filter', () => {
  const react = lifecycleLegendEntries(load('react-effect'));
  assert.deepEqual(react.map(entry => entry.kind), ['event', 'activity', 'initial', 'terminal', 'sequence', 'repeat']);
  assert.ok(react.every(entry => !entry.interactive));
  const hooks = lifecycleLegendEntries(load('claude-hooks'));
  assert.ok(hooks.some(entry => entry.kind === 'association'));
  const colored = lifecycleLegendEntries(order());
  assert.ok(colored.some(entry => entry.kind === 'state'));
  assert.match(colored.find(entry => entry.kind === 'failure').label, /配色.*終端とは限らない/);
  const doc = load('react-effect');
  doc.meta.legend = { entries: { event: { label: '発火点' }, activity: { visible: false } } };
  validateSchema('lifecycle', doc);
  const customized = lifecycleLegendEntries(doc);
  assert.equal(customized.find(entry => entry.kind === 'event').label, '発火点');
  assert.ok(!customized.some(entry => entry.kind === 'activity'));
  doc.meta.legend.mode = 'hidden';
  assert.deepEqual(lifecycleLegendEntries(doc), []);
});

test('element kinds have theme colors while explicit status palettes take priority', () => {
  assert.deepEqual(['state', 'phase', 'event', 'activity'].map(kind => lifecycleElementColorType({ kind })), ['success', 'waiting', 'start', 'active']);
  assert.equal(lifecycleElementColorType({ kind: 'event', type: 'failure' }), 'failure');
  const entries = lifecycleLegendEntries(load('claude-hooks'));
  assert.equal(entries.find(entry => entry.kind === 'event').colorType, 'start');
  assert.equal(entries.find(entry => entry.kind === 'activity').colorType, 'active');
  assert.equal(lifecycleLegendEntries(order()).find(entry => entry.kind === 'state').colorType, undefined);
});

test('all-kind legends expand automatic height instead of silently disappearing', () => {
  const doc = order(); delete doc.meta.views;
  doc.states = doc.states.slice(0, 2);
  doc.transitions = doc.transitions.slice(0, 1);
  doc.terminal = ['paid'];
  const auto = layoutLifecycle(doc);
  doc.meta.legend = { mode: 'all' };
  const all = layoutLifecycle(doc);
  assert.ok(all.viewBox[1] > auto.viewBox[1]);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lifecycle-legend-'));
  const input = path.join(tmp, 'input.json'), output = path.join(tmp, 'diagram.html');
  fs.writeFileSync(input, JSON.stringify(doc));
  const rendered = spawnSync(process.execPath, [path.join(root, 'bin/archify.mjs'), 'deliver', 'lifecycle', input, output, '--json'], { encoding: 'utf8' });
  assert.equal(rendered.status, 0, rendered.stdout + rendered.stderr);
  const svg = extractSvgs(fs.readFileSync(output, 'utf8')).direct[0];
  assert.equal((svg.match(/data-legend-semantic-kind=/g) || []).length, lifecycleLegendEntries(doc).length);
  doc.meta.viewBox = [760, 300];
  fs.writeFileSync(input, JSON.stringify(doc));
  const cramped = spawnSync(process.execPath, [path.join(root, 'bin/archify.mjs'), 'validate', 'lifecycle', input, '--json'], { encoding: 'utf8' });
  assert.equal(cramped.status, 1);
});

for (const name of ['order', 'react-effect', 'claude-hooks']) test(`${name}: the domain and output validate with no implicit rail`, () => {
  const doc = load(name); validateSchema('lifecycle', doc); assert.deepEqual(lifecycleProblems(doc), []);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lifecycle-v2-'));
  const output = path.join(tmp, 'diagram.html');
  const rendered = spawnSync(process.execPath, [path.join(root, 'renderers/lifecycle/render-lifecycle.mjs'), path.join(root, 'examples', `${name}.lifecycle.json`), output], { encoding: 'utf8' });
  assert.equal(rendered.status, 0, rendered.stderr);
  const html = fs.readFileSync(output, 'utf8');
  const svg = extractSvgs(html).direct[0]; parseXml(svg);
  assert.equal((svg.match(/data-relation-kind=/g) || []).length, doc.transitions.length);
  assert.match(svg, /data-element-kind=/);
  assert.match(svg, /data-legend-semantic-kind="initial"/);
  assert.match(svg, /data-legend-semantic-kind="terminal"/);
  assert.doesNotMatch(svg, /data-legend-kind=/);
  if (name !== 'order') {
    for (const kind of ['event', 'activity', 'sequence', 'repeat']) assert.match(svg, new RegExp(`data-legend-semantic-kind="${kind}"`));
    assert.doesNotMatch(svg, /data-legend-semantic-kind="neutral"|中立状態/);
    assert.match(svg, /data-element-kind="event"[^]*?class="c-frontend"/);
    assert.match(svg, /data-element-kind="activity"[^]*?class="c-backend"/);
    assert.match(svg, /data-legend-semantic-kind="event"[^]*?class="c-frontend"/);
    assert.match(svg, /data-legend-semantic-kind="activity"[^]*?class="c-backend"/);
  }
  assert.doesNotMatch(svg, /d="M 154 /);
  const checked = spawnSync(process.execPath, [path.join(root, 'scripts/check-render-output.mjs'), output], { encoding: 'utf8' });
  assert.equal(checked.status, 0, checked.stdout + checked.stderr);
  if (name === 'order') assert.match(svg, /入金.*金額一致.*領収書発行/);
  if (name === 'claude-hooks') {
    assert.match(svg, /data-group-kind="repeat"/);
    const association = svg.match(/<path[^>]*data-relation-kind="association"[^>]*>/)?.[0];
    assert.ok(association); assert.doesNotMatch(association, /marker-end|data-edge-from/);
    assert.match(association, /data-association-from=/);
    assert.match(svg, /data-composition-frame-kind="repeat"/);
  }
});

test('semantic failure is returned by the CLI before writing any artifact', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lifecycle-invalid-'));
  const input = path.join(tmp, 'invalid.json'), output = path.join(tmp, 'output.html');
  const doc = order(); doc.terminal = ['paid']; fs.writeFileSync(input, JSON.stringify(doc));
  const result = spawnSync(process.execPath, [path.join(root, 'bin/archify.mjs'), 'render', 'lifecycle', input, output, '--json'], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stdout + result.stderr, /lifecycle\/model/);
  assert.equal(fs.existsSync(output), false);
});
