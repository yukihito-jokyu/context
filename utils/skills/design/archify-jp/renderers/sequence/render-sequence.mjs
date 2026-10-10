import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { esc, renderDefinitions, renderSemanticSigil, textUnits } from '../shared/utils.mjs';
import { animateAttr, focusEdgeAttrs, focusNodeAttrs, focusNodeTitle, loadDiagramWithBrandMarks, writeDiagram, svgAccessibleText, svgRootAttrs } from '../shared/cli.mjs';
import { throwDiagnosticProblems } from '../shared/diagnostics.mjs';
import { resolveLegend, renderLegend as renderResolvedLegend } from '../shared/legend.mjs';
import { componentFill, arrowClassMap, rectsOverlap, cleanFlowProblems, cleanCrossingProblems, cleanAmbiguousCorridorProblems, cleanBorderRunProblems, cleanRouteRhythmProblems, cleanLabelRouteClearanceProblems, routePointsValue, asArray, isFinitePoint } from '../shared/geometry.mjs';
import { availableNodeTextWidth, fittedNodeFontSize, minimumNodeTextWidth } from '../shared/text-fit.mjs';
import { brandLabelFitWidth, brandMetadataFor, brandTopRailProblem, renderBrandMark } from '../shared/brand-marks.mjs';
import { translateMessage as i18nText } from '../shared/i18n.mjs';

const participantTextFit = {
  sublabelPreferred: 7,
  sublabelMinimum: 6,
};

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { diagram: sequence, template, outPath } = await loadDiagramWithBrandMarks({
  rendererDir: __dirname,
  diagramType: 'sequence',
  defaultExample: 'cache-miss-request.sequence.json'
});

const viewBox = sequence.meta?.viewBox || [920, 760];
// The timeline scales with viewBox height: a taller viewBox gains message room,
// a shorter one shrinks the readable band (validated below) instead of clipping.
// `column_fit: "spread"` widens the lanes with the viewBox instead of keeping
// the fixed 108px gap, so a wide canvas gains column distance and label room
// rather than dead space on the right. The default stays "fixed" so existing
// diagrams keep their coordinates.
const columnFit = sequence.meta?.column_fit === 'spread' ? 'spread' : 'fixed';
const participantCount = Math.max(1, asArray(sequence.participants).length);
const sideMargin = 62;
const participantW = columnFit === 'spread'
  ? Math.max(86, Math.min(190, Math.round((viewBox[0] - sideMargin * 2) / participantCount) - 24))
  : 86;
const colGap = columnFit === 'spread' && participantCount > 1
  ? Math.max(108, (viewBox[0] - 40 - sideMargin - participantW) / (participantCount - 1))
  : 108;

const layout = {
  topY: 72,
  participantW,
  participantH: 54,
  lifelineTop: 142,
  lifelineBottom: viewBox[1] - 65,
  legendY: viewBox[1] - 54,
  leftX: columnFit === 'spread' ? sideMargin + participantW / 2 : sideMargin,
  colGap,
  labelH: 16
};

const participantBoxWidthNote = columnFit === 'spread'
  ? `このviewBox幅と${participantCount}人の参加者では、参加者ボックスは${participantW}pxです`
  : `meta.column_fitが"spread"でない限り、参加者ボックスは${participantW}pxに固定されます`;

const arrowClass = {
  ...arrowClassMap,
  return: ['a-default', 'arrowhead']
};

function participantX(index) {
  return layout.leftX + index * layout.colGap;
}

const participants = new Map(asArray(sequence.participants).map((participant, index) => [
  participant.id,
  {
    ...participant,
    index,
    cx: participantX(index),
    x: participantX(index) - layout.participantW / 2,
    y: layout.topY,
    width: layout.participantW,
    height: layout.participantH,
    cy: layout.topY + layout.participantH / 2
  }
]));

function messageGeometry(message) {
  const from = participants.get(message.from);
  const to = participants.get(message.to);
  if (!from || !to || typeof message.y !== 'number') return null;
  const direction = to.cx > from.cx ? 1 : -1;
  const start = from.cx + direction * 7;
  const end = to.cx - direction * 7;
  return { start, end, center: (start + end) / 2 };
}

function messageLabelBox(message, relationIndex = null) {
  const geometry = messageGeometry(message);
  if (!geometry) return null;
  const width = Math.max(34, textUnits(message.label) * 5.2 + 12);
  return {
    relation: message,
    relationIndex,
    label: message.label,
    x: geometry.center - width / 2,
    y: message.y - 20,
    width,
    height: layout.labelH,
  };
}

function messageRouteBox(message) {
  const geometry = messageGeometry(message);
  if (!geometry) return null;
  return {
    x: Math.min(geometry.start, geometry.end),
    y: message.y - 2,
    width: Math.abs(geometry.end - geometry.start),
    height: 4,
  };
}

const compositionFrames = asArray(sequence.segments).map((segment, index) => ({
  id: index,
  label: segment.label,
  kind: 'segment',
  x: 48,
  y: segment.from,
  width: viewBox[0] - 96,
  height: segment.to - segment.from,
  radius: 10,
}));

function messagePath(message) {
  return {
    points: participants.has(message.from) && participants.has(message.to)
      ? [[participants.get(message.from).cx, message.y], [participants.get(message.to).cx, message.y]]
      : []
  };
}

function validateSequence() {
  const problems = [];
  if (participants.size !== asArray(sequence.participants).length) problems.push('参加者のidは一意でなければなりません。');

  if (layout.lifelineBottom - layout.lifelineTop < 120) {
    problems.push(`viewBoxの高さ${viewBox[1]}ではタイムラインが120px未満になります。meta.viewBox[1]を${layout.lifelineTop + 120 + 65}以上に設定してください。`);
  }

  for (const participant of participants.values()) {
    const estLabelW = textUnits(participant.label) * 6.8;
    if (estLabelW > layout.participantW + 6) {
      problems.push(`ラベル「${participant.label}」（約${Math.round(estLabelW)}px）が${layout.participantW}pxの参加者ボックスより幅広くなっています。短くしてください。`);
    }
    const brandRailProblem = brandTopRailProblem(participant, layout.participantW, 8, '参加者');
    if (brandRailProblem) problems.push(brandRailProblem);
    // sublabel renders as a single unwrapped <text>; shrink-to-fit handles the
    // ordinary case, this rejects what it cannot rescue.
    if (participant.sublabel) {
      const availableTextW = availableNodeTextWidth(layout.participantW);
      const minimumW = minimumNodeTextWidth(participant.sublabel, participantTextFit.sublabelMinimum);
      if (minimumW > availableTextW) {
        problems.push(`サブラベル「${participant.sublabel}」は可読最小値${participantTextFit.sublabelMinimum}pxで約${Math.ceil(minimumW)}pxを必要としますが、参加者「${participant.id}」が提供する幅は${availableTextW}pxです。サブラベルを短くしてください（${participantBoxWidthNote}）。`);
      }
    }
  }

  for (const message of asArray(sequence.messages)) {
    if (!participants.has(message.from)) problems.push(`メッセージ「${message.label}」が不明なsource「${message.from}」を参照しています。`);
    if (!participants.has(message.to)) problems.push(`メッセージ「${message.label}」が不明なtarget「${message.to}」を参照しています。`);
    if (typeof message.y !== 'number') problems.push(`メッセージ「${message.label}」には数値のyが必要です。`);
    if (message.y < layout.lifelineTop + 18 || message.y > layout.lifelineBottom - 18) {
      problems.push(`メッセージ「${message.label}」が可読タイムラインの外にあります。yを${layout.lifelineTop + 18}から${layout.lifelineBottom - 18}の範囲に保ってください。`);
    }
    if (participants.has(message.from) && participants.has(message.to)) {
      const distance = Math.abs(participants.get(message.to).cx - participants.get(message.from).cx);
      if (distance < 60) problems.push(`メッセージ「${message.label}」の幅は${Math.round(distance)}px（最小60px）です。参加者間の列距離を広げてください。`);
    }
  }

  // Participant headers are opaque nodes. Lifelines, activation bars, and
  // segment bands remain intentional pass-through geometry and are excluded.
  problems.push(...cleanFlowProblems({
    relations: sequence.messages,
    obstacles: participants.values(),
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    obstacleKind: '参加者ヘッダー',
    clearance: 0,
    routeHint: 'メッセージのyを参加者ヘッダーより下へ移動するか、参加者を並べ替える'
  }));
  problems.push(...cleanCrossingProblems({
    relations: sequence.messages,
    endpointIds: new Set(participants.keys()),
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    profile: sequence.meta?.quality_profile,
    routeHint: 'メッセージのy値を離す。ライフラインとの交差は引き続き許可される'
  }));
  problems.push(...cleanAmbiguousCorridorProblems({
    relations: sequence.messages,
    endpointIds: new Set(participants.keys()),
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    profile: sequence.meta?.quality_profile,
    routeHint: '無関係なメッセージが視覚的に融合しないよう、メッセージのy値を離す'
  }));
  problems.push(...cleanBorderRunProblems({
    relations: sequence.messages,
    endpointIds: new Set(participants.keys()),
    frames: compositionFrames,
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    profile: sequence.meta?.quality_profile,
    routeHint: 'segment境界と垂直に交差するかsegment内に明確に収まるよう、メッセージのyを移動する'
  }));
  problems.push(...cleanRouteRhythmProblems({
    relations: sequence.messages,
    endpointIds: new Set(participants.keys()),
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    profile: sequence.meta?.quality_profile,
    routeHint: '各折れに可読な余白ができるよう、参加者間隔を広げるかメッセージ経路を単純化する'
  }));

  // Vertical crowding only matters when the arrows share horizontal space;
  // disjoint arrows may legitimately run in parallel rows.
  const placed = asArray(sequence.messages)
    .filter((m) => participants.has(m.from) && participants.has(m.to))
    .map((m) => ({
      label: m.label,
      y: m.y,
      x1: Math.min(participants.get(m.from).cx, participants.get(m.to).cx),
      x2: Math.max(participants.get(m.from).cx, participants.get(m.to).cx)
    }))
    .sort((a, b) => a.y - b.y);
  for (let i = 0; i < placed.length; i += 1) {
    for (let j = i + 1; j < placed.length && placed[j].y - placed[i].y < 28; j += 1) {
      if (placed[i].x1 < placed[j].x2 && placed[j].x1 < placed[i].x2) {
        problems.push(`メッセージ「${placed[i].label}」と「${placed[j].label}」は間隔が28px未満で、水平領域を共有しています。y値を離してください。`);
      }
    }
  }

  // Label masks can extend well past the arrow span, so check the actual
  // label rectangles too — tangent arrows with long labels still collide.
  const labelRects = asArray(sequence.messages)
    .map((m, messageIndex) => messageLabelBox(m, messageIndex))
    .filter(Boolean);
  for (let i = 0; i < labelRects.length; i += 1) {
    for (let j = i + 1; j < labelRects.length; j += 1) {
      if (rectsOverlap(labelRects[i], labelRects[j], -2)) {
        problems.push(`ラベル「${labelRects[i].label}」と「${labelRects[j].label}」が重なっています。メッセージのy値を離すか、ラベルを短くしてください。`);
      }
    }
  }
  problems.push(...cleanLabelRouteClearanceProblems({
    relations: sequence.messages,
    labels: labelRects,
    endpointIds: new Set(participants.keys()),
    pathFor: messagePath,
    diagramType: 'sequence',
    relationCollection: 'messages',
    profile: sequence.meta?.quality_profile,
    routeHint: '隣接する経路が見えるよう、メッセージのy値を離す、ラベルを短くする、または参加者を並べ替える'
  }));

  for (const segment of asArray(sequence.segments)) {
    if (segment.to <= segment.from) {
      problems.push(`segment「${segment.label}」のy範囲（from ${segment.from}からto ${segment.to}）が無効です。"to"は"from"より大きくなければなりません。`);
    }
    if (segment.from < layout.topY || segment.to > layout.lifelineBottom + 20) {
      problems.push(`segment「${segment.label}」がキャンバスの外へはみ出しています。y範囲を${layout.topY}から${layout.lifelineBottom + 20}の間に保ってください。`);
    }
  }

  for (const activation of asArray(sequence.activations)) {
    if (!participants.has(activation.participant)) problems.push(`activationが不明な参加者「${activation.participant}」を参照しています。`);
    if (activation.to <= activation.from) problems.push(`「${activation.participant}」のactivationの時間範囲が無効です。"to"は"from"より大きくなければなりません。`);
  }

  const lastParticipant = asArray(sequence.participants)[asArray(sequence.participants).length - 1];
  if (lastParticipant && participants.get(lastParticipant.id).cx + layout.participantW / 2 > viewBox[0] - 40) {
    const requiredWidth = Math.ceil(participants.get(lastParticipant.id).cx + layout.participantW / 2 + 40);
    problems.push(`参加者がviewBoxの幅を超えています。meta.viewBox[0]を${requiredWidth}以上に設定するか、参加者を削除してください。`);
  }

  if (problems.length) {
    throwDiagnosticProblems('シーケンスのレイアウト検証に失敗しました', problems, {
      subject: { diagramType: 'sequence' },
    });
  }
}

function renderParticipant(participant) {
  const fill = componentFill[participant.type] || 'c-external';
  const hasSub = participant.sublabel != null && participant.sublabel !== '';
  const sub = hasSub
    ? `\n          <text data-detail="context" x="${participant.cx}" y="${layout.topY + 39}" class="t-muted" font-size="${fittedNodeFontSize(participant.sublabel, layout.participantW, participantTextFit.sublabelPreferred, participantTextFit.sublabelMinimum)}" text-anchor="middle">${esc(participant.sublabel)}</text>`
    : '';
  const brand = renderBrandMark(participant, { x: participant.x + layout.participantW - 22, y: layout.topY + 6 });
  const labelFontSize = fittedNodeFontSize(participant.label, brandLabelFitWidth(participant, layout.participantW), 11, 8);
  const passport = {
    kind: participant.type,
    sublabel: participant.sublabel,
    context: i18nText(sequence.meta.locale, 'node.context.sequence'),
    ...brandMetadataFor(participant),
  };
  return `        <g ${focusNodeAttrs(participant.id, participant.label, passport, sequence.meta.locale)}>
          ${focusNodeTitle(participant.label, passport)}
          <rect x="${participant.x}" y="${layout.topY}" width="${layout.participantW}" height="${layout.participantH}" rx="6" class="c-mask"/>
          <rect x="${participant.x}" y="${layout.topY}" width="${layout.participantW}" height="${layout.participantH}" rx="6" class="${fill}"${animateAttr(sequence.meta, 'node', participant.index)} stroke-width="1.5"/>
          ${renderSemanticSigil(participant.type, { x: participant.x + 6, y: layout.topY + 6 })}${brand ? `\n          ${brand}` : ''}
          <text data-node-label=""${hasSub ? ' data-detail-anchor=""' : ''} x="${participant.cx}" y="${layout.topY + 22}" class="t-primary" font-size="${labelFontSize}" font-weight="600" text-anchor="middle">${esc(participant.label)}</text>${sub}
        </g>`;
}

function renderLifeline(participant) {
  return `        <path d="M ${participant.cx} ${layout.lifelineTop} L ${participant.cx} ${layout.lifelineBottom}" class="a-default" stroke-width="0.8" stroke-dasharray="3,7"/>`;
}

function renderSegment(segment, index) {
  return `        <rect data-graph-role="structural-frame" data-composition-frame-kind="segment" data-composition-frame-id="${index}" x="48" y="${segment.from}" width="${viewBox[0] - 96}" height="${segment.to - segment.from}" rx="10" class="c-lane" stroke-width="1"/>`;
}

function renderSegmentLabel(segment, index) {
  const labelW = Math.max(42, textUnits(segment.label) * 5.2 + 14);
  const occupied = asArray(sequence.messages)
    .flatMap((message) => [messageLabelBox(message), messageRouteBox(message)])
    .filter(Boolean);
  const label = { x: 56, y: segment.from - 22, width: labelW, height: 18 };
  for (let attempt = 0; attempt < 4; attempt += 1) {
    if (!occupied.some((rect) => rectsOverlap(label, rect, 2))) break;
    label.y -= 22;
  }
  return `        <g data-graph-role="segment-label" data-segment-id="${index}">
          <rect x="${label.x}" y="${label.y}" width="${label.width}" height="${label.height}" rx="3" class="c-mask"/>
          <text x="${label.x + 6}" y="${label.y + 13}" class="t-dim" font-size="9" font-weight="600">${esc(segment.label)}</text>
        </g>`;
}

function renderActivation(activation) {
  const participant = participants.get(activation.participant);
  const fill = componentFill[activation.type] || componentFill[participant.type] || 'c-external';
  const x = participant.cx - 5;
  const height = activation.to - activation.from;
  return `        <rect x="${x}" y="${activation.from}" width="10" height="${height}" rx="3" class="c-mask"/>
        <rect x="${x}" y="${activation.from}" width="10" height="${height}" rx="3" class="${fill}" stroke-width="1"/>`;
}

function messageLabel(message, x1, x2) {
  const box = messageLabelBox(message);
  const center = box ? box.x + box.width / 2 : (x1 + x2) / 2;
  const y = message.y - 10;
  const labelW = box?.width || Math.max(34, textUnits(message.label) * 5.2 + 12);
  const accent = message.variant === 'security'
    ? 't-security'
    : message.variant === 'dashed'
      ? 't-messagebus'
      : message.variant === 'return'
        ? 't-muted'
        : 't-backend';
  return `        <g data-detail="context">
          <rect x="${center - labelW / 2}" y="${y - 10}" width="${labelW}" height="${layout.labelH}" rx="3" class="c-mask"/>
          <text x="${center}" y="${y}" class="${accent}" font-size="9" text-anchor="middle">${esc(message.label)}</text>
        </g>`;
}

function renderMessage(message, index) {
  const { start, end } = messageGeometry(message);
  const [cls, marker] = arrowClass[message.variant || 'default'] || arrowClass.default;
  const strokeWidth = message.variant === 'emphasis' ? 1.8 : 1.4;
  const dash = message.variant === 'return' ? ' stroke-dasharray="3,5"' : '';
  const note = message.note
    ? `\n        <text data-detail="fine" x="${Math.min(start, end) + 12}" y="${message.y + 18}" class="t-dim" font-size="7">${esc(message.note)}</text>`
    : '';
  return `        <g ${focusEdgeAttrs(message.from, message.to, message.label, index, message.id)}>
          <path data-composition-edge-from="${esc(message.from)}" data-composition-edge-to="${esc(message.to)}"${message.id ? ` data-composition-edge-id="${esc(message.id)}"` : ''} data-composition-points="${routePointsValue([[start, message.y], [end, message.y]])}" d="M ${start} ${message.y} L ${end} ${message.y}" class="${cls}"${animateAttr(sequence.meta, 'edge', index)} stroke-width="${strokeWidth}"${dash} marker-end="url(#${marker})"/>
${messageLabel(message, start, end)}${note}
        </g>`;
}

const LEGEND_CATALOG = [
  { kind: 'emphasis', className: 'a-emphasis', marker: 'arrowhead-emphasis', strokeWidth: 1.8 },
  { kind: 'return', className: 'a-default', marker: 'arrowhead', dash: '3,5' },
  { kind: 'security', className: 'a-security', marker: 'arrowhead-security' },
  { kind: 'dashed', className: 'a-dashed', marker: 'arrowhead-dashed' },
  { kind: 'default', className: 'a-default', marker: 'arrowhead' },
].map((entry) => ({
  ...entry,
  interactive: false,
  swatchWidth: 34,
  swatchGap: 9,
  label: i18nText(sequence.meta.locale, `legend.sequence.${entry.kind}`),
}));

function renderLegend() {
  const presentKinds = new Set(asArray(sequence.messages).map((message) => message.variant || 'default'));
  const entries = resolveLegend(sequence.meta?.legend, LEGEND_CATALOG, presentKinds);
  return renderResolvedLegend({
    entries,
    locale: sequence.meta.locale,
    layout: {
      x: 40,
      baselineY: layout.legendY,
      width: viewBox[0] - 80,
      minTitleY: layout.legendY - 30,
      unfit: sequence.meta?.legend === undefined ? 'hide' : 'error',
      diagramType: 'sequence',
    },
    renderSwatch: (entry) => `<path d="M ${entry.x} ${entry.baseline - 3} L ${entry.x + 34} ${entry.baseline - 3}" class="${entry.className}" stroke-width="${entry.strokeWidth || 1.4}"${entry.dash ? ` stroke-dasharray="${entry.dash}"` : ''} marker-end="url(#${entry.marker})"/>`,
  });
}

function renderSvg() {
  const participantList = [...participants.values()];
  return `      <svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}" ${svgRootAttrs(sequence.meta)}>
${svgAccessibleText(sequence.meta, 'sequence')}
${renderDefinitions()}

        <!-- Background Grid -->
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- Time Segments -->
${asArray(sequence.segments).map(renderSegment).join('\n\n')}

        <!-- Lifelines -->
${participantList.map(renderLifeline).join('\n')}

        <!-- Activations -->
${asArray(sequence.activations).map(renderActivation).join('\n')}

        <!-- Messages -->
${asArray(sequence.messages).map(renderMessage).join('\n\n')}

        <!-- Segment Labels -->
${asArray(sequence.segments).map(renderSegmentLabel).join('\n')}

        <!-- Participants -->
${participantList.map(renderParticipant).join('\n\n')}

        <!-- Legend -->
${renderLegend()}
      </svg>`;
}

validateSequence();
writeDiagram({
  outPath,
  template,
  diagramType: 'sequence',
  meta: sequence.meta,
  svg: renderSvg(),
  cards: sequence.cards,
});
