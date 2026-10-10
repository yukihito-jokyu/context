import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { esc } from '../shared/utils.mjs';
import { focusEdgeAttrs, focusNodeAttrs, loadDiagram, svgAccessibleText, svgRootAttrs, writeDiagram } from '../shared/cli.mjs';
import { throwDiagnosticProblems } from '../shared/diagnostics.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { diagram, template, outPath } = loadDiagram({ rendererDir: __dirname, diagramType: 'er', defaultExample: 'ecommerce.er.json' });
function measure(item) { return { item, x: item.pos[0], y: item.pos[1], width: item.width || 270, height: 45 + item.columns.length * 41 }; }
const boxes = new Map(diagram.entities.map((item) => [item.id, measure(item)]));
const columns = new Map(diagram.entities.map((entity) => [entity.id, new Set(entity.columns.map((column) => column.id))]));
const problems = [];
for (const entity of diagram.entities) for (const column of entity.columns) if (column.foreign_key && !columns.get(column.foreign_key.entity)?.has(column.foreign_key.column)) problems.push(`/entities/${entity.id}/columns/${column.id}/foreign_keyが不明な列を参照しています`);
for (const relation of diagram.relationships) for (const side of ['from', 'to']) if (!columns.get(relation[side].entity)?.has(relation[side].column)) problems.push(`/relationships/${relation.id}/${side}が不明な列を参照しています`);
if (problems.length) throwDiagnosticProblems('ER参照の検証に失敗しました', problems, { code: 'er/unknown-reference', subject: { diagramType: 'er' } });

function columnY(box, columnId) { return box.y + 45 + box.item.columns.findIndex((c) => c.id === columnId) * 41 + 20; }
function route(from, to, fromColumn, toColumn) {
  const fc = [from.x + from.width / 2, from.y + from.height / 2]; const tc = [to.x + to.width / 2, to.y + to.height / 2];
  const dx = tc[0] - fc[0]; const dy = tc[1] - fc[1];
  if (Math.abs(dy) > Math.abs(dx) * 0.7) {
    const down = dy >= 0; const start = [fc[0], down ? from.y + from.height : from.y]; const end = [tc[0], down ? to.y : to.y + to.height]; const m = (start[1] + end[1]) / 2;
    return [start, [start[0], m], [end[0], m], end].filter((p, i, a) => i === 0 || p[0] !== a[i - 1][0] || p[1] !== a[i - 1][1]);
  }
  const right = dx >= 0; const start = [right ? from.x + from.width : from.x, columnY(from, fromColumn)]; const end = [right ? to.x : to.x + to.width, columnY(to, toColumn)]; const m = (start[0] + end[0]) / 2;
  return [start, [m, start[1]], [m, end[1]], end].filter((p, i, a) => i === 0 || p[0] !== a[i - 1][0] || p[1] !== a[i - 1][1]);
}
function pathData(points) { return points.map((p, i) => `${i ? 'L' : 'M'} ${p[0]} ${p[1]}`).join(' '); }
function marker(value) { return `url(#cf-${value.replaceAll('_', '-')})`; }
function renderRelation(relation, index) {
  const points = route(boxes.get(relation.from.entity), boxes.get(relation.to.entity), relation.from.column, relation.to.column);
  const label = relation.label || `${relation.from_cardinality} : ${relation.to_cardinality}`;
  return `        <path ${focusEdgeAttrs(relation.from.entity, relation.to.entity, label, index, relation.id)} class="er-edge ${relation.identifying ? 'identifying' : 'non-identifying'}" d="${pathData(points)}" marker-start="${marker(relation.from_cardinality)}" marker-end="${marker(relation.to_cardinality)}"/>`;
}
function renderNode(box) {
  const { item, x, y, width, height } = box;
  const rows = item.columns.map((column, index) => {
    const baseline = 70 + index * 41; const rule = index ? `<line class="er-rule" x1="0" y1="${45 + index * 41}" x2="${width}" y2="${45 + index * 41}"/>` : '';
    const badges = [column.primary_key ? '<tspan class="er-pk">PK</tspan>' : '', column.foreign_key ? '<tspan class="er-fk">FK</tspan>' : '', column.unique ? '<tspan class="er-uq">UQ</tspan>' : ''].filter(Boolean).join('<tspan> </tspan>');
    return `${rule}${badges ? `<text class="er-badge" x="12" y="${baseline}">${badges}</text>` : ''}<text class="er-column" x="${badges ? 62 : 42}" y="${baseline}">${esc(column.name)}</text><text class="er-type" x="${width - 15}" y="${baseline}">${esc(column.type)} · ${column.nullable ? 'NULL' : 'NN'}</text>`;
  }).join('');
  return `        <g class="er-entity" ${focusNodeAttrs(item.id, item.name, { kind: 'database', sublabel: `${item.columns.length} columns`, context: 'ER entity' }, diagram.meta.locale)}><g transform="translate(${x} ${y})"><title>${esc(`${item.name} · ${item.columns.length} columns`)}</title><rect class="body" width="${width}" height="${height}" rx="8"/><path class="head" d="M8 0H${width - 8}A8 8 0 0 1 ${width} 8V45H0V8A8 8 0 0 1 8 0Z"/><text class="er-name" data-node-label x="${width / 2}" y="29">${esc(item.name)}</text><line class="er-rule" x1="0" y1="45" x2="${width}" y2="45"/>${rows}</g></g>`;
}
const measured = [...boxes.values()];
const viewBox = diagram.meta.viewBox || [Math.ceil(Math.max(...measured.map((b) => b.x + b.width)) + 60), Math.ceil(Math.max(...measured.map((b) => b.y + b.height)) + 60)];
const definitions = `<defs><style>.er-entity .body{fill:var(--mask);stroke:var(--database-stroke);stroke-width:2}.er-entity .head{fill:var(--database-fill)}.er-rule{stroke:var(--grid)}.er-name{fill:var(--text);font-size:16px;font-weight:700;text-anchor:middle}.er-column{fill:var(--text);font-size:11px}.er-type{fill:var(--text-muted);font-size:10px;text-anchor:end}.er-badge{font-size:9px;font-weight:700}.er-pk{fill:var(--security-stroke)}.er-fk{fill:var(--backend-stroke)}.er-uq{fill:var(--cloud-stroke)}.er-edge{fill:none;stroke:var(--arrow);stroke-width:2}.er-edge.identifying{stroke-width:3}.er-edge.non-identifying{stroke-dasharray:7 5}.er-cardinality{fill:var(--mask);stroke:var(--arrow);stroke-width:1.7}</style><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" class="c-grid" stroke-width=".5"/></pattern><marker id="cf-one" viewBox="0 0 16 18" refX="15" refY="9" markerWidth="13" markerHeight="15" orient="auto-start-reverse"><path d="M11 2V16M15 2V16" fill="none" stroke="var(--arrow)" stroke-width="1.7"/></marker><marker id="cf-zero-or-many" viewBox="0 0 24 22" refX="23" refY="11" markerWidth="20" markerHeight="18" orient="auto-start-reverse"><circle class="er-cardinality" cx="5" cy="11" r="4"/><path d="M10 11L22 2M10 11L22 11M10 11L22 20" fill="none" stroke="var(--arrow)" stroke-width="1.7"/></marker><marker id="cf-one-or-many" viewBox="0 0 24 22" refX="23" refY="11" markerWidth="20" markerHeight="18" orient="auto-start-reverse"><path d="M5 3V19M10 11L22 2M10 11L22 11M10 11L22 20" fill="none" stroke="var(--arrow)" stroke-width="1.7"/></marker><marker id="cf-zero-or-one" viewBox="0 0 23 20" refX="22" refY="10" markerWidth="19" markerHeight="17" orient="auto-start-reverse"><circle class="er-cardinality" cx="5" cy="10" r="4"/><path d="M14 2V18M19 2V18" fill="none" stroke="var(--arrow)" stroke-width="1.7"/></marker></defs>`;
const svg = `      <svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}" ${svgRootAttrs(diagram.meta)} data-diagram-type="er" data-focus-camera="node">\n${svgAccessibleText(diagram.meta, 'er')}\n        ${definitions}\n        <rect width="100%" height="100%" fill="url(#grid)"/>\n${diagram.relationships.map(renderRelation).join('\n')}\n${measured.map(renderNode).join('\n')}\n      </svg>`;
writeDiagram({ outPath, template, diagramType: 'er', meta: diagram.meta, svg, cards: diagram.cards });
