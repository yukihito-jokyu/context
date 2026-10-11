import fs from 'node:fs';
import path from 'node:path';

// A child page shows where it sits inside its parent diagram: a thumbnail of
// the parent's nodes and edges, read from the parent's rendered SVG. Each
// parent node carries its link target relative to the child, so the viewer can
// light up this page's node and its siblings' nodes. Geometry is read at
// render time (render parents first) and never written into specs.

const unescapeHtml = (value) => value
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const posix = (value) => value.split(path.sep).join('/');
const round = (value) => Math.round(value * 10) / 10;

function attr(tag, name) {
  const found = tag.match(new RegExp(`\\s${name}="([^"]*)"`));
  return found ? unescapeHtml(found[1]) : null;
}

function numbers(value) {
  return (value.match(/-?\d*\.?\d+(?:e-?\d+)?/gi) || []).map(Number);
}

// Geometry of a rendered diagram: viewBox, node boxes, boundary frames and
// drawn edges, with link hrefs as written in that HTML.
export function readGeometry(htmlPath) {
  let html;
  try {
    html = fs.readFileSync(htmlPath, 'utf8');
  } catch (_) {
    return null;
  }
  const start = html.search(/<svg\b[^>]*\sviewBox="/);
  if (start < 0) return null;
  const svg = html.slice(start, html.indexOf('</svg>', start));
  const viewBox = numbers(attr(svg.slice(0, svg.indexOf('>') + 1), 'viewBox') || '');
  if (viewBox.length !== 4) return null;

  // Walk the tags keeping the translate offset of every open <g>: ER and
  // class nodes draw their box inside a translated group, and composite
  // diagrams translate each half. Anything under another kind of transform
  // (scale, rotate) is left out.
  const translateOf = (tag) => {
    const transform = attr(tag, 'transform');
    if (!transform) return [0, 0];
    const found = transform.trim().match(/^translate\(\s*(-?[\d.]+(?:e-?\d+)?)(?:[\s,]+(-?[\d.]+(?:e-?\d+)?))?\s*\)$/i);
    return found ? [Number(found[1]), Number(found[2] || 0)] : null;
  };
  const nodes = [];
  const groups = [];
  const rawEdges = [];
  const stack = [{ offset: [0, 0], ok: true, node: null }];
  for (const match of svg.matchAll(/<(\/?)(g|rect|path)\b([^>]*?)(\/?)>/g)) {
    const [tag, closing, name, , selfClosing] = match;
    const top = stack[stack.length - 1];
    if (name === 'g') {
      if (closing) {
        if (stack.length > 1) stack.pop();
        continue;
      }
      const shift = translateOf(tag);
      const entry = {
        offset: shift ? [top.offset[0] + shift[0], top.offset[1] + shift[1]] : top.offset,
        ok: top.ok && !!shift,
        node: top.node,
      };
      const id = attr(tag, 'data-node-id');
      if (id) {
        const href = attr(tag, 'data-node-link-href');
        entry.node = { id, label: attr(tag, 'data-node-label') || id, ...(href ? { href } : {}), box: null, ok: entry.ok };
        nodes.push(entry.node);
      }
      if (!selfClosing) stack.push(entry);
      continue;
    }
    if (closing) continue;
    const shift = translateOf(tag);
    if (!shift || !top.ok) continue;
    const dx = top.offset[0] + shift[0];
    const dy = top.offset[1] + shift[1];
    if (name === 'rect') {
      const [x, y, width, height] = ['x', 'y', 'width', 'height'].map((key) => Number(attr(tag, key) ?? 0));
      if (![x, y, width, height].every(Number.isFinite)) continue;
      const boundary = attr(tag, 'data-boundary-id');
      if (boundary) {
        const href = attr(tag, 'data-node-link-href');
        groups.push({
          id: boundary,
          label: attr(tag, 'data-boundary-label') || boundary,
          box: [round(x + dx), round(y + dy), round(width), round(height)],
          ...(href ? { href } : {}),
          group: true,
        });
        continue;
      }
      // A node's box is the first rect drawn inside it.
      if (top.node && !top.node.box && width && height) top.node.box = [round(x + dx), round(y + dy), round(width), round(height)];
      continue;
    }
    const from = attr(tag, 'data-edge-from');
    const to = attr(tag, 'data-edge-to');
    const d = attr(tag, 'd');
    if (from === null || to === null || !d) continue;
    const values = numbers(d);
    const points = [];
    for (let i = 0; i + 1 < values.length; i += 2) points.push([round(values[i] + dx), round(values[i + 1] + dy)]);
    if (points.length >= 2) rawEdges.push({ from, to, points });
  }
  const placed = nodes.filter((node) => node.box).map(({ box, ok, ...node }) => ({ ...node, box }));
  if (!placed.length) return null;
  const known = new Set([...placed, ...groups].map((node) => node.id));
  const edges = rawEdges.filter((edge) => known.has(edge.from) && known.has(edge.to));
  return { viewBox: viewBox.map(round), groups, nodes: placed, edges };
}

export function readLocator(parentHtmlPath, childHtmlPath) {
  const geometry = readGeometry(parentHtmlPath);
  if (!geometry) return null;
  const parentDir = path.dirname(path.resolve(parentHtmlPath));
  const childDir = path.dirname(path.resolve(childHtmlPath));
  // Each parent node carries its link target relative to the child.
  const toChild = (href) => posix(path.relative(childDir, path.resolve(parentDir, href.split('#')[0])));
  const strip = ({ href, ...item }) => ({ ...item, ...(href ? { to: toChild(href) } : {}) });
  const nodes = geometry.nodes.map(strip);
  // Boundaries that link as a group: drawn as a frame on the thumbnail, and
  // their unlinked members take the group's target.
  const groups = geometry.groups.map(strip);
  const inside = (outer, inner) => inner[0] >= outer[0] && inner[1] >= outer[1]
    && inner[0] + inner[2] <= outer[0] + outer[2] && inner[1] + inner[3] <= outer[1] + outer[3];
  for (const node of nodes) {
    if (node.to) continue;
    const owner = groups.filter((group) => group.to && inside(group.box, node.box))
      .sort((a, b) => a.box[2] * a.box[3] - b.box[2] * b.box[3])[0];
    if (owner) {
      node.to = owner.to;
      node.group = owner.id;
    }
  }
  return { viewBox: geometry.viewBox, groups, nodes, edges: geometry.edges };
}

// deliver/compare render inside a staging folder next to the final file
// (`<dir>/.archify-*/`); resolve from where the HTML will actually live.
function finalPathOf(outPath) {
  const finalPath = path.resolve(outPath);
  if (/^\.archify-/.test(path.basename(path.dirname(finalPath)))) {
    return path.join(path.dirname(path.dirname(finalPath)), path.basename(finalPath));
  }
  return finalPath;
}

// The locator for a diagram whose meta names a parent, resolved from the
// HTML being written.
export function locatorFor(meta, outPath) {
  const parent = meta?.hierarchy?.parent;
  if (!parent?.href || meta.hierarchy.role === 'map') return null;
  const finalPath = finalPathOf(outPath);
  const parentPath = path.resolve(path.dirname(finalPath), parent.href);
  return readLocator(parentPath, finalPath);
}

// Thumbnails of the diagrams this page cross-links with, keyed by href as
// written: the node a link lands on, and the node a link comes from, are
// drawn on them. Links down the tree (no `..`, as the viewer reads a descent)
// and the parent are left out, so parents never wait on their children.
export function peersFor(meta, outPath, hrefs) {
  const hierarchy = meta?.hierarchy;
  if (!hierarchy || hierarchy.role === 'map') return null;
  const finalPath = finalPathOf(outPath);
  const dir = path.dirname(finalPath);
  const parentPath = hierarchy.parent?.href ? path.resolve(dir, hierarchy.parent.href) : null;
  const descent = (href) => {
    const clean = href.replace(/^(\.\/)+/, '');
    return clean.includes('/') && !clean.split('/').includes('..');
  };
  const wanted = [...hrefs, ...(hierarchy.incoming || []).map((entry) => entry.href)]
    .map((href) => href.split('#')[0])
    .filter((href) => !descent(href));
  const peers = {};
  for (const href of [...new Set(wanted)].sort()) {
    const target = path.resolve(dir, href);
    if (target === finalPath || target === parentPath) continue;
    const geometry = readGeometry(target);
    if (!geometry) continue;
    const strip = ({ href: _href, ...item }) => item;
    peers[href] = { viewBox: geometry.viewBox, groups: geometry.groups.map(strip), nodes: geometry.nodes.map(strip), edges: geometry.edges };
  }
  return Object.keys(peers).length ? peers : null;
}

// Link hrefs as they appear in rendered SVG markup.
export function linkHrefsIn(svg) {
  return [...String(svg).matchAll(/\sdata-node-link-href="([^"]*)"/g)].map((match) => unescapeHtml(match[1]));
}
