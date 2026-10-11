import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { textUnits } from './utils.mjs';
import { checkHierarchy, clipLabel, concernId, concernKey, hierarchyTree, treeParents } from './hierarchy-graph.mjs';

// The map is itself an Archify architecture diagram with
// `meta.hierarchy.role: "map"`. Its flat form is a left-to-right tree whose
// columns are hierarchy levels (L0 root, L1 concerns, L2 diagrams, ...); the
// viewer lifts the same nodes and edges into a stacked 3D layer view. One
// spec therefore drives validation, export and both presentations.

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const cli = path.join(skillRoot, 'bin/archify.mjs');

// Component kinds carry the colour; the legend is relabelled so a colour
// reads as a diagram type (or a concern) instead of an infrastructure role.
const KIND_BY_TYPE = {
  architecture: 'backend',
  workflow: 'frontend',
  'workflow-er': 'frontend',
  dataflow: 'messagebus',
  lifecycle: 'security',
  sequence: 'database',
  'sequence-er': 'database',
  class: 'database',
  er: 'database',
};
const LEGEND = {
  cloud: '関心ごと',
  backend: 'architecture',
  frontend: 'workflow',
  messagebus: 'dataflow',
  security: 'lifecycle',
  database: 'sequence / class / er',
  external: '未作成（リンク切れ）',
};

const NODE_H = 56;
const MIN_W = 150;
const MAX_W = 400;
const COL_GAP = 120;
const ROW_GAP = 16;
const GROUP_GAP = 30;
const ORIGIN = 60;

function nodeWidth(label, sublabel) {
  const need = Math.max(textUnits(label) * 12 * 0.62, textUnits(sublabel) * 9 * 0.62) + 48;
  return Math.min(MAX_W, Math.max(MIN_W, Math.ceil(need / 10) * 10));
}

function slug(value, used) {
  const base = `d-${String(value).replace(/\.html$/, '').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '')}`.slice(0, 60) || 'd';
  let id = base;
  for (let i = 2; used.has(id); i += 1) id = `${base}-${i}`;
  used.add(id);
  return id;
}

function levelName(depth, hasConcerns) {
  if (depth === 0) return 'L0 全体図';
  if (depth === 1 && hasConcerns) return 'L1 関心ごと';
  return `L${depth} 詳細図`;
}

export function buildMapSpec(result, mapPath) {
  const tree = hierarchyTree(result, mapPath);
  const mapDir = path.dirname(path.resolve(mapPath));
  const toMap = (file) => path.relative(mapDir, file).split(path.sep).join('/');
  const onwardByHref = new Map(result.diagrams.map((diagram) => {
    const targets = new Set(result.edges.filter((edge) => edge.from === diagram.htmlPath && edge.to !== diagram.htmlPath).map((edge) => edge.to));
    return [toMap(diagram.htmlPath), targets.size];
  }));
  const used = new Set();

  // Map tree: diagrams, plus a concern node between the root and the
  // diagrams of each `<concern>/<diagram>/` directory, plus missing targets.
  function diagramNode(item) {
    const missing = item.links.filter((link) => !link.resolved)
      .filter((link, index, all) => all.findIndex((other) => other.href === link.href) === index)
      .map((link) => ({
        kind: 'missing',
        id: slug(`missing-${link.href}`, used),
        label: link.href.split('#')[0].split('/').pop(),
        sublabel: '未作成',
        type: 'external',
        children: [],
      }));
    return {
      kind: 'diagram',
      id: slug(item.href, used),
      label: item.title,
      sublabel: `${item.type} · ノード ${item.nodeCount}`,
      type: KIND_BY_TYPE[item.type] || 'backend',
      href: item.href,
      item,
      missing,
      children: [],
    };
  }
  const root = diagramNode(tree);
  const concerns = new Map();
  for (const child of tree.children) {
    const key = concernKey(child.href);
    const node = diagramNode(child);
    if (!key) {
      root.children.push(node);
      continue;
    }
    if (!concerns.has(key)) {
      const concern = { kind: 'concern', id: concernId(key), label: key.split('/').pop(), type: 'cloud', key, children: [] };
      concerns.set(key, concern);
      root.children.push(concern);
    }
    concerns.get(key).children.push(node);
  }
  root.children.push(...root.missing);
  (function expand(node) {
    if (node.kind === 'diagram' && node !== root) {
      node.children.push(...node.item.children.map(diagramNode), ...node.missing);
    }
    node.children.forEach(expand);
  })(root);
  for (const concern of concerns.values()) concern.sublabel = `図 ${concern.children.length}`;
  const hasConcerns = concerns.size > 0;

  // Column per depth, sized to its widest node.
  const columnWidth = [];
  (function size(node, depth) {
    node.depth = depth;
    columnWidth[depth] = Math.max(columnWidth[depth] || 0, nodeWidth(node.label, node.sublabel || ''));
    node.children.forEach((child) => size(child, depth + 1));
  })(root, 0);
  const columnX = [];
  columnWidth.forEach((width, depth) => {
    columnX[depth] = depth === 0 ? ORIGIN : columnX[depth - 1] + columnWidth[depth - 1] + COL_GAP;
  });

  // Tidy tree: leaves stack top to bottom; below the root every parent spans
  // its children so parent-to-child edges are straight.
  function measure(node) {
    if (!node.children.length) {
      node.span = NODE_H;
      return node.span;
    }
    const gap = node === root ? GROUP_GAP : ROW_GAP;
    node.span = node.children.reduce((sum, child) => sum + measure(child), 0) + (node.children.length - 1) * gap;
    return node.span;
  }
  measure(root);
  const components = [];
  const connections = [];
  const levelIds = [];
  function place(node, top) {
    const height = node === root || !node.children.length ? NODE_H : node.span;
    node.y = Math.round(top + (node.span - height) / 2);
    let cursor = top;
    const gap = node === root ? GROUP_GAP : ROW_GAP;
    for (const child of node.children) {
      place(child, cursor);
      cursor += child.span + gap;
      connections.push({
        id: `e-${child.id}`,
        from: node.id,
        to: child.id,
        ...(node === root ? {} : { fromSide: 'right', toSide: 'left' }),
        ...(child.kind === 'missing' ? { variant: 'dashed' } : {}),
      });
    }
    (levelIds[node.depth] ||= []).push(node.id);
    components.push({
      id: node.id,
      type: node.type,
      label: node.label,
      sublabel: node.sublabel,
      pos: [columnX[node.depth], node.y],
      size: [columnWidth[node.depth], height],
      ...(node.href ? { link: { href: node.href, label: clipLabel(node.label), onward: onwardByHref.get(node.href) ?? 0 } } : {}),
    });
  }
  place(root, ORIGIN + 30);

  const boundaries = levelIds.map((ids, depth) => ({ kind: 'region', label: levelName(depth, hasConcerns), wraps: ids }));
  const views = [...concerns.values()].slice(0, 5).map((concern) => ({
    id: `v-${concern.id}`.slice(0, 60),
    label: concern.label,
    focus: [root.id, concern.id, ...concern.children.map((child) => child.id)],
    note: `${concern.key}/ 配下の図`,
  }));

  // Cross links: distinct diagram pairs that are not a parent-to-child edge.
  const parentOf = treeParents(result);
  const crossPairs = new Set(result.edges
    .filter((edge) => edge.to !== edge.from && parentOf.get(edge.to) !== edge.from)
    .map((edge) => `${edge.from}\n${edge.to}`));
  // At most one short line for the issues keeps the card (and the page) from
  // growing; the full messages are in the hierarchy-check output.
  const first = result.diagnostics[0];
  const issues = first ? [clipLabel(
    `${first.severity === 'error' ? 'エラー' : '警告'}: ${first.code.replace(/^hierarchy\//, '')}${result.diagnostics.length > 1 ? ` ほか ${result.diagnostics.length - 1} 件` : ''}`, 40)] : [];
  return {
    schema_version: 1,
    diagram_type: 'architecture',
    meta: {
      title: `${tree.title} — 図のマップ`,
      locale: 'ja',
      quality_profile: 'showcase',
      legend: { entries: Object.fromEntries(Object.entries(LEGEND).map(([kind, label]) => [kind, { label }])) },
      hierarchy: { role: 'map', parent: { href: tree.href, label: clipLabel(tree.title) } },
      ...(views.length ? { views } : {}),
    },
    components,
    boundaries,
    connections,
    cards: [
      {
        dot: result.summary.errors ? 'rose' : 'emerald',
        title: '整合性チェック',
        items: [`図 ${result.diagrams.length} / エラー ${result.summary.errors} / 警告 ${result.summary.warnings}`, ...issues],
      },
      {
        dot: 'cyan',
        title: '階層',
        items: [`L0〜L${columnWidth.length - 1} の ${columnWidth.length} 段 / 関心ごと ${concerns.size}`, `図をまたぐ横断リンク ${crossPairs.size} 組（線は親子のみ）`],
      },
      {
        dot: 'violet',
        title: '使い方',
        items: ['左上で立体／平面を切り替え', 'ダブルクリックで図を開く'],
      },
    ],
  };
}

// Builds the map from the same walk the consistency check uses, so the map
// and `hierarchy-check` can never disagree about what is linked. The spec is
// kept next to the HTML (`<name>.architecture.json`) so the map stays
// reviewable and reproducible.
export function buildHierarchyMap(rootSpecPath, outPath, { scanDir = null } = {}) {
  const result = checkHierarchy(rootSpecPath, { scanDir, pendingMaps: [outPath] });
  if (!result.diagrams.length) return { result, written: false, delivery: null };
  const spec = buildMapSpec(result, outPath);
  const resolvedOut = path.resolve(outPath);
  const specPath = path.join(path.dirname(resolvedOut), `${path.basename(resolvedOut, '.html')}.architecture.json`);
  fs.mkdirSync(path.dirname(specPath), { recursive: true });
  fs.writeFileSync(specPath, `${JSON.stringify(spec, null, 2)}\n`);
  const run = spawnSync(process.execPath, [cli, 'deliver', 'architecture', specPath, resolvedOut, '--quality', 'showcase', '--json'], { encoding: 'utf8' });
  let delivery = null;
  try {
    delivery = JSON.parse(run.stdout);
  } catch (_) {
    delivery = { ok: false, error: (run.stderr || run.stdout || '').trim() };
  }
  return { result, written: run.status === 0, delivery, specPath };
}
