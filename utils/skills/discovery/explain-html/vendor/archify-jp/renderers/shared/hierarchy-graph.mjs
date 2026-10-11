import fs from 'node:fs';
import path from 'node:path';
import { hierarchyGroups, hierarchyNodeEntries, hierarchyViewerPayload } from './hierarchy.mjs';
import { locatorFor, peersFor } from './hierarchy-locator.mjs';

// Cross-file hierarchy facts. A single render only sees one spec, so link
// targets, focus/view anchors, parent back-references and HTML freshness are
// checked here by walking the link graph from the root diagram.

const DIAGRAM_TYPES = new Set(['architecture', 'workflow', 'sequence', 'dataflow', 'lifecycle', 'class', 'er', 'sequence-er', 'workflow-er']);
const IGNORED_DIRS = new Set(['node_modules', '.git']);

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (_) {
    return null;
  }
}

function isDiagramSpec(value) {
  return value && typeof value === 'object' && DIAGRAM_TYPES.has(value.diagram_type) && value.meta && typeof value.meta === 'object';
}

function isSpecCandidate(name) {
  return name.endsWith('.json') && !name.endsWith('.visual-check.json');
}

export function htmlPathForSpec(specPath, spec) {
  const dir = path.dirname(specPath);
  if (typeof spec?.meta?.output === 'string' && spec.meta.output.trim()) {
    return path.resolve(dir, spec.meta.output);
  }
  const base = path.basename(specPath, '.json');
  const typeSuffix = `.${spec?.diagram_type}`;
  return path.join(dir, `${base.endsWith(typeSuffix) ? base.slice(0, -typeSuffix.length) : base}.html`);
}

// Convention: the spec sits next to its HTML and either names it through
// meta.output or shares its basename (`name.html` <- `name.<type>.json`).
export function findSpecForHtml(htmlPath) {
  const dir = path.dirname(htmlPath);
  let entries;
  try {
    entries = fs.readdirSync(dir);
  } catch (_) {
    return { specPath: null, candidates: [] };
  }
  const candidates = entries.filter(isSpecCandidate)
    .map((name) => path.join(dir, name))
    .filter((file) => {
      const spec = readJson(file);
      return isDiagramSpec(spec) && path.resolve(htmlPathForSpec(file, spec)) === path.resolve(htmlPath);
    });
  return { specPath: candidates.length === 1 ? candidates[0] : null, candidates };
}

function unescapeHtml(value) {
  return String(value)
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

// Reads the facts the viewer will act on: focusable node ids, the link data
// attributes and the parent/map payload.
export function readRenderedHierarchy(htmlPath) {
  let html;
  try {
    html = fs.readFileSync(htmlPath, 'utf8');
  } catch (_) {
    return null;
  }
  const nodeIds = new Set();
  const links = new Map();
  for (const match of html.matchAll(/<g\b[^>]*\sdata-node-id="([A-Za-z][^"]*)"[^>]*>/g)) {
    const tag = match[0];
    const id = unescapeHtml(match[1]);
    nodeIds.add(id);
    const attr = (name) => {
      const found = tag.match(new RegExp(`\\s${name}="([^"]*)"`));
      return found ? unescapeHtml(found[1]) : undefined;
    };
    const href = attr('data-node-link-href');
    if (href !== undefined) {
      const onward = attr('data-node-link-onward');
      links.set(id, { href, focus: attr('data-node-link-focus'), view: attr('data-node-link-view'), label: attr('data-node-link-label'), onward: onward === undefined ? undefined : Number(onward), title: attr('data-node-link-title') });
    }
  }
  // Linked boundaries carry the same link attributes on their frame.
  for (const match of html.matchAll(/<rect\b[^>]*\sdata-boundary-id="([^"]+)"[^>]*>/g)) {
    const tag = match[0];
    const attr = (name) => {
      const found = tag.match(new RegExp(`\\s${name}="([^"]*)"`));
      return found ? unescapeHtml(found[1]) : undefined;
    };
    const href = attr('data-node-link-href');
    if (href === undefined) continue;
    const onward = attr('data-node-link-onward');
    links.set(unescapeHtml(match[1]), { href, focus: attr('data-node-link-focus'), view: attr('data-node-link-view'), label: attr('data-node-link-label'), onward: onward === undefined ? undefined : Number(onward), title: attr('data-node-link-title') });
  }
  // Drawn relationships, for checking that cross links are backed by a line.
  const edgePairs = [];
  for (const match of html.matchAll(/\sdata-edge-from="([^"]*)"\s+data-edge-to="([^"]*)"/g)) {
    edgePairs.push([unescapeHtml(match[1]), unescapeHtml(match[2])]);
  }
  const viewIds = new Set();
  const guided = html.match(/<script id="archify-guided-views-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (guided) {
    try {
      for (const view of JSON.parse(guided[1])) if (view?.id) viewIds.add(view.id);
    } catch (_) { /* malformed payload reads as no views */ }
  }
  let navigation = null;
  const data = html.match(/<script id="archify-hierarchy-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (data) {
    try {
      navigation = JSON.parse(data[1]);
    } catch (_) {
      navigation = null;
    }
  }
  return { nodeIds, links, viewIds, navigation, edges: edgePairs };
}

function diagramRecord(specPath) {
  const spec = readJson(specPath);
  if (!isDiagramSpec(spec)) return null;
  const htmlPath = htmlPathForSpec(specPath, spec);
  // `id` is the id in the rendered SVG (composite halves are namespaced),
  // which is what links, focus anchors and the viewer use; `specId` is the
  // id as authored, which leaf_nodes refer to.
  const nodes = [
    ...hierarchyNodeEntries(spec.diagram_type, spec).map(({ node, renderedId }) => ({
      id: renderedId,
      specId: node.id,
      label: node.label ?? node.name ?? node.id,
      link: node.link || null,
    })),
    ...hierarchyGroups(spec.diagram_type, spec).map((group) => ({
      id: group.id,
      specId: group.id,
      label: group.label ?? group.id,
      link: group.link,
      group: true,
      members: group.members,
    })),
  ];
  // Boundaries with an id can be relation endpoints; they stand for their members.
  const groupMembers = {};
  if (spec.diagram_type === 'architecture') {
    for (const boundary of spec.boundaries || []) {
      if (boundary?.id) groupMembers[boundary.id] = [...(boundary.wraps || [])];
    }
  }
  return {
    groupMembers,
    specPath: path.resolve(specPath),
    htmlPath: path.resolve(htmlPath),
    type: spec.diagram_type,
    title: spec.meta.title,
    meta: spec.meta,
    hierarchy: spec.meta.hierarchy || null,
    views: (spec.meta.views || []).map((view) => view.id),
    nodes,
    rendered: readRenderedHierarchy(htmlPath),
  };
}

function sameLink(a, b) {
  const norm = (link) => JSON.stringify([link?.href ?? null, link?.focus ?? null, link?.view ?? null, link?.label ?? null, link?.onward ?? null, link?.title ?? null]);
  return norm(a) === norm(b);
}

function listSpecs(dir) {
  const found = [];
  (function walk(current) {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch (_) {
      return;
    }
    for (const entry of entries) {
      if (entry.name.startsWith('.') || IGNORED_DIRS.has(entry.name)) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (isSpecCandidate(entry.name) && isDiagramSpec(readJson(full))) found.push(path.resolve(full));
    }
  })(dir);
  return found;
}

/**
 * Walks the hierarchy from rootSpecPath and returns every diagram plus
 * diagnostics. Options:
 *   scanDir     — also report specs under this directory that no link reaches
 *   pendingMaps — map files about to be generated (not reported as missing)
 */
export function checkHierarchy(rootSpecPath, { scanDir = null, pendingMaps = [] } = {}) {
  const diagnostics = [];
  const rootDir = path.dirname(path.resolve(rootSpecPath));
  const rel = (file) => path.relative(rootDir, file).split(path.sep).join('/') || '.';
  const report = (severity, code, message, subject = {}) => diagnostics.push({ code, severity, message, subject });
  const pending = new Set(pendingMaps.map((file) => path.resolve(file)));

  const root = diagramRecord(rootSpecPath);
  if (!root) {
    report('error', 'hierarchy/root-invalid', `ルート仕様 ${rootSpecPath} を Archify の図として読み込めません`);
    return { ok: false, rootDir, diagrams: [], edges: [], diagnostics, summary: summarize(diagnostics) };
  }

  const diagrams = new Map([[root.htmlPath, root]]);
  const edges = [];
  const queue = [root];
  while (queue.length) {
    const diagram = queue.shift();
    for (const node of diagram.nodes) {
      if (!node.link) continue;
      const target = path.resolve(path.dirname(diagram.htmlPath), node.link.href);
      const subject = { diagram: rel(diagram.specPath), node: node.id, href: node.link.href };
      if (target === diagram.htmlPath) {
        report('warning', 'hierarchy/self-link', `${rel(diagram.specPath)} のノード ${node.id} が自分自身の図へリンクしています`, subject);
      }
      edges.push({ from: diagram.htmlPath, to: target, node: node.id, label: node.label, link: node.link });
      if (diagrams.has(target)) continue;
      const { specPath, candidates } = findSpecForHtml(target);
      if (!specPath) {
        const exists = fs.existsSync(target);
        if (candidates.length > 1) {
          report('error', 'hierarchy/link-target-ambiguous', `${node.link.href} に対応する仕様JSONが複数あります: ${candidates.map(rel).join(', ')}`, subject);
        } else {
          report('error', exists ? 'hierarchy/link-target-spec-missing' : 'hierarchy/link-target-missing',
            exists
              ? `${rel(diagram.specPath)} のノード ${node.id} の遷移先 ${node.link.href} に対応する仕様JSONがありません`
              : `${rel(diagram.specPath)} のノード ${node.id} の遷移先 ${node.link.href} が存在しません。詳細図を作成してください`,
            subject);
        }
        continue;
      }
      const record = diagramRecord(specPath);
      if (!record) continue;
      diagrams.set(record.htmlPath, record);
      queue.push(record);
    }
  }

  const incoming = new Map();
  for (const edge of edges) {
    if (!incoming.has(edge.to)) incoming.set(edge.to, []);
    incoming.get(edge.to).push(edge);
  }

  const mapTargets = new Set();
  for (const diagram of diagrams.values()) {
    const where = rel(diagram.specPath);
    const ids = new Set(diagram.nodes.map((node) => node.specId));
    const hierarchy = diagram.hierarchy || {};
    const leafIds = new Set((hierarchy.leaf_nodes || []).map((leaf) => leaf.id));

    for (const leaf of hierarchy.leaf_nodes || []) {
      if (!ids.has(leaf.id)) report('error', 'hierarchy/leaf-unknown', `${where} の leaf_nodes に存在しないノード ${leaf.id} があります`, { diagram: where, node: leaf.id });
    }
    if (hierarchy.require_links === true) {
      const grouped = new Set(diagram.nodes.filter((node) => node.group).flatMap((node) => node.members));
      for (const node of diagram.nodes) {
        if (!node.link && !leafIds.has(node.specId) && !grouped.has(node.specId)) {
          report('error', 'hierarchy/missing-link', `${where} のノード ${node.id}（${node.label}）に遷移先がありません。詳細図を作って link を追加するか、理由付きで leaf_nodes に登録してください`, { diagram: where, node: node.id });
        }
      }
    }

    // Link anchors must exist in the target as rendered, because that is what
    // the viewer resolves after navigation.
    for (const node of diagram.nodes) {
      if (!node.link) continue;
      const target = diagrams.get(path.resolve(path.dirname(diagram.htmlPath), node.link.href));
      if (!target) continue;
      const subject = { diagram: where, node: node.id, href: node.link.href };
      const targetIds = target.rendered ? target.rendered.nodeIds : new Set(target.nodes.map((n) => n.id));
      if (node.link.focus && !targetIds.has(node.link.focus)) {
        const composite = target.type === 'sequence-er' || target.type === 'workflow-er';
        report('error', 'hierarchy/focus-missing', `${where} のノード ${node.id} が指す focus ${node.link.focus} は ${rel(target.specPath)} に存在しません${composite ? `。合成図では出力の id に接頭辞が付きます（${target.type === 'sequence-er' ? 'seq-' : 'flow-'}<id> または er-<id>）` : ''}`, subject);
      }
      const targetViews = target.rendered && target.rendered.viewIds.size ? target.rendered.viewIds : new Set(target.views);
      if (node.link.view && !targetViews.has(node.link.view)) {
        report('error', 'hierarchy/view-missing', `${where} のノード ${node.id} が指す view ${node.link.view} は ${rel(target.specPath)} に存在しません`, subject);
      }
    }

    if (diagram !== root) {
      const parents = incoming.get(diagram.htmlPath) || [];
      if (!hierarchy.parent) {
        report('warning', 'hierarchy/parent-missing', `${where} に meta.hierarchy.parent がありません。上位図へ戻るリンクが表示されません`, { diagram: where });
      } else {
        const declared = path.resolve(path.dirname(diagram.htmlPath), hierarchy.parent.href);
        if (!parents.some((edge) => edge.from === declared)) {
          report('error', 'hierarchy/parent-mismatch', `${where} の親 ${hierarchy.parent.href} は、この図へリンクしていません`, { diagram: where, href: hierarchy.parent.href });
        }
      }
    }

    if (hierarchy.map) {
      const mapPath = path.resolve(path.dirname(diagram.htmlPath), hierarchy.map.href);
      mapTargets.add(mapPath);
      if (!fs.existsSync(mapPath) && !pending.has(mapPath)) {
        report('error', 'hierarchy/map-missing', `${where} のマップ ${hierarchy.map.href} が存在しません。archify map で生成してください`, { diagram: where, href: hierarchy.map.href });
      }
    }

    if (!diagram.rendered) {
      report('error', 'hierarchy/html-missing', `${where} の HTML ${rel(diagram.htmlPath)} がありません。deliver で生成してください`, { diagram: where });
      continue;
    }
    // The HTML must carry exactly the spec's links, or navigation silently
    // drifts from the reviewed source.
    const staleNodes = diagram.nodes.filter((node) => !sameLink(node.link, diagram.rendered.links.get(node.id)));
    // The parent thumbnail follows the parent's rendered geometry.
    const payload = hierarchyViewerPayload(diagram.meta);
    const locator = payload ? locatorFor(diagram.meta, diagram.htmlPath) : null;
    const peers = payload ? peersFor(diagram.meta, diagram.htmlPath, diagram.nodes.filter((node) => node.link).map((node) => node.link.href)) : null;
    const expectedNavigation = JSON.stringify(payload ? { ...payload, ...(locator ? { locator } : {}), ...(peers ? { peers } : {}) } : payload);
    const renderedNavigation = JSON.stringify(diagram.rendered.navigation ?? null);
    if (staleNodes.length || expectedNavigation !== renderedNavigation) {
      const what = staleNodes.length ? `ノード ${staleNodes.map((node) => node.id).join(', ')} のリンク` : '親図／マップのリンク、または親図・リンク先・参照元の縮図';
      report('error', 'hierarchy/stale-html', `${where} の HTML が仕様と一致しません（${what}）。deliver で再生成してください`, { diagram: where });
    }
  }

  // Synced facts (breadcrumb trail, onward counts) must match the graph.
  const rootMap = root.hierarchy?.map ? path.resolve(path.dirname(root.htmlPath), root.hierarchy.map.href) : null;
  const derived = deriveHierarchy({ root: root.htmlPath, diagrams: [...diagrams.values()], edges }, rootMap);
  for (const diagram of diagrams.values()) {
    const want = derived.get(diagram.specPath);
    const haveTrail = diagram.hierarchy?.trail || [];
    const haveSiblings = diagram.hierarchy?.siblings || [];
    const haveIncoming = diagram.hierarchy?.incoming || [];
    const staleOnward = diagram.nodes.filter((node) => node.link && Object.prototype.hasOwnProperty.call(want.onward, node.id)
      && (node.link.onward !== want.onward[node.id] || node.link.title !== want.titles[node.id]));
    if (JSON.stringify(haveTrail) !== JSON.stringify(want.trail) || JSON.stringify(haveSiblings) !== JSON.stringify(want.siblings) || JSON.stringify(haveIncoming) !== JSON.stringify(want.incoming) || staleOnward.length) {
      report('error', 'hierarchy/sync-stale',
        `${rel(diagram.specPath)} のパンくず／同じ階層の図／参照元／子図の数がリンク構造と一致しません。archify hierarchy-sync で更新し、deliver し直してください`,
        { diagram: rel(diagram.specPath) });
    }
  }

  // One destination split over several nodes reads as several places; wrap
  // the nodes in a boundary and link the boundary once.
  for (const diagram of diagrams.values()) {
    const byTarget = new Map();
    for (const node of diagram.nodes) {
      if (node.group || !node.link) continue;
      const key = JSON.stringify([path.resolve(path.dirname(diagram.htmlPath), node.link.href), node.link.focus || null, node.link.view || null]);
      if (!byTarget.has(key)) byTarget.set(key, []);
      byTarget.get(key).push(node);
    }
    for (const [key, nodes] of byTarget) {
      if (nodes.length < 2) continue;
      const target = rel(JSON.parse(key)[0]);
      report('warning', 'hierarchy/split-destination',
        `${rel(diagram.specPath)} のノード ${nodes.map((node) => node.label).join('、')} が同じ遷移先 ${target} を指しています。囲み（boundary）にまとめ、囲みに link を付けてください`,
        { diagram: rel(diagram.specPath), nodes: nodes.map((node) => node.id), target });
    }
  }

  // A cross link between two detail diagrams should follow a line in their
  // common parent, or the jump looks arbitrary from the overview.
  const parentOf = treeParents({ root: root.htmlPath, diagrams: [...diagrams.values()], edges });
  const carriersTo = (parent, target) => {
    const ids = new Set();
    const labels = [];
    for (const node of parent.nodes) {
      if (!node.link || path.resolve(path.dirname(parent.htmlPath), node.link.href) !== target) continue;
      labels.push(node.label);
      for (const id of node.group ? node.members : [node.id]) ids.add(id);
    }
    return { ids, labels };
  };
  const unbacked = new Set();
  for (const edge of edges) {
    const parentPath = parentOf.get(edge.from);
    if (!parentPath || parentOf.get(edge.to) !== parentPath || edge.to === parentPath || edge.to === edge.from) continue;
    const parent = diagrams.get(parentPath);
    if (!parent?.rendered) continue;
    const from = carriersTo(parent, edge.from);
    const to = carriersTo(parent, edge.to);
    if (!from.ids.size || !to.ids.size) continue;
    const ends = (id) => parent.groupMembers?.[id] || [id];
    const touches = (id, set) => ends(id).some((member) => set.has(member));
    const backed = parent.rendered.edges.some(([a, b]) => (touches(a, from.ids) && touches(b, to.ids)) || (touches(b, from.ids) && touches(a, to.ids)));
    const key = `${edge.from}\n${edge.to}`;
    if (backed || unbacked.has(key)) continue;
    unbacked.add(key);
    report('warning', 'hierarchy/cross-link-unbacked',
      `${rel(diagrams.get(edge.from).specPath)} から ${rel(diagrams.get(edge.to).specPath)} へのリンクに対応する線が、親図 ${rel(parent.specPath)} の ${from.labels.join('・')} と ${to.labels.join('・')} の間にありません`,
      { diagram: rel(diagrams.get(edge.from).specPath), target: rel(diagrams.get(edge.to).specPath), parent: rel(parent.specPath) });
  }

  // A link between detail diagrams should land on a node, or the reader sees
  // which diagram it opens but not which node the two diagrams share.
  for (const edge of edges) {
    if (edge.link.focus || edge.from === edge.to || !diagrams.has(edge.to)) continue;
    if (parentOf.get(edge.to) === edge.from || parentOf.get(edge.from) === edge.to) continue;
    const source = diagrams.get(edge.from);
    if (source.nodes.find((node) => node.id === edge.node)?.group) continue;
    report('warning', 'hierarchy/cross-link-unfocused',
      `${rel(source.specPath)} のノード ${edge.node}（${edge.label}）から ${rel(diagrams.get(edge.to).specPath)} へのリンクに focus がありません。遷移先で対応するノードの id を link.focus に書いてください`,
      { diagram: rel(source.specPath), node: edge.node, target: rel(diagrams.get(edge.to).specPath) });
  }

  if (mapTargets.size > 1) {
    report('warning', 'hierarchy/map-inconsistent', `図ごとにマップの参照先が異なります: ${[...mapTargets].map(rel).join(', ')}`);
  }

  if (scanDir) {
    const reachable = new Set([...diagrams.values()].map((diagram) => diagram.specPath));
    // The map's own spec is generated output, not a diagram of the hierarchy.
    const maps = new Set([...mapTargets, ...pending]);
    for (const specPath of listSpecs(path.resolve(scanDir))) {
      const spec = readJson(specPath);
      if (maps.has(path.resolve(htmlPathForSpec(specPath, spec)))) continue;
      if (!reachable.has(specPath)) {
        report('warning', 'hierarchy/orphan', `${rel(specPath)} はルートからどのリンクでも辿れません`, { diagram: rel(specPath) });
      }
    }
  }

  const summary = summarize(diagnostics);
  return { ok: summary.errors === 0, root: root.htmlPath, rootDir, diagrams: [...diagrams.values()], edges, diagnostics, summary };
}

function summarize(diagnostics) {
  return {
    errors: diagnostics.filter((d) => d.severity === 'error').length,
    warnings: diagnostics.filter((d) => d.severity === 'warning').length,
  };
}

// Tree for the map page: each diagram hangs under its declared parent when
// that parent links to it, otherwise under the first diagram that reached it.
// Each diagram hangs under its declared parent when that parent links to it,
// otherwise under the first diagram that reached it.
export function treeParents(result) {
  const parentOf = new Map();
  for (const diagram of result.diagrams) {
    if (diagram.htmlPath === result.root) continue;
    const incoming = result.edges.filter((edge) => edge.to === diagram.htmlPath);
    const declared = diagram.hierarchy?.parent
      ? path.resolve(path.dirname(diagram.htmlPath), diagram.hierarchy.parent.href)
      : null;
    const chosen = incoming.find((edge) => edge.from === declared) || incoming[0];
    if (chosen) parentOf.set(diagram.htmlPath, chosen.from);
  }
  return parentOf;
}

const posix = (value) => value.split(path.sep).join('/');

// Labels sync writes are bounded by the schema (crumbs 80, incoming 120);
// diagram titles are not, so long ones are shortened rather than rejected.
// Counted in code points, as the schema does, so emoji are never split.
export function clipLabel(text, max = 80) {
  const chars = Array.from(String(text ?? ''));
  return chars.length > max ? `${chars.slice(0, max - 1).join('')}…` : chars.join('');
}

// Concern directory of a root child: the folder above its own folder, as in
// the recommended `<concern>/<diagram>/<diagram>.html` layout.
export function concernKey(hrefFromMap) {
  const parts = hrefFromMap.split('/');
  return parts.length >= 3 ? parts.slice(0, -2).join('/') : null;
}

export function concernId(key) {
  return `c-${key.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '')}`.slice(0, 60);
}

/**
 * Cross-diagram facts every diagram shows but cannot compute alone:
 *   trail  — breadcrumb from the root to the parent (concern levels link to
 *            the map focused on that concern)
 *   onward — per link, how many diagrams the target links on to
 *   titles — per link, the target diagram's title (the viewer names it)
 *   siblings — the diagrams sharing this one's parent (and concern), in the
 *            parent's link order, so a detail page can show where it sits
 *   incoming — cross links from other detail diagrams into this one (not the
 *            tree parent's links, not links back up to a parent), so the
 *            node they land on can show where readers come from
 * Returned per spec path; `archify hierarchy-sync` writes them into specs and
 * checkHierarchy reports specs that disagree.
 */
export function deriveHierarchy(result, mapPath = null) {
  const parentOf = treeParents(result);
  const byHtml = new Map(result.diagrams.map((diagram) => [diagram.htmlPath, diagram]));
  const mapDir = mapPath ? path.dirname(path.resolve(mapPath)) : null;
  const onwardOf = new Map();
  for (const edge of result.edges) {
    if (!onwardOf.has(edge.from)) onwardOf.set(edge.from, new Set());
    if (edge.to !== edge.from) onwardOf.get(edge.from).add(edge.to);
  }
  const trails = new Map();
  function trailOf(htmlPath, seen = new Set()) {
    if (trails.has(htmlPath)) return trails.get(htmlPath);
    const parent = parentOf.get(htmlPath);
    if (!parent || seen.has(parent) || !byHtml.has(parent)) {
      trails.set(htmlPath, []);
      return [];
    }
    const crumbs = [...trailOf(parent, new Set([...seen, htmlPath])),
      { htmlPath: parent, label: clipLabel(byHtml.get(parent).title) }];
    if (parent === result.root && mapDir) {
      const key = concernKey(posix(path.relative(mapDir, htmlPath)));
      if (key) crumbs.push({ htmlPath: path.resolve(mapPath), label: key.split('/').pop(), focus: concernId(key) });
    }
    trails.set(htmlPath, crumbs);
    return crumbs;
  }
  const concernOf = (htmlPath) => (mapDir ? concernKey(posix(path.relative(mapDir, htmlPath))) : null);
  function siblingsOf(htmlPath, from) {
    const parent = parentOf.get(htmlPath);
    if (!parent) return [];
    const sameConcern = parent !== result.root || concernOf(htmlPath) === null
      ? () => true
      : (other) => concernOf(other) === concernOf(htmlPath);
    const group = [];
    for (const edge of result.edges) {
      if (edge.from !== parent || group.includes(edge.to)) continue;
      if (parentOf.get(edge.to) !== parent || !byHtml.has(edge.to) || !sameConcern(edge.to)) continue;
      group.push(edge.to);
    }
    if (group.length < 2) return [];
    return group.map((other) => ({ href: posix(path.relative(from, other)), label: clipLabel(byHtml.get(other).title) }));
  }
  const derived = new Map();
  for (const diagram of result.diagrams) {
    const from = path.dirname(diagram.htmlPath);
    const trail = trailOf(diagram.htmlPath).map((crumb) => ({
      href: posix(path.relative(from, crumb.htmlPath)),
      label: crumb.label,
      ...(crumb.focus ? { focus: crumb.focus } : {}),
    }));
    const onward = {};
    const titles = {};
    for (const node of diagram.nodes) {
      if (!node.link) continue;
      const target = path.resolve(from, node.link.href);
      if (byHtml.has(target)) {
        onward[node.id] = (onwardOf.get(target) || new Set()).size;
        titles[node.id] = byHtml.get(target).title;
      }
    }
    const incoming = [];
    for (const edge of result.edges) {
      if (edge.to !== diagram.htmlPath || edge.from === edge.to || !byHtml.has(edge.from)) continue;
      if (parentOf.get(edge.to) === edge.from || parentOf.get(edge.from) === edge.to) continue;
      const source = byHtml.get(edge.from);
      if (!source.nodes.find((node) => node.id === edge.node && !node.group)) continue;
      incoming.push({
        href: posix(path.relative(from, edge.from)),
        label: clipLabel(source.title, 120),
        node: edge.node,
        node_label: clipLabel(edge.label, 120),
        ...(edge.link.focus ? { focus: edge.link.focus } : {}),
      });
    }
    derived.set(diagram.specPath, { trail, onward, titles, siblings: siblingsOf(diagram.htmlPath, from), incoming, level: trail.length });
  }
  return derived;
}

export function hierarchyTree(result, mapPath) {
  const mapDir = path.dirname(path.resolve(mapPath));
  const toMap = (file) => path.relative(mapDir, file).split(path.sep).join('/');
  const byHtml = new Map(result.diagrams.map((diagram) => [diagram.htmlPath, diagram]));
  const parentOf = treeParents(result);
  const issuesFor = (diagram) => result.diagnostics
    .filter((d) => d.subject?.diagram === path.relative(result.rootDir, diagram.specPath).split(path.sep).join('/'))
    .map((d) => ({ severity: d.severity, code: d.code, message: d.message }));

  function build(htmlPath, trail) {
    const diagram = byHtml.get(htmlPath);
    const leafIds = new Set((diagram.hierarchy?.leaf_nodes || []).map((leaf) => leaf.id));
    const outgoing = result.edges.filter((edge) => edge.from === htmlPath);
    const children = [];
    const seen = new Set();
    for (const edge of outgoing) {
      if (seen.has(edge.to) || trail.has(edge.to)) continue;
      if (parentOf.get(edge.to) !== htmlPath || !byHtml.has(edge.to)) continue;
      seen.add(edge.to);
      children.push(build(edge.to, new Set([...trail, edge.to])));
    }
    return {
      title: diagram.title,
      type: diagram.type,
      href: toMap(diagram.htmlPath),
      spec: toMap(diagram.specPath),
      nodeCount: diagram.nodes.filter((node) => !node.group).length,
      linkedCount: diagram.nodes.filter((node) => node.link).length,
      leafCount: leafIds.size,
      links: outgoing.map((edge) => ({
        node: edge.node,
        label: edge.label,
        target: byHtml.get(edge.to)?.title || edge.link.href,
        href: `${toMap(edge.to)}${edge.link.view || edge.link.focus ? '#' + [edge.link.view ? `view=${encodeURIComponent(edge.link.view)}` : null, edge.link.focus ? `focus=${encodeURIComponent(edge.link.focus)}` : null].filter(Boolean).join('&') : ''}`,
        resolved: byHtml.has(edge.to),
      })),
      leaves: (diagram.hierarchy?.leaf_nodes || []).map((leaf) => ({
        node: leaf.id,
        label: diagram.nodes.find((node) => node.specId === leaf.id)?.label || leaf.id,
        reason: leaf.reason,
      })),
      issues: issuesFor(diagram),
      children,
    };
  }
  return build(result.root, new Set([result.root]));
}

/**
 * Writes the derived trail and onward counts into every reachable spec.
 * Returns the specs whose content changed; they need `deliver` afterwards.
 */
export function syncHierarchy(rootSpecPath, { write = true } = {}) {
  const result = checkHierarchy(rootSpecPath);
  if (!result.diagrams.length) return { result, changed: [] };
  const root = result.diagrams.find((diagram) => diagram.htmlPath === result.root);
  const mapPath = root.hierarchy?.map ? path.resolve(path.dirname(root.htmlPath), root.hierarchy.map.href) : null;
  const derived = deriveHierarchy(result, mapPath);
  const parentOf = treeParents(result);
  const byHtml = new Map(result.diagrams.map((diagram) => [diagram.htmlPath, diagram]));
  const changed = [];
  for (const diagram of result.diagrams) {
    const raw = fs.readFileSync(diagram.specPath, 'utf8');
    const spec = JSON.parse(raw);
    const want = derived.get(diagram.specPath);
    const hierarchy = { ...(spec.meta.hierarchy || {}) };
    if (want.trail.length) hierarchy.trail = want.trail;
    else delete hierarchy.trail;
    if (want.siblings.length) hierarchy.siblings = want.siblings;
    else delete hierarchy.siblings;
    if (want.incoming.length) hierarchy.incoming = want.incoming;
    else delete hierarchy.incoming;
    const parent = parentOf.get(diagram.htmlPath);
    if (parent && !hierarchy.parent) {
      hierarchy.parent = { href: posix(path.relative(path.dirname(diagram.htmlPath), parent)), label: clipLabel(byHtml.get(parent).title) };
    }
    if (Object.keys(hierarchy).length) spec.meta.hierarchy = hierarchy;
    const carriers = [
      ...hierarchyNodeEntries(spec.diagram_type, spec).map(({ node, renderedId }) => ({ node, id: renderedId })),
      ...hierarchyGroups(spec.diagram_type, spec).map((group) => ({ node: group, id: group.id })),
    ];
    for (const { node, id } of carriers) {
      if (!node.link) continue;
      if (Object.prototype.hasOwnProperty.call(want.onward, id)) {
        node.link.onward = want.onward[id];
        node.link.title = want.titles[id];
      } else {
        delete node.link.onward;
        delete node.link.title;
      }
    }
    const next = `${JSON.stringify(spec, null, 2)}\n`;
    if (next !== raw) {
      changed.push(diagram.specPath);
      if (write) fs.writeFileSync(diagram.specPath, next);
    }
  }
  return { result, changed };
}
