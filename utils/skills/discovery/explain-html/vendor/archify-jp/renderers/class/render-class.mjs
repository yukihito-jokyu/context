import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { esc } from '../shared/utils.mjs';
import { focusEdgeAttrs, focusNodeAttrs, loadDiagram, svgAccessibleText, svgRootAttrs, writeDiagram } from '../shared/cli.mjs';
import { throwDiagnosticProblems } from '../shared/diagnostics.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { diagram, template, outPath } = loadDiagram({ rendererDir: __dirname, diagramType: 'class', defaultExample: 'domain-model.class.json' });
const visibility = { public: '+', protected: '#', package: '~', private: '−' };

function methodLines(method, width) {
  const params = method.parameters.map((p) => `${p.name}: ${p.type}`).join(', ');
  const lead = `${visibility[method.visibility]} ${method.static ? '$' : ''}${method.name}`;
  const head = `${lead}(${params})`;
  const full = `${head}: ${method.return_type}`;
  const units = Math.max(12, Math.floor((width - 28) / 6.8));
  if (full.length <= units) return [full];
  if (head.length <= units) return [head, `  : ${method.return_type}`];
  return [`${lead}(`, `  ${params}`, `): ${method.return_type}`];
}

function measure(item) {
  const width = item.width || 240;
  const attributeRows = Math.max(1, item.attributes.length);
  const methodRows = item.methods.length ? item.methods.reduce((n, m) => n + methodLines(m, width).length, 0) : 1;
  return { item, x: item.pos[0], y: item.pos[1], width, height: 58 + 16 + attributeRows * 23 + 16 + methodRows * 20 + 8 };
}

const boxes = new Map(diagram.classes.map((item) => [item.id, measure(item)]));
const problems = [];
for (const relation of diagram.relationships) {
  if (!boxes.has(relation.from)) problems.push(`/relationships/${relation.id}/fromが不明なクラス ${JSON.stringify(relation.from)} を参照しています`);
  if (!boxes.has(relation.to)) problems.push(`/relationships/${relation.id}/toが不明なクラス ${JSON.stringify(relation.to)} を参照しています`);
}
if (problems.length) throwDiagnosticProblems('クラス関係の検証に失敗しました', problems, { code: 'class/unknown-reference', subject: { diagramType: 'class' } });

function route(from, to) {
  const fc = [from.x + from.width / 2, from.y + from.height / 2];
  const tc = [to.x + to.width / 2, to.y + to.height / 2];
  const dx = tc[0] - fc[0]; const dy = tc[1] - fc[1];
  let start; let end; let points;
  if (Math.abs(dy) > Math.abs(dx) * 0.7) {
    const down = dy >= 0;
    start = [fc[0], down ? from.y + from.height : from.y]; end = [tc[0], down ? to.y : to.y + to.height];
    const m = (start[1] + end[1]) / 2; points = [start, [start[0], m], [end[0], m], end];
  } else {
    const right = dx >= 0;
    start = [right ? from.x + from.width : from.x, fc[1]]; end = [right ? to.x : to.x + to.width, tc[1]];
    const m = (start[0] + end[0]) / 2; points = [start, [m, start[1]], [m, end[1]], end];
  }
  return { start, end, points: points.filter((p, i, a) => i === 0 || p[0] !== a[i - 1][0] || p[1] !== a[i - 1][1]) };
}

function pathData(points) { return points.map((p, i) => `${i ? 'L' : 'M'} ${p[0]} ${p[1]}`).join(' '); }
function marker(kind) {
  if (kind === 'composition') return ' marker-start="url(#class-diamond-filled)"';
  if (kind === 'aggregation') return ' marker-start="url(#class-diamond-open)"';
  if (kind === 'inheritance' || kind === 'realization') return ' marker-end="url(#class-triangle)"';
  if (kind === 'dependency') return ' marker-end="url(#class-arrow-open)"';
  return '';
}

function renderRelation(relation, index) {
  const r = route(boxes.get(relation.from), boxes.get(relation.to));
  const mi = Math.max(0, Math.floor((r.points.length - 1) / 2));
  const mid = [(r.points[mi][0] + r.points[mi + 1][0]) / 2, (r.points[mi][1] + r.points[mi + 1][1]) / 2];
  return `        <g data-relation-id="${esc(relation.id)}"><path ${focusEdgeAttrs(relation.from, relation.to, relation.label, index, relation.id)} class="class-edge ${esc(relation.kind)}" d="${pathData(r.points)}"${marker(relation.kind)}/>${relation.label ? `<text class="class-label" x="${mid[0]}" y="${mid[1] - 9}">${esc(relation.label)}</text>` : ''}${relation.from_multiplicity ? `<text class="class-multiplicity" x="${r.start[0]}" y="${r.start[1] + 18}">${esc(relation.from_multiplicity)}</text>` : ''}${relation.to_multiplicity ? `<text class="class-multiplicity" x="${r.end[0]}" y="${r.end[1] + 18}">${esc(relation.to_multiplicity)}</text>` : ''}</g>`;
}

function renderNode(box) {
  const { item, x, y, width, height } = box;
  const attrBottom = 58 + 16 + Math.max(1, item.attributes.length) * 23;
  const attrs = item.attributes.length ? item.attributes.map((a, i) => `<text class="class-member" x="14" y="${82 + i * 23}">${esc(`${visibility[a.visibility]} ${a.static ? '$' : ''}${a.name}: ${a.type}`)}</text>`).join('') : '<text class="class-member class-empty" x="14" y="82">—</text>';
  const methods = item.methods.length ? item.methods.flatMap((m) => methodLines(m, width)).map((line, i) => `<text class="class-member" x="14" y="${attrBottom + 28 + i * 20}">${esc(line)}</text>`).join('') : `<text class="class-member class-empty" x="14" y="${attrBottom + 28}">—</text>`;
  const semanticKind = item.kind === 'interface' ? 'external' : 'backend';
  return `        <g class="class-node ${esc(item.kind)}" ${focusNodeAttrs(item.id, item.name, { kind: semanticKind, sublabel: item.stereotype || item.kind, context: item.kind === 'interface' ? 'UML interface' : 'UML class' }, diagram.meta.locale)}>
          <g transform="translate(${x} ${y})"><title>${esc([item.name, item.stereotype].filter(Boolean).join(' · '))}</title><rect width="${width}" height="${height}" rx="8"/><text class="class-stereo" x="${width / 2}" y="20">&lt;&lt;${esc(item.stereotype || item.kind)}&gt;&gt;</text><text class="class-name" data-node-label x="${width / 2}" y="44">${esc(item.name)}</text><line class="class-divider" x1="0" y1="58" x2="${width}" y2="58"/>${attrs}<line class="class-divider" x1="0" y1="${attrBottom}" x2="${width}" y2="${attrBottom}"/>${methods}</g>
        </g>`;
}

const measured = [...boxes.values()];
const viewBox = diagram.meta.viewBox || [Math.ceil(Math.max(...measured.map((b) => b.x + b.width)) + 60), Math.ceil(Math.max(...measured.map((b) => b.y + b.height)) + 60)];
const definitions = `<defs><style>.class-node rect{fill:var(--backend-fill);stroke:var(--backend-stroke);stroke-width:2}.class-node.interface rect{fill:var(--cloud-fill);stroke:var(--cloud-stroke)}.class-divider{stroke:var(--grid)}.class-name{fill:var(--text);font-size:17px;font-weight:700;text-anchor:middle}.class-stereo{fill:var(--text-muted);font-size:11px;text-anchor:middle}.class-member{fill:var(--text);font-size:11px}.class-empty{fill:var(--text-dim)}.class-edge{fill:none;stroke:var(--arrow);stroke-width:2}.class-edge.dependency,.class-edge.realization{stroke-dasharray:7 6}.class-label{fill:var(--text-muted);font-size:11px;text-anchor:middle;paint-order:stroke;stroke:var(--mask);stroke-width:5px}.class-multiplicity{fill:var(--text);font-size:11px;font-weight:700;text-anchor:middle}</style><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" class="c-grid" stroke-width=".5"/></pattern><marker id="class-triangle" viewBox="0 0 14 14" refX="13" refY="7" markerWidth="12" markerHeight="12" orient="auto"><path d="M1 1L13 7L1 13Z" fill="var(--mask)" stroke="var(--arrow)" stroke-width="1.5"/></marker><marker id="class-diamond-filled" viewBox="0 0 14 14" refX="1" refY="7" markerWidth="12" markerHeight="12" orient="auto"><path d="M1 7L7 1L13 7L7 13Z" fill="var(--text)" stroke="var(--arrow)"/></marker><marker id="class-diamond-open" viewBox="0 0 14 14" refX="1" refY="7" markerWidth="12" markerHeight="12" orient="auto"><path d="M1 7L7 1L13 7L7 13Z" fill="var(--mask)" stroke="var(--arrow)"/></marker><marker id="class-arrow-open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="9" markerHeight="9" orient="auto"><path d="M1 1L11 6L1 11" fill="none" stroke="var(--arrow)" stroke-width="1.5"/></marker></defs>`;
const svg = `      <svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}" ${svgRootAttrs(diagram.meta)} data-diagram-type="class" data-focus-camera="node">\n${svgAccessibleText(diagram.meta, 'class')}\n        ${definitions}\n        <rect width="100%" height="100%" fill="url(#grid)"/>\n${diagram.relationships.map(renderRelation).join('\n')}\n${measured.map(renderNode).join('\n')}\n      </svg>`;
writeDiagram({ outPath, template, diagramType: 'class', meta: diagram.meta, svg, cards: diagram.cards });
