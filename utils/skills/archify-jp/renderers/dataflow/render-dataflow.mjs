import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { esc, renderDefinitions, renderSemanticSigil, textUnits } from '../shared/utils.mjs';
import { animateAttr, focusEdgeAttrs, focusNodeAttrs, focusNodeTitle, loadDiagramWithBrandMarks, writeDiagram, svgAccessibleText, svgRootAttrs } from '../shared/cli.mjs';
import { throwDiagnosticProblems } from '../shared/diagnostics.mjs';
import { resolveLegend, renderLegend as renderResolvedLegend } from '../shared/legend.mjs';
import { availableNodeTextWidth, fittedNodeFontSize, minimumNodeTextWidth } from '../shared/text-fit.mjs';
import { brandLabelFitWidth, brandMetadataFor, brandTopRailProblem, renderBrandMark } from '../shared/brand-marks.mjs';
import { translateMessage as i18nText } from '../shared/i18n.mjs';
import {
  asArray,
  isFinitePoint,
  rectsOverlap,
  cleanEndpointSideProblems,
  cleanFlowProblems,
  cleanCrossingProblems,
  cleanAmbiguousCorridorProblems,
  cleanBorderRunProblems,
  cleanRouteRhythmProblems,
  cleanLabelRouteClearanceProblems,
  suggestLabelObstacleFix,
  suggestLabelPairFix,
  anchor,
  automaticPortSpread,
  defaultFromSide,
  defaultToSide,
  chosenSide,
  polylinePath,
  routePointsValue,
  labelPoint,
  componentFill,
  componentText,
  arrowClassMap,
  variantAccent
} from '../shared/geometry.mjs';

const nodeTextFit = {
  sublabelPreferred: 7,
  sublabelMinimum: 6,
  tagPreferred: 7,
  tagMinimum: 6,
};

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { diagram: dataflow, template, outPath } = await loadDiagramWithBrandMarks({
  rendererDir: __dirname,
  diagramType: 'dataflow',
  defaultExample: 'product-analytics.dataflow.json'
});

const viewBox = dataflow.meta?.viewBox || [940, 720];
const layout = {
  stageY: 46,
  stageH: 36,
  stageBottomPad: 74,
  leftX: 100,
  colGap: 215,
  stageW: 168,
  nodeW: 112,
  nodeH: 58,
  rowYs: [128, 242, 356, 470, 584],
  labelH: 16
};

function flowLabelSize(flow) {
  const longestLine = Math.max(textUnits(flow.label), textUnits(flow.classification || ''));
  return {
    width: Math.round(Math.max(34, longestLine * 4.9 + 12) * 10) / 10,
    height: flow.classification ? 27 : layout.labelH,
  };
}

function stageX(index) {
  return layout.leftX + index * layout.colGap;
}

function stageFrame(stage, index) {
  return {
    id: index,
    label: stage.label,
    kind: 'stage',
    x: stageX(index) - layout.stageW / 2,
    y: layout.stageY,
    width: layout.stageW,
    height: viewBox[1] - layout.stageY - layout.stageBottomPad,
    radius: 10,
  };
}

const compositionFrames = asArray(dataflow.stages).map(stageFrame);

function measureNode(node) {
  const width = node.width || layout.nodeW;
  const height = node.height || layout.nodeH;
  const cx = stageX(node.stage);
  const y = layout.rowYs[node.row] + (node.yOffset || 0);
  return {
    ...node,
    width,
    height,
    cx,
    cy: y + height / 2,
    x: cx - width / 2,
    y
  };
}

const nodes = new Map(asArray(dataflow.nodes).map((node) => [node.id, measureNode(node)]));
const nodeSteps = new Map();
for (const [index, flow] of asArray(dataflow.flows).entries()) {
  if (!nodeSteps.has(flow.from)) nodeSteps.set(flow.from, index);
  if (!nodeSteps.has(flow.to)) nodeSteps.set(flow.to, index + 1);
}
for (const [index, node] of asArray(dataflow.nodes).entries()) {
  if (!nodeSteps.has(node.id)) nodeSteps.set(node.id, index);
}

function validateDataflow() {
  const problems = [];
  if (nodes.size !== asArray(dataflow.nodes).length) problems.push('ノードの id は一意である必要があります。');

  const stageCount = asArray(dataflow.stages).length;
  for (const node of nodes.values()) {
    if (typeof node.stage !== 'number' || node.stage < 0 || node.stage >= stageCount) {
      problems.push(`ノード "${node.id}" の stage ${node.stage} は無効です。有効範囲は 0..${stageCount - 1} です。`);
    }
    if (typeof node.row !== 'number' || node.row < 0 || node.row >= layout.rowYs.length) {
      problems.push(`ノード "${node.id}" の row ${node.row} は無効です。有効範囲は 0..${layout.rowYs.length - 1} です。`);
    }
    if (!isFinitePoint(node.x, node.y, node.cx, node.cy)) {
      problems.push(`ノード "${node.id}" の座標が有限値ではありません。stage、row、width、height、yOffset が数値であることを確認してください。`);
      continue;
    }
    if (node.x < 24 || node.x + node.width > viewBox[0] - 24) {
      problems.push(`ノード "${node.id}" が viewBox の水平方向の範囲を超えています。node.width を減らすか meta.viewBox[0] を増やしてください。`);
    }
    if (node.y < layout.stageY + layout.stageH + 22 || node.y + node.height > viewBox[1] - layout.stageBottomPad) {
      problems.push(`ノード "${node.id}" が図の可読領域を超えています。y を ${layout.stageY + layout.stageH + 22} から ${viewBox[1] - layout.stageBottomPad} の間に収めてください（row/yOffset を調整するか meta.viewBox[1] を増やしてください）。`);
    }
    const estLabelW = textUnits(node.label) * 6.2;
    if (estLabelW > node.width + 6) {
      problems.push(`ラベル "${node.label}"（約 ${Math.round(estLabelW)}px）がノード "${node.id}"（${node.width}px）より広くなっています。ラベルを短くするか node.width を増やしてください。`);
    }
    const brandRailProblem = brandTopRailProblem(node, node.width, 8);
    if (brandRailProblem) problems.push(brandRailProblem);
    // sublabel and tag render as single unwrapped <text> elements; shrink-to-fit
    // handles the ordinary case, this rejects what it cannot rescue.
    const availableTextW = availableNodeTextWidth(node.width);
    for (const [field, value, minimum] of [
      ['サブラベル', node.sublabel, nodeTextFit.sublabelMinimum],
      ['タグ', node.tag, nodeTextFit.tagMinimum],
    ]) {
      if (!value) continue;
      const minimumW = minimumNodeTextWidth(value, minimum);
      if (minimumW > availableTextW) {
        problems.push(`${field} "${value}" は可読性を保つ最小値 ${minimum}px で約 ${Math.ceil(minimumW)}px 必要ですが、ノード "${node.id}" には ${availableTextW}px しかありません。${field.toLowerCase()} を短くするか node.width を増やしてください。`);
      }
    }
  }

  const nodeList = asArray(dataflow.nodes);
  for (let i = 0; i < nodeList.length; i += 1) {
    for (let j = i + 1; j < nodeList.length; j += 1) {
      const a = nodes.get(nodeList[i].id);
      const b = nodes.get(nodeList[j].id);
      if (rectsOverlap(a, b, 10)) {
        problems.push(`ノード "${a.id}" と "${b.id}" の間隔が 10px 未満です。一方を別の stage/row へ移動するか yOffset を調整してください。`);
      }
    }
  }

  for (const flow of asArray(dataflow.flows)) {
    if (!nodes.has(flow.from)) problems.push(`フロー "${flow.label || flow.from}" が不明な接続元 "${flow.from}" を参照しています。`);
    if (!nodes.has(flow.to)) problems.push(`フロー "${flow.label || flow.to}" が不明な接続先 "${flow.to}" を参照しています。`);
    if (!flow.label) problems.push(`フロー "${flow.from}" -> "${flow.to}" には短いデータラベルが必要です。`);
    if (nodes.has(flow.from) && nodes.has(flow.to)) {
      const routed = pathFor(flow);
      const [start, end] = [routed.points[0], routed.points[routed.points.length - 1]];
      const distance = Math.hypot(end[0] - start[0], end[1] - start[1]);
      if (distance < 34) problems.push(`フロー "${flow.label}" が短すぎます（${Math.round(distance)}px、最小 34px）。チャネルを経由させるか、ノード同士を離してください。`);
      if (Array.isArray(flow.via)) {
        for (let segmentIndex = 0; segmentIndex < routed.points.length - 1; segmentIndex += 1) {
          const segmentStart = routed.points[segmentIndex];
          const segmentEnd = routed.points[segmentIndex + 1];
          const isDiagonal = Math.abs(segmentStart[0] - segmentEnd[0]) > 0.01
            && Math.abs(segmentStart[1] - segmentEnd[1]) > 0.01;
          if (!isDiagonal) continue;
          const viaIndex = Math.min(segmentIndex, flow.via.length - 1);
          problems.push(`フロー "${flow.label}" に (${segmentStart.join(', ')}) から (${segmentEnd.join(', ')}) への斜めのセグメントがあります。同じ x または y 座標を使い、via[${viaIndex}] を隣接点に揃えてください。`);
        }
      }
    }
  }

  problems.push(...cleanEndpointSideProblems({
    relations: dataflow.flows,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    fromSideFor: (flow) => flowSides(flow).fromSide,
    toSideFor: (flow) => flowSides(flow).toSide,
    routeHint: '自動ルーティングを維持するか、最初と最後のセグメントがノード境界を垂直に横切る fromSide/toSide と via 点を選ぶ',
  }));
  problems.push(...cleanFlowProblems({
    relations: dataflow.flows,
    obstacles: nodes.values(),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    obstacleKind: 'node',
    routeHint: 'fromSide/toSide を調整するか、route/via または channelX/channelY を設定するか、ノードを別の stage/row へ移動する'
  }));
  problems.push(...cleanCrossingProblems({
    relations: dataflow.flows,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    profile: dataflow.meta?.quality_profile,
    routeHint: 'フローが別々のステージ間経路帯を使用するよう route/via または channelX/channelY を調整する'
  }));
  problems.push(...cleanAmbiguousCorridorProblems({
    relations: dataflow.flows,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    profile: dataflow.meta?.quality_profile,
    routeHint: '無関係なフローが視覚的に合流しないよう route/via または channelX/channelY を調整する'
  }));
  problems.push(...cleanBorderRunProblems({
    relations: dataflow.flows,
    endpointIds: new Set(nodes.keys()),
    frames: compositionFrames,
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    profile: dataflow.meta?.quality_profile,
    routeHint: 'フローがステージ境界に沿わず垂直に横切るよう route/via または channelX/channelY を調整する'
  }));
  problems.push(...cleanRouteRhythmProblems({
    relations: dataflow.flows,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    profile: dataflow.meta?.quality_profile,
    routeHint: '各曲がり角が明確なステージ間経路帯を使用するよう route/via または channelX/channelY を調整する'
  }));

  const labelRects = [];
  for (const [flowIndex, flow] of asArray(dataflow.flows).entries()) {
    if (!flow.label || !nodes.has(flow.from) || !nodes.has(flow.to)) continue;
    const [lx, ly] = labelPoint(flow, pathFor(flow).points);
    const { width, height } = flowLabelSize(flow);
    labelRects.push({ relation: flow, relationIndex: flowIndex, label: flow.label, x: lx - width / 2, y: ly - 11, width, height, lx, ly });
  }
  for (const rect of labelRects) {
    for (const node of nodes.values()) {
      if (rectsOverlap(rect, node, -2)) {
        problems.push(`ラベル "${rect.label}" がノード "${node.id}" と重なっています。labelDx/labelDy/labelSegment を調整するか labelAt を設定してください。\n${suggestLabelObstacleFix(rect, rect.lx, rect.ly, node, 'node')}`);
      }
    }
  }
  for (let i = 0; i < labelRects.length; i += 1) {
    for (let j = i + 1; j < labelRects.length; j += 1) {
      if (rectsOverlap(labelRects[i], labelRects[j], -2)) {
        problems.push(`ラベル "${labelRects[i].label}" と "${labelRects[j].label}" が重なっています。labelDx/labelDy を調整してください。\n${suggestLabelPairFix(labelRects[i], labelRects[j])}`);
      }
    }
  }
  problems.push(...cleanLabelRouteClearanceProblems({
    relations: dataflow.flows,
    labels: labelRects,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'dataflow',
    relationCollection: 'flows',
    profile: dataflow.meta?.quality_profile,
    routeHint: 'labelAt、labelDx、labelDy、または labelSegment を調整する。それでも解消しない場合は、もう一方のフローの route/via/channelX/channelY を調整する'
  }));

  const lastStageX = stageX(asArray(dataflow.stages).length - 1);
  if (lastStageX + layout.stageW / 2 > viewBox[0] - 24) {
    problems.push(`ステージが viewBox の幅を超えています。meta.viewBox[0] を ${Math.ceil(lastStageX + layout.stageW / 2 + 24)} 以上に設定してください。`);
  }

  if (problems.length) {
    throwDiagnosticProblems('データフローのレイアウト検証に失敗しました', problems, {
      subject: { diagramType: 'dataflow' },
    });
  }
}

function routeVia(flow, from, to, start, end) {
  if (flow.via) return flow.via;
  switch (flow.route || 'auto') {
    case 'straight':
      return [];
    case 'vertical-channel': {
      const x = flow.channelX ?? start[0] + (end[0] > start[0] ? 44 : -44);
      return [[x, start[1]], [x, end[1]]];
    }
    case 'bottom-channel': {
      const y = flow.channelY ?? Math.max(from.y + from.height, to.y + to.height) + 26;
      return [[start[0], y], [end[0], y]];
    }
    case 'top-channel': {
      const y = flow.channelY ?? Math.min(from.y, to.y) - 24;
      return [[start[0], y], [end[0], y]];
    }
    case 'auto':
    default: {
      if (Math.abs(start[1] - end[1]) < 4) return [];
      const midX = start[0] + (end[0] - start[0]) / 2;
      return [[midX, start[1]], [midX, end[1]]];
    }
  }
}

const pathCache = new Map();

function flowSides(flow) {
  const from = nodes.get(flow.from);
  const to = nodes.get(flow.to);
  return {
    fromSide: chosenSide(flow.fromSide, defaultFromSide(from, to)),
    toSide: chosenSide(flow.toSide, defaultToSide(from, to)),
  };
}

const automaticPorts = automaticPortSpread(dataflow.flows, nodes, {
  sideFor: (flow, endpoint) => flowSides(flow)[endpoint === 'source' ? 'fromSide' : 'toSide'],
});

function pathFor(flow) {
  if (pathCache.has(flow)) return pathCache.get(flow);
  const from = nodes.get(flow.from);
  const to = nodes.get(flow.to);
  const ports = automaticPorts.get(flow);
  const { fromSide, toSide } = flowSides(flow);
  const start = ports?.from || anchor(from, fromSide);
  const end = ports?.to || anchor(to, toSide);
  // Drop consecutive duplicate points so a purely vertical (or horizontal)
  // auto-route never emits a zero-length final segment — SVG derives
  // marker-end orientation from the last segment, and a degenerate segment
  // leaves the arrowhead angle undefined (see #169).
  const rawPoints = [start, ...routeVia(flow, from, to, start, end), end];
  const points = [];
  for (const p of rawPoints) {
    const prev = points.at(-1);
    if (!prev || Math.abs(p[0] - prev[0]) > 0.0001 || Math.abs(p[1] - prev[1]) > 0.0001) {
      points.push(p);
    }
  }
  // Guard against an all-degenerate route (e.g. start === end): keep both
  // endpoints so the path is still well-formed even if the marker is hidden.
  if (points.length < 2) points.push(end);
  const routed = { d: polylinePath(points), points };
  pathCache.set(flow, routed);
  return routed;
}

function renderStage(stage, index) {
  const frame = compositionFrames[index];
  const cx = stageX(index);
  return `        <rect data-graph-role="structural-frame" data-composition-frame-kind="stage" data-composition-frame-id="${index}" x="${frame.x}" y="${frame.y}" width="${frame.width}" height="${frame.height}" rx="${frame.radius}" class="c-lane" stroke-width="1"/>
        <text x="${cx}" y="${layout.stageY + 22}" class="t-dim" font-size="9" font-weight="600" text-anchor="middle">${String(index + 1).padStart(2, '0')} / ${esc(stage.label)}</text>`;
}

function renderNode(node) {
  const fill = componentFill[node.type] || 'c-external';
  const accent = componentText[node.type] || 't-muted';
  const hasSub = node.sublabel != null && node.sublabel !== '';
  const sub = hasSub
    ? `\n          <text data-detail="context" x="${node.cx}" y="${node.y + 37}" class="t-muted" font-size="${fittedNodeFontSize(node.sublabel, node.width, nodeTextFit.sublabelPreferred, nodeTextFit.sublabelMinimum)}" text-anchor="middle">${esc(node.sublabel)}</text>`
    : '';
  const tag = node.tag
    ? `\n        <text data-detail="fine" x="${node.cx}" y="${node.y + node.height - 11}" class="${accent}" font-size="${fittedNodeFontSize(node.tag, node.width, nodeTextFit.tagPreferred, nodeTextFit.tagMinimum)}" text-anchor="middle">${esc(node.tag)}</text>`
    : '';
  const stage = asArray(dataflow.stages)[node.stage];
  const context = stage
    ? `${String(node.stage + 1).padStart(2, '0')} / ${stage.label}`
    : i18nText(dataflow.meta.locale, 'node.context.dataflow');
  const brand = renderBrandMark(node, { x: node.x + node.width - 22, y: node.y + 6 });
  const labelFontSize = fittedNodeFontSize(node.label, brandLabelFitWidth(node, node.width), 10, 8);
  const passport = { kind: node.type, sublabel: node.sublabel, tag: node.tag, context, ...brandMetadataFor(node) };
  return `        <g ${focusNodeAttrs(node.id, node.label, passport, dataflow.meta.locale)}>
          ${focusNodeTitle(node.label, passport)}
          <rect x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" rx="6" class="c-mask"/>
          <rect x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" rx="6" class="${fill}"${animateAttr(dataflow.meta, 'node', nodeSteps.get(node.id))} stroke-width="1.5"/>
          ${renderSemanticSigil(node.type, { x: node.x + 6, y: node.y + 6 })}${brand ? `\n          ${brand}` : ''}
          <text data-node-label=""${hasSub ? ' data-detail-anchor=""' : ''} x="${node.cx}" y="${node.y + 21}" class="t-primary" font-size="${labelFontSize}" font-weight="600" text-anchor="middle">${esc(node.label)}</text>${sub}${tag}
        </g>`;
}

function renderFlowPath(flow, index) {
  const [cls, marker] = arrowClassMap[flow.variant || 'default'] || arrowClassMap.default;
  const routed = pathFor(flow);
  const strokeWidth = flow.width || (flow.variant === 'emphasis' ? 1.8 : 1.4);
  return `        <path ${focusEdgeAttrs(flow.from, flow.to, flow.label, index, flow.id)} data-composition-points="${routePointsValue(routed.points)}" d="${routed.d}" class="${cls}"${animateAttr(dataflow.meta, 'edge', index)} stroke-width="${strokeWidth}" marker-end="url(#${marker})"/>`;
}

function renderFlowLabel(flow, index) {
  const routed = pathFor(flow);
  const [lx, ly] = labelPoint(flow, routed.points);
  const { width: labelW, height: labelH } = flowLabelSize(flow);
  const classification = flow.classification
    ? `\n        <text data-detail="fine" x="${lx}" y="${ly + 11}" class="t-dim" font-size="7" text-anchor="middle">${esc(flow.classification)}</text>`
    : '';
  return `        <g data-detail="context" ${focusEdgeAttrs(flow.from, flow.to, flow.label, index, flow.id)}>
          <rect x="${lx - labelW / 2}" y="${ly - 11}" width="${labelW}" height="${labelH}" rx="4" class="c-mask"/>
          <text x="${lx}" y="${ly}" class="${variantAccent(flow.variant)}" font-size="8" text-anchor="middle">${esc(flow.label)}</text>${classification}
        </g>`;
}

const LEGEND_CATALOG = [
  { kind: 'emphasis', className: 'a-emphasis', marker: 'arrowhead-emphasis', strokeWidth: 1.8, swatchWidth: 34, swatchGap: 9, interactive: false },
  { kind: 'security', className: 'a-security', marker: 'arrowhead-security', swatchWidth: 34, swatchGap: 9, interactive: false },
  { kind: 'dashed', className: 'a-dashed', marker: 'arrowhead-dashed', swatchWidth: 34, swatchGap: 9, interactive: false },
  { kind: 'database' },
  { kind: 'default', className: 'a-default', marker: 'arrowhead', swatchWidth: 34, swatchGap: 9, interactive: false },
].map((entry) => ({
  ...entry,
  label: i18nText(dataflow.meta.locale, `legend.dataflow.${entry.kind}`),
}));

function renderLegend() {
  const presentKinds = new Set(asArray(dataflow.flows).map((flow) => flow.variant || 'default'));
  if ([...nodes.values()].some((node) => node.type === 'database')) presentKinds.add('database');
  const entries = resolveLegend(dataflow.meta?.legend, LEGEND_CATALOG, presentKinds);
  return renderResolvedLegend({
    entries,
    locale: dataflow.meta.locale,
    layout: {
      x: 40,
      baselineY: viewBox[1] - 36,
      width: viewBox[0] - 80,
      minTitleY: viewBox[1] - 66,
      unfit: dataflow.meta?.legend === undefined ? 'hide' : 'error',
      diagramType: 'dataflow',
    },
    renderSwatch: (entry) => entry.kind === 'database'
      ? `<rect x="${entry.x}" y="${entry.baseline - 8}" width="14" height="9" rx="2" class="c-database" stroke-width="1"/>`
      : `<path d="M ${entry.x} ${entry.baseline - 3} L ${entry.x + 34} ${entry.baseline - 3}" class="${entry.className}" stroke-width="${entry.strokeWidth || 1.4}" marker-end="url(#${entry.marker})"/>`,
  });
}

function renderSvg() {
  return `      <svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}" ${svgRootAttrs(dataflow.meta)}>
${svgAccessibleText(dataflow.meta, 'dataflow')}
${renderDefinitions()}

        <!-- Background Grid -->
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- Data Stages -->
${dataflow.stages.map(renderStage).join('\n\n')}

        <!-- Flow paths -->
${asArray(dataflow.flows).map(renderFlowPath).join('\n')}

        <!-- Nodes -->
${[...nodes.values()].map(renderNode).join('\n\n')}

        <!-- Flow labels -->
${asArray(dataflow.flows).map(renderFlowLabel).join('\n')}

        <!-- Legend -->
${renderLegend()}
      </svg>`;
}

validateDataflow();
writeDiagram({
  outPath,
  template,
  diagramType: 'dataflow',
  meta: dataflow.meta,
  svg: renderSvg(),
  cards: dataflow.cards,
});
