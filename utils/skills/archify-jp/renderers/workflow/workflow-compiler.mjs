import { esc, renderDefinitions, renderSemanticSigil, textUnits } from '../shared/utils.mjs';
import { animateAttr, focusEdgeAttrs, focusNodeAttrs, focusNodeTitle, svgAccessibleText, svgRootAttrs } from '../shared/cli.mjs';
import {
  throwDiagnosticError,
  throwDiagnosticProblems,
  withDiagnosticRecordingSuppressed,
} from '../shared/diagnostics.mjs';
import { validateSchema } from '../shared/validator.mjs';
import {
  legendFootprint,
  measureLegend,
  relationshipLegendObstacles,
  resolveLegend,
  renderLegend as renderResolvedLegend,
} from '../shared/legend.mjs';
import { availableNodeTextWidth, fittedNodeFontSize, minimumNodeTextWidth } from '../shared/text-fit.mjs';
import { brandLabelFitWidth, brandMetadataFor, brandTopRailProblem, renderBrandMark } from '../shared/brand-marks.mjs';
import { translateMessage as i18nText } from '../shared/i18n.mjs';
import {
  createMappedWorkflowCandidate,
  intrinsicWorkflow,
  planningWorkflow,
} from './workflow-migration-geometry.mjs';
import {
  asArray,
  isFinitePoint,
  rectsOverlap,
  segmentIntersectsRect,
  segmentRectClearance,
  cleanEndpointSideProblems,
  cleanFlowProblems,
  cleanCrossingProblems,
  cleanAmbiguousCorridorProblems,
  cleanBorderRunProblems,
  cleanRouteRhythmProblems,
  cleanLabelRouteClearanceProblems,
  collectAmbiguousCorridors,
  collectLabelRouteClearance,
  collectBorderRuns,
  forwardCollinearAnalysisSegments,
  sourceSegmentIndexAtPoint,
  suggestLabelObstacleFix,
  suggestLabelPairFix,
  anchor,
  automaticPortSpread,
  defaultFromSide,
  defaultToSide,
  chosenSide,
  normalizeRoutePoints,
  routeHonorsEndpointSides,
  polylinePath,
  routePointsValue,
  labelPoint,
  componentFill,
  componentText,
  arrowClassMap,
  variantAccent
} from '../shared/geometry.mjs';

const LEGACY_COLUMN_CENTERS = Object.freeze([88, 220, 300, 430, 500, 625]);
const READABLE_CANDIDATE_COST_PRIORITY = Object.freeze([
  'automaticForwardReversePx',
  'properCrossingCount',
  'sharedCorridorPx',
  'labelRouteClearanceDeficit',
  'interiorPreferred28Deficit',
  'bendCount',
  'stretchMilli',
  'canvasGrowthPx',
  'portDisplacementMilli',
  'legacyCoordinateDisplacement',
  'stableCandidateOrdinal',
]);
const MAX_READABLE_LAYOUT_FEEDBACK_ROUNDS = 3;
const GROUP_FRAME_TOP_INSET = 8;
const GROUP_FRAME_BOTTOM_INSET = 4;
const GROUP_LABEL_BASELINE_OFFSET = -2;
const GROUP_LABEL_MASK_ASCENT = 10;
const GROUP_LABEL_MASK_H = 14;
const GROUP_NODE_INSET = 4;

class WorkflowLayoutFeedback extends Error {
  constructor(request) {
    super(`ワークフローレイアウトには ${request.kind} フィードバックが必要です。`);
    this.name = 'WorkflowLayoutFeedback';
    this.request = request;
  }
}

function createLegacyLayout() {
  return {
    contract: 'fixed-v1',
    laneX: 40,
    laneY: 52,
    laneW: 640,
    laneH: 104,
    laneGap: 20,
    laneTitleH: 30,
    colXs: [...LEGACY_COLUMN_CENTERS],
    nodeW: 92,
    nodeH: 52,
    defaultViewBoxWidth: 720,
  };
}

function authoredNodeWidth(node) {
  return Number.isFinite(node?.width) ? node.width : 92;
}

function nodeWidthContributor(node) {
  return `ノード ${node.id} の幅 ${authoredNodeWidth(node)}px`;
}

function authoredNodeHeight(node) {
  if (Number.isFinite(node?.height)) return node.height;
  return node?.tag ? 68 : 52;
}

function workflowLabelWidth(label) {
  return Math.max(30, textUnits(label) * 4.8 + 10);
}

function readableGroupBounds(workflow, group, colXs) {
  if (!Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)
    || group.fromCol < 0 || group.fromCol > group.toCol || group.toCol >= colXs.length) {
    return { x: 0, width: 0, cx: 0 };
  }
  const start = colXs[group.fromCol] - 50;
  const end = colXs[group.toCol] + 50;
  const naturalWidth = end - start;
  const minimumWidth = textUnits(group.label) * 5.6 + 20;
  let width = Math.max(naturalWidth, minimumWidth);
  let left = group.fromCol === group.toCol && width > naturalWidth
    ? start
    : (start + end - width) / 2;
  let right = left + width;
  for (const node of asArray(workflow.nodes)) {
    if (node.lane !== group.lane
      || !Number.isInteger(node.col)
      || node.col < group.fromCol
      || node.col > group.toCol
      || node.col < 0
      || node.col >= colXs.length) continue;
    const halfWidth = authoredNodeWidth(node) / 2;
    left = Math.min(left, colXs[node.col] - halfWidth - GROUP_NODE_INSET);
    right = Math.max(right, colXs[node.col] + halfWidth + GROUP_NODE_INSET);
  }
  width = right - left;
  return { x: left, width, cx: left + width / 2 };
}

function verticalIntervalsOverlap(a, b, clearance = 0) {
  const aCenter = Number(a?.yOffset) || 0;
  const bCenter = Number(b?.yOffset) || 0;
  return Math.abs(aCenter - bCenter)
    < authoredNodeHeight(a) / 2 + authoredNodeHeight(b) / 2 + clearance;
}

function createReadableLayout(workflow, layoutFeedback = {}) {
  const columnCount = 6;
  const baselinePitch = 120;
  const columnStart = 94;
  const maxLayoutIterations = 3;
  const channelDetourBudgetPx = 4 * 28;
  const constraints = [];
  const feedbackConstraints = [];
  const channelLabelEdgeKeys = new Set();
  const widthContributors = new Set();
  const heightContributors = new Set();
  const nodes = asArray(workflow.nodes);
  const nodesById = new Map(nodes.map((node) => [node.id, node]));

  for (let col = 0; col < columnCount - 1; col += 1) {
    constraints.push({ from: col, to: col + 1, minimum: baselinePitch });
  }
  for (const [key, minimum] of Object.entries(layoutFeedback.rankGapMinimums || {}).sort()) {
    const [from, to] = key.split(':').map(Number);
    constraints.push({
      from,
      to,
      minimum,
      contributors: layoutFeedback.rankGapContributors?.[key]
        || [`ランク ${from}→${to} の経路間隔`],
    });
  }

  for (let leftIndex = 0; leftIndex < nodes.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < nodes.length; rightIndex += 1) {
      const leftNode = nodes[leftIndex];
      const rightNode = nodes[rightIndex];
      if (leftNode.lane !== rightNode.lane || leftNode.col === rightNode.col) continue;
      if (!verticalIntervalsOverlap(leftNode, rightNode, 8)) continue;
      const fromNode = leftNode.col < rightNode.col ? leftNode : rightNode;
      const toNode = fromNode === leftNode ? rightNode : leftNode;
      constraints.push({
        from: fromNode.col,
        to: toNode.col,
        minimum: authoredNodeWidth(fromNode) / 2 + 8 + authoredNodeWidth(toNode) / 2,
        contributors: [
          `ランク ${fromNode.col}→${toNode.col} のノード幅間隔`,
          nodeWidthContributor(fromNode),
          nodeWidthContributor(toNode),
        ],
      });
    }
  }

  for (const edge of asArray(workflow.edges)) {
    const fromNode = nodesById.get(edge.from);
    const toNode = nodesById.get(edge.to);
    if (!fromNode || !toNode || fromNode.lane !== toNode.lane || fromNode.col === toNode.col) continue;
    if (edge.via || edge.channelX !== undefined || edge.channelY !== undefined
      || !['auto', 'straight'].includes(edge.route || 'auto')) continue;
    if ((Number(fromNode.yOffset) || 0) !== (Number(toNode.yOffset) || 0)) continue;
    const earlier = fromNode.col < toNode.col ? fromNode : toNode;
    const later = earlier === fromNode ? toNode : fromNode;
    const labeledDirectClearance = edge.label && !edge.labelAt
      ? Math.max(28, workflowLabelWidth(edge.label) + 8)
      : 28;
    const directLabelExpansionCost = Math.max(0, labeledDirectClearance - 28);
    const canUseAutomaticLabelChannel = edge.label
      && !edge.labelAt
      && (edge.route || 'auto') === 'auto'
      && !edge.fromSide
      && !edge.toSide
      && edge.channelX === undefined
      && edge.channelY === undefined;
    const preferLabelChannel = canUseAutomaticLabelChannel
      && directLabelExpansionCost > channelDetourBudgetPx;
    if (preferLabelChannel) channelLabelEdgeKeys.add(stableValueKey(edge));
    constraints.push({
      from: earlier.col,
      to: later.col,
      minimum: authoredNodeWidth(earlier) / 2 + 28 + authoredNodeWidth(later) / 2,
      contributors: [
        `ランク ${earlier.col}→${later.col} の直接経路間隔`,
        `ランク ${earlier.col}→${later.col} のノード幅間隔`,
        nodeWidthContributor(earlier),
        nodeWidthContributor(later),
      ],
    });
    if (!preferLabelChannel && labeledDirectClearance > 28) {
      const labelConstraintMinimum = authoredNodeWidth(earlier) / 2
        + labeledDirectClearance
        + authoredNodeWidth(later) / 2;
      feedbackConstraints.push({
        from: earlier.col,
        to: later.col,
        minimum: labelConstraintMinimum,
        contributors: [
          `ランク ${earlier.col}→${later.col} の直接経路間隔`,
          `エッジ ${workflowEdgeName(edge)} のラベルマスク`,
          nodeWidthContributor(earlier),
          nodeWidthContributor(later),
        ],
      });
    }
  }

  for (const phase of asArray(workflow.phases)) {
    if (!Number.isInteger(phase.fromCol) || !Number.isInteger(phase.toCol)
      || phase.fromCol < 0 || phase.fromCol > phase.toCol || phase.toCol >= columnCount) continue;
    const minimumWidth = textUnits(phase.label) * 5.6 + 8;
    if (phase.fromCol === phase.toCol) {
      if (phase.toCol < columnCount - 1) {
        constraints.push({
          from: phase.toCol,
          to: phase.toCol + 1,
          minimum: baselinePitch + Math.max(0, minimumWidth - 92),
          contributors: [`フェーズ ${phase.id || phase.label} のラベル範囲`],
        });
      }
      continue;
    }
    constraints.push({
      from: phase.fromCol,
      to: phase.toCol,
      minimum: Math.max(0, minimumWidth - 92),
      contributors: [`フェーズ ${phase.id || phase.label} のラベル範囲`],
    });
  }

  for (const group of asArray(workflow.groups)) {
    if (!Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)
      || group.fromCol < 0 || group.fromCol > group.toCol || group.toCol >= columnCount) continue;
    const minimumWidth = textUnits(group.label) * 5.6 + 20;
    if (group.fromCol === group.toCol) {
      if (group.toCol < columnCount - 1) {
        constraints.push({
          from: group.toCol,
          to: group.toCol + 1,
          minimum: baselinePitch + Math.max(0, minimumWidth - 100),
          contributors: [`グループ ${group.id || group.label} のラベル範囲`],
        });
      }
      continue;
    }
    constraints.push({
      from: group.fromCol,
      to: group.toCol,
      minimum: Math.max(0, minimumWidth - 100),
      contributors: [`グループ ${group.id || group.label} のラベル範囲`],
    });
  }

  let activeConstraints = [...constraints];
  let colXs;
  let colProvenance;
  for (let iteration = 0; iteration < maxLayoutIterations; iteration += 1) {
    colXs = Array.from({ length: columnCount }, (_, col) => columnStart + col * baselinePitch);
    colProvenance = Array.from({ length: columnCount }, () => new Set());
    const orderedConstraints = activeConstraints
      .filter(({ from, to, minimum }) => (
        Number.isInteger(from) && Number.isInteger(to)
        && from >= 0 && from < to && to < columnCount
        && Number.isFinite(minimum)
      ))
      .sort((a, b) => a.to - b.to || a.from - b.from || a.minimum - b.minimum);
    for (let to = 1; to < columnCount; to += 1) {
      for (const constraint of orderedConstraints) {
        if (constraint.to !== to) continue;
        const candidate = colXs[constraint.from] + constraint.minimum;
        const candidateProvenance = new Set([
          ...colProvenance[constraint.from],
          ...asArray(constraint.contributors),
        ]);
        if (candidate > colXs[to] + 0.0001) {
          colXs[to] = candidate;
          colProvenance[to] = candidateProvenance;
        } else if (Math.abs(candidate - colXs[to]) <= 0.0001
          && candidate > columnStart + to * baselinePitch + 0.0001) {
          for (const contributor of candidateProvenance) colProvenance[to].add(contributor);
        }
      }
    }
    if (iteration > 0 || !feedbackConstraints.length) break;
    activeConstraints = [...activeConstraints, ...feedbackConstraints];
  }

  const firstRankNodes = nodes.filter((node) => node.col === 0);
  const firstExtent = firstRankNodes.reduce(
    (maximum, node) => Math.max(maximum, authoredNodeWidth(node) / 2),
    46,
  );
  const leftInset = 8;
  const leftShift = Math.max(0, 40 + leftInset + firstExtent - colXs[0]);
  if (leftShift) {
    for (let col = 0; col < colXs.length; col += 1) colXs[col] += leftShift;
    for (const node of firstRankNodes) {
      if (Math.abs(authoredNodeWidth(node) / 2 - firstExtent) > 0.0001) continue;
      for (const provenance of colProvenance) provenance.add(nodeWidthContributor(node));
    }
  }

  const unpinnedTopEndpointIds = new Set();
  for (const edge of asArray(workflow.edges)) {
    const preservesHorizontalPins = Array.isArray(edge.via) || edge.channelX !== undefined;
    if (preservesHorizontalPins) continue;
    if (edge.fromSide === 'top') unpinnedTopEndpointIds.add(edge.from);
    if (edge.toSide === 'top') unpinnedTopEndpointIds.add(edge.to);
  }
  const laneOrder = new Map(asArray(workflow.lanes).map((lane, index) => [lane.id, index]));
  let laneHeaderShift = 0;
  const laneHeaderShiftContributors = new Set();
  for (const nodeId of unpinnedTopEndpointIds) {
    const node = nodesById.get(nodeId);
    if (!node || !Number.isInteger(node.col) || node.col < 0 || node.col >= columnCount) continue;
    const lanePosition = laneOrder.get(node.lane);
    const lane = asArray(workflow.lanes)[lanePosition];
    if (!lane) continue;
    const prefix = lane.variant === 'exception'
      ? 'EX'
      : String(lanePosition + 1).padStart(2, '0');
    const laneHeaderRight = 40 + 14 + textUnits(`${prefix} / ${lane.label}`) * 6.2;
    const requiredShift = laneHeaderRight + 2 - colXs[node.col];
    if (requiredShift > laneHeaderShift + 0.0001) {
      laneHeaderShift = requiredShift;
      laneHeaderShiftContributors.clear();
      laneHeaderShiftContributors.add(`レーン ${lane.id} のラベル幅`);
    } else if (requiredShift > 0 && Math.abs(requiredShift - laneHeaderShift) <= 0.0001) {
      laneHeaderShiftContributors.add(`レーン ${lane.id} のラベル幅`);
    }
  }
  if (laneHeaderShift > 0) {
    for (let col = 0; col < colXs.length; col += 1) colXs[col] += laneHeaderShift;
    for (const provenance of colProvenance) {
      for (const contributor of laneHeaderShiftContributors) provenance.add(contributor);
    }
  }

  let measuredContentLeftShift = asArray(workflow.edges).reduce((maximum, edge) => {
    if (!channelLabelEdgeKeys.has(stableValueKey(edge))) return maximum;
    const fromNode = nodesById.get(edge.from);
    const toNode = nodesById.get(edge.to);
    if (!fromNode || !toNode) return maximum;
    const labelCenter = (colXs[fromNode.col] + colXs[toNode.col]) / 2;
    const labelLeft = labelCenter - workflowLabelWidth(edge.label) / 2;
    return Math.max(maximum, 16 - labelLeft);
  }, 0);
  for (const phase of asArray(workflow.phases)) {
    if (!Number.isInteger(phase.fromCol) || !Number.isInteger(phase.toCol)) continue;
    const width = Math.max(
      colXs[phase.toCol] - colXs[phase.fromCol] + 92,
      textUnits(phase.label) * 5.6 + 8,
    );
    const left = phase.fromCol === phase.toCol
      ? colXs[phase.fromCol] - 46
      : (colXs[phase.fromCol] + colXs[phase.toCol] - width) / 2;
    measuredContentLeftShift = Math.max(measuredContentLeftShift, 16 - left);
  }
  for (const group of asArray(workflow.groups)) {
    if (!Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)) continue;
    const bounds = readableGroupBounds(workflow, group, colXs);
    measuredContentLeftShift = Math.max(measuredContentLeftShift, 44 - bounds.x);
  }
  if (measuredContentLeftShift > 0) {
    for (let col = 0; col < colXs.length; col += 1) colXs[col] += measuredContentLeftShift;
  }

  let rightmost = colXs.at(-1) + 50;
  let rightmostContributors = new Set(colProvenance.at(-1));
  for (const node of nodes) {
    if (!Number.isInteger(node.col) || node.col < 0 || node.col >= columnCount) continue;
    const nodeRight = colXs[node.col] + authoredNodeWidth(node) / 2;
    const nodeContributors = new Set([
      ...colProvenance[node.col],
      nodeWidthContributor(node),
    ]);
    if (nodeRight > rightmost + 0.0001) {
      rightmost = nodeRight;
      rightmostContributors = nodeContributors;
    } else if (Math.abs(nodeRight - rightmost) <= 0.0001) {
      for (const contributor of nodeContributors) rightmostContributors.add(contributor);
    }
  }
  for (const group of asArray(workflow.groups)) {
    if (!Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)) continue;
    const bounds = readableGroupBounds(workflow, group, colXs);
    const groupRight = bounds.x + bounds.width;
    const groupContributors = new Set([
      ...colProvenance[group.fromCol],
      ...colProvenance[group.toCol],
      `グループ ${group.id || group.label} のラベル範囲`,
      ...nodes
        .filter((node) => node.lane === group.lane
          && node.col >= group.fromCol && node.col <= group.toCol)
        .map(nodeWidthContributor),
    ]);
    if (groupRight > rightmost + 0.0001) {
      rightmost = groupRight;
      rightmostContributors = groupContributors;
    } else if (Math.abs(groupRight - rightmost) <= 0.0001) {
      for (const contributor of groupContributors) rightmostContributors.add(contributor);
    }
  }
  const widestLaneLabel = asArray(workflow.lanes).reduce((widest, lane, index) => {
    const width = textUnits(`${String(index + 1).padStart(2, '0')} / ${lane.label}`) * 6.2 + 30;
    return width > widest.width ? { width, lane } : widest;
  }, { width: 0, lane: null });
  const laneLabelWidth = widestLaneLabel.width;
  const rightmostLaneWidth = Math.ceil(rightmost - 40 + 8);
  const laneW = Math.max(
    640,
    rightmostLaneWidth,
    Math.ceil(laneLabelWidth),
  );
  if (laneW > 640) {
    if (rightmostLaneWidth === laneW) {
      for (const contributor of rightmostContributors) widthContributors.add(contributor);
    }
    if (Math.ceil(laneLabelWidth) === laneW && widestLaneLabel.lane) {
      widthContributors.add(`レーン ${widestLaneLabel.lane.id || widestLaneLabel.lane.label} のラベル幅`);
    }
  }
  let maxVerticalExtent = 0;
  const verticalExtentContributors = new Set();
  for (const node of nodes) {
    const yOffset = Number(node.yOffset) || 0;
    const extent = authoredNodeHeight(node) / 2 + Math.abs(yOffset);
    const contributor = `ノード ${node.id} の高さ ${authoredNodeHeight(node)}px${yOffset ? `、yOffset ${yOffset}px` : ''}`;
    if (extent > maxVerticalExtent + 0.0001) {
      maxVerticalExtent = extent;
      verticalExtentContributors.clear();
      verticalExtentContributors.add(contributor);
    } else if (Math.abs(extent - maxVerticalExtent) <= 0.0001) {
      verticalExtentContributors.add(contributor);
    }
  }
  const baseContentH = Math.max(74, Math.ceil(maxVerticalExtent * 2 + 8));
  const laneH = 30 + baseContentH;
  const groupsByLane = new Map();
  for (const group of asArray(workflow.groups)) {
    groupsByLane.set(group.lane, [...(groupsByLane.get(group.lane) || []), group]);
  }
  const groupLaneReserves = asArray(workflow.lanes).map((lane) => {
    let header = 0;
    let footer = 0;
    for (const group of groupsByLane.get(lane.id) || []) {
      const bounds = readableGroupBounds(workflow, group, colXs);
      const labelLeft = bounds.x + 10;
      const labelRight = labelLeft + textUnits(group.label) * 5.6;
      for (const node of nodes) {
        if (node.lane !== group.lane
          || !Number.isInteger(node.col)
          || node.col < group.fromCol
          || node.col > group.toCol
          || node.col < 0
          || node.col >= colXs.length) continue;
        const halfWidth = authoredNodeWidth(node) / 2;
        const nodeLeft = colXs[node.col] - halfWidth;
        const nodeRight = colXs[node.col] + halfWidth;
        const overlapsLabel = nodeRight > labelLeft && nodeLeft < labelRight;
        const topOffset = (baseContentH - authoredNodeHeight(node)) / 2
          + (Number(node.yOffset) || 0);
        const minimumTopOffset = overlapsLabel ? 11 : 9;
        header = Math.max(header, Math.ceil(minimumTopOffset - topOffset));
        const bottomMargin = baseContentH - GROUP_FRAME_BOTTOM_INSET
          - topOffset - authoredNodeHeight(node);
        footer = Math.max(footer, Math.ceil(1 - bottomMargin));
      }
    }
    return { header: Math.max(0, header), footer: Math.max(0, footer) };
  });
  const groupHeaderHeights = groupLaneReserves.map(({ header }) => header);
  const groupFooterHeights = groupLaneReserves.map(({ footer }) => footer);
  const laneHeights = groupLaneReserves.map(({ header, footer }) => laneH + header + footer);
  const laneGap = Math.max(20, Math.ceil(layoutFeedback.laneGapMin || 0));
  for (const [index, reserve] of groupHeaderHeights.entries()) {
    if (!reserve) continue;
    const lane = asArray(workflow.lanes)[index];
    heightContributors.add(`レーン ${lane.id || lane.label} のグループラベル間隔 ${reserve}px`);
  }
  for (const [index, reserve] of groupFooterHeights.entries()) {
    if (!reserve) continue;
    const lane = asArray(workflow.lanes)[index];
    heightContributors.add(`レーン ${lane.id || lane.label} のグループ枠収容間隔 ${reserve}px`);
  }
  if (laneH > 104) {
    for (const contributor of verticalExtentContributors) heightContributors.add(contributor);
  }
  if (laneGap > 20) {
    for (const contributor of asArray(layoutFeedback.laneGapContributors)) {
      heightContributors.add(contributor);
    }
  }
  const requiredWidth = 40 + laneW + 16;

  return {
    contract: 'readable-v2',
    laneX: 40,
    laneY: 52,
    laneW,
    laneH,
    laneHeights,
    laneGap,
    laneTitleH: 30,
    groupHeaderHeights,
    groupFooterHeights,
    colXs,
    nodeW: 92,
    nodeH: 52,
    defaultViewBoxWidth: requiredWidth,
    channelLabelEdgeKeys,
    widthContributors: [...widthContributors].sort(stableCompare),
    heightContributors: [...heightContributors].sort(stableCompare),
  };
}

function compilerFailure(contract, diagnostics, error = diagnostics.map(({ message }) => message).join('\n')) {
  return {
    ok: false,
    error,
    diagnostics,
    receipt: { contract, diagnostics },
  };
}

function workflowEdgeName(edge) {
  return edge.id || `${edge.from}->${edge.to}`;
}

function stableText(value) {
  return value == null ? '' : String(value);
}

function stableCompare(left, right) {
  const a = stableText(left);
  const b = stableText(right);
  return a < b ? -1 : a > b ? 1 : 0;
}

function stableValueKey(value) {
  if (Array.isArray(value)) return `[${value.map(stableValueKey).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort(stableCompare).map((key) => `${JSON.stringify(key)}:${stableValueKey(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function cloneWorkflow(value) {
  return JSON.parse(JSON.stringify(value));
}

function canonicalReadableWorkflow(workflow) {
  if (workflow.schema_version !== 2) return workflow;
  const laneOrder = new Map(asArray(workflow.lanes).map((lane, index) => [lane.id, index]));
  const nodes = [...asArray(workflow.nodes)].sort((left, right) => (
    (laneOrder.get(left.lane) ?? Number.MAX_SAFE_INTEGER) - (laneOrder.get(right.lane) ?? Number.MAX_SAFE_INTEGER)
    || left.col - right.col
    || stableCompare(left.id, right.id)
  ));
  const edges = [...asArray(workflow.edges)].sort((left, right) => (
    stableCompare(left.id, right.id)
    || stableCompare(left.from, right.from)
    || stableCompare(left.to, right.to)
    || stableCompare(left.label, right.label)
    || stableCompare(left.route, right.route)
    || stableCompare(stableValueKey(left), stableValueKey(right))
  ));
  const phases = workflow.phases === undefined ? undefined : [...asArray(workflow.phases)].sort((left, right) => (
    left.fromCol - right.fromCol || left.toCol - right.toCol
    || stableCompare(left.id, right.id)
  ));
  const groups = workflow.groups === undefined ? undefined : [...asArray(workflow.groups)].sort((left, right) => (
    (laneOrder.get(left.lane) ?? Number.MAX_SAFE_INTEGER) - (laneOrder.get(right.lane) ?? Number.MAX_SAFE_INTEGER)
    || left.fromCol - right.fromCol || left.toCol - right.toCol
    || stableCompare(left.id, right.id)
  ));
  return {
    ...workflow,
    nodes,
    edges,
    ...(phases ? { phases } : {}),
    ...(groups ? { groups } : {}),
  };
}

function semanticContractDiagnostics(workflow) {
  const checks = workflow.semanticChecks;
  if (!checks) return [];

  const nodeIds = new Set(asArray(workflow.nodes).map((node) => node.id));
  const incoming = new Map([...nodeIds].map((id) => [id, 0]));
  const outgoing = new Map([...nodeIds].map((id) => [id, 0]));
  const adjacency = new Map([...nodeIds].map((id) => [id, new Set()]));
  for (const edge of asArray(workflow.edges)) {
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) continue;
    outgoing.set(edge.from, outgoing.get(edge.from) + 1);
    incoming.set(edge.to, incoming.get(edge.to) + 1);
    adjacency.get(edge.from).add(edge.to);
  }

  const diagnostics = [];
  const diagnostic = (code, message, subject, evidence, supportedFixes) => ({
    code,
    severity: 'error',
    message,
    subject: { diagramType: 'workflow', ...subject },
    evidence,
    supportedFixes,
  });
  const referencedNodes = [
    ...asArray(checks.allowedRoots).map((id, index) => ({ id, path: `/semanticChecks/allowedRoots/${index}` })),
    ...asArray(checks.allowedTerminals).map((id, index) => ({ id, path: `/semanticChecks/allowedTerminals/${index}` })),
    ...asArray(checks.requiredEdges).flatMap((relation, index) => [
      { id: relation.from, path: `/semanticChecks/requiredEdges/${index}/from` },
      { id: relation.to, path: `/semanticChecks/requiredEdges/${index}/to` },
    ]),
    ...asArray(checks.requiredPaths).flatMap((relation, index) => [
      { id: relation.from, path: `/semanticChecks/requiredPaths/${index}/from` },
      { id: relation.to, path: `/semanticChecks/requiredPaths/${index}/to` },
    ]),
  ];
  for (const { id, path } of referencedNodes) {
    if (nodeIds.has(id)) continue;
    diagnostics.push(diagnostic(
      'workflow/semantic-node-reference',
      `ワークフローのセマンティック契約が ${path} で不明なノード "${id}" を参照しています。`,
      { node: id, path },
      { knownNodes: [...nodeIds] },
      [`"${id}" を既存のノード id に置き換える`, 'コンパイル前に不足しているノードを追加する'],
    ));
  }
  if (diagnostics.length) return diagnostics;

  if (checks.allowedRoots !== undefined) {
    const allowed = new Set(checks.allowedRoots);
    for (const [node, count] of incoming) {
      if (count > 0 || allowed.has(node)) continue;
      diagnostics.push(diagnostic(
        'workflow/unexpected-root',
        `ワークフローノード "${node}" には入力エッジがなく、semanticChecks.allowedRoots にも宣言されていません。`,
        { node, path: '/semanticChecks/allowedRoots' },
        { incomingEdges: 0, allowedRoots: [...allowed] },
        [`"${node}" への不足している入力エッジを追加する`, `"${node}" が意図した開始点である場合は semanticChecks.allowedRoots に宣言する`],
      ));
    }
  }

  if (checks.allowedTerminals !== undefined) {
    const allowed = new Set(checks.allowedTerminals);
    for (const [node, count] of outgoing) {
      if (count > 0 || allowed.has(node)) continue;
      diagnostics.push(diagnostic(
        'workflow/unexpected-terminal',
        `ワークフローノード "${node}" には出力エッジがなく、semanticChecks.allowedTerminals にも宣言されていません。`,
        { node, path: '/semanticChecks/allowedTerminals' },
        { outgoingEdges: 0, allowedTerminals: [...allowed] },
        [`"${node}" からの不足している出力エッジを追加する`, `"${node}" が意図した終点である場合は semanticChecks.allowedTerminals に宣言する`],
      ));
    }
  }

  const authoredEdges = new Set(asArray(workflow.edges).map((edge) => `${edge.from}\u0000${edge.to}`));
  for (const [index, relation] of asArray(checks.requiredEdges).entries()) {
    if (authoredEdges.has(`${relation.from}\u0000${relation.to}`)) continue;
    diagnostics.push(diagnostic(
      'workflow/required-edge',
      `ワークフローのセマンティック契約にはエッジ "${relation.from}" -> "${relation.to}" が必要ですが、一致する作成済みエッジがありません。`,
      { from: relation.from, to: relation.to, path: `/semanticChecks/requiredEdges/${index}` },
      { authoredEdgeCount: asArray(workflow.edges).length },
      [`セマンティック要件を削除せず、"${relation.from}" から "${relation.to}" へのエッジを追加する`],
    ));
  }

  function reachable(from, to) {
    const visited = new Set([from]);
    const pending = [from];
    while (pending.length) {
      const current = pending.shift();
      if (current === to) return true;
      for (const next of adjacency.get(current) || []) {
        if (visited.has(next)) continue;
        visited.add(next);
        pending.push(next);
      }
    }
    return false;
  }

  for (const [index, relation] of asArray(checks.requiredPaths).entries()) {
    if (reachable(relation.from, relation.to)) continue;
    diagnostics.push(diagnostic(
      'workflow/required-path',
      `ワークフローのセマンティック契約には "${relation.from}" から "${relation.to}" への有向経路が必要ですが、該当する経路がありません。`,
      { from: relation.from, to: relation.to, path: `/semanticChecks/requiredPaths/${index}` },
      { reachableNodes: [...new Set([relation.from, ...(adjacency.get(relation.from) || [])])] },
      [`セマンティック要件を弱めず、"${relation.from}" から "${relation.to}" への有向経路を復元する`],
    ));
  }

  return diagnostics;
}

function compileWorkflowInternal({
  workflow: inputWorkflow,
  qualityProfile,
  discoverFixes = true,
  layoutFeedback = {},
} = {}) {
  if (!inputWorkflow || typeof inputWorkflow !== 'object' || Array.isArray(inputWorkflow)) {
    const diagnostics = [{
      code: 'workflow/input-contract',
      severity: 'error',
      message: 'compileWorkflow には解析済みのワークフロードキュメントオブジェクトが1つ必要です。',
      subject: { diagramType: 'workflow', path: '/' },
      evidence: {},
      supportedFixes: [],
    }];
    return compilerFailure('fixed-v1', diagnostics, diagnostics[0].message);
  }
  const resolvedQualityProfile = qualityProfile || inputWorkflow.meta?.quality_profile;
  const authoredQualityProfile = inputWorkflow.meta?.quality_profile;
  const qualityResolvedWorkflow = resolvedQualityProfile && resolvedQualityProfile !== inputWorkflow.meta?.quality_profile
    ? { ...inputWorkflow, meta: { ...inputWorkflow.meta, quality_profile: resolvedQualityProfile } }
    : inputWorkflow;
  let inputDiagnostics = [];
  try {
    validateSchema('workflow', qualityResolvedWorkflow);
  } catch (error) {
    inputDiagnostics = Array.isArray(error?.archifyDiagnostics)
      ? error.archifyDiagnostics.map((diagnostic) => ({
          ...diagnostic,
          supportedFixes: [],
        }))
      : [{
        code: 'workflow/input-contract',
        severity: 'error',
        message: 'ワークフロースキーマの検証が予期せず失敗しました。',
        subject: { diagramType: 'workflow', path: '/' },
        evidence: { reason: error?.message || String(error) },
        supportedFixes: [],
      }];
  }
  if (inputDiagnostics.length) {
    return compilerFailure(
      inputWorkflow.schema_version === 2 ? 'readable-v2' : 'fixed-v1',
      inputDiagnostics,
    );
  }
  const workflow = canonicalReadableWorkflow(qualityResolvedWorkflow);
  const semanticDiagnostics = semanticContractDiagnostics(workflow);
  if (semanticDiagnostics.length) {
    return compilerFailure(
      workflow.schema_version === 2 ? 'readable-v2' : 'fixed-v1',
      semanticDiagnostics,
    );
  }
  const sourceIndexes = {
    lanes: new Map(asArray(qualityResolvedWorkflow.lanes).map((lane, index) => [lane, index])),
    nodes: new Map(asArray(qualityResolvedWorkflow.nodes).map((node, index) => [node, index])),
    edges: new Map(asArray(qualityResolvedWorkflow.edges).map((edge, index) => [edge, index])),
  };
  const layout = workflow.schema_version === 2
    ? createReadableLayout(workflow, layoutFeedback)
    : createLegacyLayout();

const LEGEND_CATALOG = [
  'frontend',
  'backend',
  'security',
  'messagebus',
  'database',
  'cloud',
  'external',
].map((kind) => ({ kind, label: i18nText(workflow.meta.locale, `legend.workflow.${kind}`) }));
const presentLegendKinds = new Set(asArray(workflow.nodes).map((node) => node.type));
const workflowLegendEntries = resolveLegend(
  workflow.meta?.legend,
  LEGEND_CATALOG,
  presentLegendKinds,
);
const legendFootprintOptions = { fontSize: 7, itemGap: 7 };
const oneRowLegendFootprint = legendFootprint(workflowLegendEntries, {
  ...legendFootprintOptions,
  width: Number.MAX_SAFE_INTEGER,
});
const minimumCanvasWidth = workflow.schema_version === 2
  ? Math.max(layout.defaultViewBoxWidth, oneRowLegendFootprint.minWidth + 40)
  : layout.defaultViewBoxWidth;
const legendPackingWidth = Math.max(
  1,
  (workflow.schema_version === 2
    ? minimumCanvasWidth
    : (workflow.meta?.viewBox?.[0] ?? minimumCanvasWidth)) - 40,
);
const packedLegendFootprint = legendFootprint(workflowLegendEntries, {
  ...legendFootprintOptions,
  width: legendPackingWidth,
});
const legendExtraHeight = workflow.schema_version === 2
  ? packedLegendFootprint.extraHeight
  : 0;

// Content is 680px wide (laneX + laneW); auto height fits the lanes plus legend.
const autoHeight = layout.laneY
  + (layout.laneHeights?.reduce((total, height) => total + height, 0)
    ?? (workflow.lanes?.length || 1) * layout.laneH)
  + ((workflow.lanes?.length || 1) - 1) * layout.laneGap
  + 124
  + legendExtraHeight;
let viewBox = workflow.meta?.viewBox || [minimumCanvasWidth, autoHeight];
let requiredViewBox = [...viewBox];

const laneIndex = new Map(asArray(workflow.lanes).map((lane, index) => [lane.id, index]));
const laneLabels = new Map(asArray(workflow.lanes).map((lane) => [lane.id, lane.label]));

function nodeContext(node) {
  const group = asArray(workflow.groups).find((candidate) => (
    candidate.lane === node.lane && node.col >= candidate.fromCol && node.col <= candidate.toCol
  ));
  const phase = asArray(workflow.phases).find((candidate) => (
    node.col >= candidate.fromCol && node.col <= candidate.toCol
  ));
  return [laneLabels.get(node.lane), group?.label, phase?.label].filter(Boolean).join(' › ')
    || i18nText(workflow.meta.locale, 'node.context.workflow');
}

function laneHeight(idOrIndex) {
  const index = typeof idOrIndex === 'number' ? idOrIndex : laneIndex.get(idOrIndex);
  return layout.laneHeights?.[index] ?? layout.laneH;
}

function laneGroupHeaderH(idOrIndex) {
  const index = typeof idOrIndex === 'number' ? idOrIndex : laneIndex.get(idOrIndex);
  return layout.groupHeaderHeights?.[index] ?? 0;
}

function laneGroupFooterH(idOrIndex) {
  const index = typeof idOrIndex === 'number' ? idOrIndex : laneIndex.get(idOrIndex);
  return layout.groupFooterHeights?.[index] ?? 0;
}

function laneTop(id) {
  const index = laneIndex.get(id);
  const precedingHeight = asArray(workflow.lanes).slice(0, index)
    .reduce((total, _lane, lanePosition) => total + laneHeight(lanePosition), 0);
  return layout.laneY + precedingHeight + index * layout.laneGap;
}

function lastLaneBottom() {
  return layout.laneY
    + asArray(workflow.lanes).reduce((total, _lane, index) => total + laneHeight(index), 0)
    + (workflow.lanes.length - 1) * layout.laneGap;
}

function legendY() {
  return lastLaneBottom() + 44 + legendExtraHeight;
}

function workflowLegendLayout(obstacles = []) {
  return {
    x: 20,
    baselineY: legendY(),
    width: workflow.schema_version === 2 ? legendPackingWidth : viewBox[0] - 40,
    fontSize: 7,
    itemGap: 7,
    minTitleY: lastLaneBottom() + 8,
    obstacles,
    unfit: workflow.meta?.legend === undefined ? 'hide' : 'error',
    diagramType: 'workflow',
  };
}

function workflowLegendRects() {
  if (!workflowLegendEntries.length) return [];
  const measured = measureLegend(workflowLegendEntries, workflowLegendLayout());
  if (!measured) return [];
  return [
    { kind: 'title', x: 20, y: measured.titleY - 10, width: 48, height: 14 },
    ...measured.entries.map((entry) => ({
      kind: entry.kind,
      x: entry.x,
      y: entry.baseline - 10,
      width: entry.width,
      height: 14,
    })),
  ];
}

function measureNode(node) {
  const width = node.width || layout.nodeW;
  const height = node.height || (node.tag ? 68 : layout.nodeH);
  const cx = layout.colXs[node.col];
  const groupHeaderH = laneGroupHeaderH(node.lane);
  const contentH = laneHeight(node.lane) - layout.laneTitleH
    - groupHeaderH - laneGroupFooterH(node.lane);
  const y = laneTop(node.lane) + layout.laneTitleH + groupHeaderH
    + (contentH - height) / 2 + (node.yOffset || 0);
  return {
    ...node,
    width,
    height,
    x: cx - width / 2,
    y,
    cx,
    cy: y + height / 2
  };
}

// Font sizes for this renderer's node text; the fitting geometry is shared.
const nodeTextFit = {
  labelPreferred: 11,
  labelMinimum: 9,
  sublabelPreferred: 8,
  sublabelMinimum: 6,
  tagPreferred: 7,
  tagMinimum: 6,
};

const nodes = new Map(asArray(workflow.nodes).map((node) => [node.id, measureNode(node)]));

function workflowCompositionFrames() {
  const frames = [];
  for (const [index, lane] of asArray(workflow.lanes).entries()) {
    const y = laneTop(lane.id);
    const height = laneHeight(index);
    frames.push({ id: `lane-${index}`, label: lane.label, kind: 'lane', x: layout.laneX, y, width: layout.laneW, height, radius: 10 });
    if (lane.variant === 'exception') {
      frames.push({ id: `lane-${index}-exception`, label: `${lane.label} exception`, kind: 'exception-lane', x: layout.laneX + 6, y: y + 6, width: layout.laneW - 12, height: height - 12, radius: 8 });
    }
  }
  for (const [index, group] of asArray(workflow.groups).entries()) {
    const span = groupSpan(group);
    frames.push({
      id: `group-${index}`,
      label: group.label,
      kind: 'group',
      x: span.x,
      y: laneTop(group.lane) + layout.laneTitleH + GROUP_FRAME_TOP_INSET,
      width: span.width,
      height: workflow.schema_version === 2
        ? laneHeight(group.lane) - layout.laneTitleH
          - GROUP_FRAME_TOP_INSET - GROUP_FRAME_BOTTOM_INSET
        : layout.laneH - layout.laneTitleH - 16,
      radius: 9,
    });
  }
  return frames;
}

function workflowSceneLabelObstacles() {
  const obstacles = [];
  for (const [index, lane] of asArray(workflow.lanes).entries()) {
    const prefix = lane.variant === 'exception' ? 'EX' : String(index + 1).padStart(2, '0');
    const label = `${prefix} / ${lane.label}`;
    obstacles.push({
      kind: 'lane-header',
      id: lane.id,
      x: layout.laneX + 14,
      y: laneTop(lane.id) + 12,
      width: textUnits(label) * 6.2,
      height: 14,
    });
  }
  for (const phase of asArray(workflow.phases)) {
    if (!Number.isInteger(phase.fromCol) || !Number.isInteger(phase.toCol)
      || phase.fromCol < 0 || phase.toCol >= layout.colXs.length || phase.fromCol > phase.toCol) continue;
    const span = phaseSpan(phase);
    obstacles.push({
      kind: 'phase-header',
      id: phase.id ?? null,
      x: span.x,
      y: 27,
      width: span.width,
      height: 16,
    });
  }
  for (const group of asArray(workflow.groups)) {
    if (!laneIndex.has(group.lane)
      || !Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)
      || group.fromCol < 0 || group.toCol >= layout.colXs.length || group.fromCol > group.toCol) continue;
    const span = groupSpan(group);
    const frameY = laneTop(group.lane) + layout.laneTitleH + GROUP_FRAME_TOP_INSET;
    const labelBaseline = frameY + GROUP_LABEL_BASELINE_OFFSET;
    obstacles.push({
      kind: 'group-label',
      id: group.id ?? null,
      x: span.x + 10,
      y: labelBaseline - GROUP_LABEL_MASK_ASCENT,
      width: textUnits(group.label) * 5.6,
      height: GROUP_LABEL_MASK_H,
    });
  }
  return obstacles;
}

const mainPathSteps = new Map(asArray(workflow.mainPath).map((id, index) => [id, index]));
const edgeSteps = new Map(asArray(workflow.edges).map((edge, index) => {
  const fromStep = mainPathSteps.get(edge.from);
  const toStep = mainPathSteps.get(edge.to);
  const mainStep = Number.isInteger(fromStep) && toStep === fromStep + 1 ? fromStep : null;
  return [edge, mainStep ?? asArray(workflow.mainPath).length + index];
}));

function nodeStep(node) {
  return mainPathSteps.get(node.id) ?? asArray(workflow.mainPath).length + asArray(workflow.nodes).findIndex((item) => item.id === node.id);
}

  function acceptsFix(mutator) {
    if (!discoverFixes) return false;
    const candidate = cloneWorkflow(workflow);
    mutator(candidate);
    return withDiagnosticRecordingSuppressed(() => compileWorkflowWithFeedback({
      workflow: candidate,
      qualityProfile: resolvedQualityProfile,
      discoverFixes: false,
    }).ok);
  }

  function verifiedLegacyAlternative(edge, from, to, requiredClearance) {
    const occupied = [...nodes.values()].filter((node) => node.lane === to.lane && node.id !== to.id);
  const candidates = layout.colXs.map((center, col) => ({ center, col }))
    .filter(({ col }) => col !== to.col)
    .sort((a, b) => Math.abs(a.col - to.col) - Math.abs(b.col - to.col) || a.col - b.col);
  for (const candidate of candidates) {
    const candidateRect = { ...to, col: candidate.col, cx: candidate.center, x: candidate.center - to.width / 2 };
    if (occupied.some((node) => rectsOverlap(candidateRect, node, 8))) continue;
    const centerDistance = Math.abs(candidate.center - from.cx);
    const signedClearance = centerDistance - from.width / 2 - to.width / 2;
      if (signedClearance < requiredClearance) continue;
      if (acceptsFix((document) => {
        document.nodes.find((node) => node.id === to.id).col = candidate.col;
      })) return candidate.col;
    }
    return null;
  }

  function readableMigrationProvidesCapacity(from, to, requiredClearance) {
    const readable = createReadableLayout({ ...workflow, schema_version: 2 });
    const centerDistance = Math.abs(readable.colXs[to.col] - readable.colXs[from.col]);
    if (centerDistance - from.width / 2 - to.width / 2 < requiredClearance) return false;
    if (!discoverFixes) return false;

    return withDiagnosticRecordingSuppressed(() => {
      const migrationQualityProfile = authoredQualityProfile;
      let planned = compileWorkflowWithFeedback({
        workflow: intrinsicWorkflow(workflow),
        qualityProfile: migrationQualityProfile,
        discoverFixes: false,
      });
      if (!planned.ok) {
        planned = compileWorkflowWithFeedback({
          workflow: planningWorkflow(workflow),
          qualityProfile: migrationQualityProfile,
          discoverFixes: false,
        });
      }
      if (!planned.ok || !Array.isArray(planned.receipt?.columns)) return false;

      let candidate;
      try {
        candidate = createMappedWorkflowCandidate(
          workflow,
          LEGACY_COLUMN_CENTERS,
          planned.receipt.columns,
        ).document;
      } catch {
        return false;
      }
      let compiled = compileWorkflowWithFeedback({
        workflow: candidate,
        qualityProfile: migrationQualityProfile,
        discoverFixes: false,
      });
      const requiredViewBox = compiled.diagnostics?.length
        && compiled.diagnostics.every(({ code }) => code === 'workflow/viewbox-capacity')
        ? compiled.diagnostics.find(({ evidence }) => Array.isArray(evidence?.requiredViewBox))
          ?.evidence.requiredViewBox
        : null;
      if (!compiled.ok && Array.isArray(candidate.meta?.viewBox) && requiredViewBox) {
        candidate.meta.viewBox = [
          Math.max(candidate.meta.viewBox[0], requiredViewBox[0]),
          Math.max(candidate.meta.viewBox[1], requiredViewBox[1]),
        ];
        compiled = compileWorkflowWithFeedback({
          workflow: candidate,
          qualityProfile: migrationQualityProfile,
          discoverFixes: false,
        });
      }
      return compiled.ok;
    });
  }

function verifiedReducedWidths(from, to, requiredClearance) {
  const widthBudget = 2 * (Math.abs(to.cx - from.cx) - requiredClearance);
  if (widthBudget < 64) return null;
  const widths = [from.width, to.width];
  let excess = widths[0] + widths[1] - widthBudget;
  for (const index of widths[0] >= widths[1] ? [0, 1] : [1, 0]) {
    const reduction = Math.min(excess, widths[index] - 32);
    widths[index] -= reduction;
    excess -= reduction;
  }
  if (excess > 0.0001) return null;
  const candidates = [from, to];
  const labelsFit = candidates.every((node, index) => (
    textUnits(node.label) * 6.8 <= widths[index] + 6
    && (!node.sublabel || minimumNodeTextWidth(node.sublabel, nodeTextFit.sublabelMinimum) <= availableNodeTextWidth(widths[index]))
    && (!node.tag || minimumNodeTextWidth(node.tag, nodeTextFit.tagMinimum) <= availableNodeTextWidth(widths[index]))
  ));
  if (!labelsFit) return null;
  const serializedWidths = widths.map((width) => Math.floor((width + 1e-9) * 100) / 100);
  const signedClearance = Math.abs(to.cx - from.cx)
    - serializedWidths[0] / 2 - serializedWidths[1] / 2;
  if (signedClearance + 0.0001 < requiredClearance) return null;
  const accepted = acceptsFix((document) => {
    document.nodes.find((node) => node.id === from.id).width = serializedWidths[0];
    document.nodes.find((node) => node.id === to.id).width = serializedWidths[1];
  });
  return accepted ? serializedWidths : null;
}

function enforceLegacyColumnCapacity() {
  if (workflow.schema_version !== 1) return;
  for (const edge of workflow.edges) {
    const from = nodes.get(edge.from);
    const to = nodes.get(edge.to);
    if (!from || !to || from.lane !== to.lane || from.col === to.col) continue;
    if (!verticalIntervalsOverlap(from, to, 8)) continue;
    const centerDistance = Math.abs(to.cx - from.cx);
    const actualSignedClearance = centerDistance - from.width / 2 - to.width / 2;
    const direct = !edge.via && ['auto', 'straight'].includes(edge.route || 'auto')
      && Math.abs(from.cy - to.cy) < 0.0001;
    const requiredDirectClearance = direct ? 28 : 8;
    if (actualSignedClearance >= requiredDirectClearance) continue;
    const alternative = verifiedLegacyAlternative(edge, from, to, requiredDirectClearance);
    const reducedWidths = verifiedReducedWidths(from, to, requiredDirectClearance);
    const capacity = actualSignedClearance < 0
      ? `${Math.abs(Math.round(actualSignedClearance))}px 重なる状態です`
      : `直接間隔が ${Math.round(actualSignedClearance)}px しかありません`;
    const message = `fixed-v1 レイアウトでは、ワークフローの列 ${from.col}→${to.col} に配置されたノード "${from.id}" と "${to.id}" は${capacity}。`;
    const supportedFixes = [];
    if (readableMigrationProvidesCapacity(from, to, requiredDirectClearance)) {
      supportedFixes.push('このワークフローを schema_version 2 へ移行する');
    }
    if (alternative !== null) supportedFixes.push(`ノード "${to.id}" を検証済みの空き列 ${alternative} へ移動する`);
    if (reducedWidths) {
      supportedFixes.push(`ノード幅を "${from.id}"=${Math.round(reducedWidths[0] * 100) / 100}px、"${to.id}"=${Math.round(reducedWidths[1] * 100) / 100}px に設定する`);
    }
    throwDiagnosticError(message, [{
      code: 'workflow/column-capacity',
      severity: 'error',
      message,
      subject: {
        diagramType: 'workflow',
        edge: edge.id ?? null,
        from: edge.from,
        to: edge.to,
        fromCol: from.col,
        toCol: to.col,
      },
      evidence: {
        centerDistancePx: centerDistance,
        nodeWidthsPx: [from.width, to.width],
        actualSignedClearancePx: actualSignedClearance,
        requiredDirectClearancePx: requiredDirectClearance,
      },
      supportedFixes,
      suppresses: [
        'workflow/short-edge',
        'clean-flow/endpoint-side-direction',
        'workflow/label-node-overlap',
      ],
    }]);
  }
}

function verifiedEdgeFix(edge, message, mutator) {
  const edgeIndex = workflow.edges.indexOf(edge);
  if (edgeIndex < 0) return null;
  const accepted = acceptsFix((document) => mutator(document.edges[edgeIndex], document));
  return accepted ? message : null;
}

function verifiedAutomaticRouteFix(edge, { clearSides = false } = {}) {
  const edgeName = workflowEdgeName(edge);
  return verifiedEdgeFix(
    edge,
    clearSides
      ? `readable-v2 が検証済みの自動候補を使用できるよう、エッジ "${edgeName}" から明示的な経路形状と端点側面を削除する`
      : `readable-v2 が検証済みの自動候補を使用できるよう、エッジ "${edgeName}" から明示的な経路形状を削除する`,
    (candidate) => {
      delete candidate.via;
      delete candidate.channelX;
      delete candidate.channelY;
      delete candidate.route;
      if (clearSides) {
        delete candidate.fromSide;
        delete candidate.toSide;
      }
    },
  );
}

function authoredPinEvidence(edge, field) {
  const authoredEdgeIndex = sourceIndexes.edges.get(edge);
  const value = Array.isArray(edge[field])
    ? edge[field].map((item) => (Array.isArray(item) ? [...item] : item))
    : edge[field];
  return {
    edge: workflowEdgeName(edge),
    field,
    ...(Number.isInteger(authoredEdgeIndex) ? { path: `/edges/${authoredEdgeIndex}/${field}` } : {}),
    value,
  };
}

function combinations(values, size, start = 0, prefix = [], output = []) {
  if (prefix.length === size) {
    output.push([...prefix]);
    return output;
  }
  for (let index = start; index <= values.length - (size - prefix.length); index += 1) {
    prefix.push(values[index]);
    combinations(values, size, index + 1, prefix, output);
    prefix.pop();
  }
  return output;
}

function verifiedPinRemovalAlternatives(edge, fields, reason) {
  if (!discoverFixes) return { removalSets: [], supportedFixes: [] };
  const edgeIndex = workflow.edges.indexOf(edge);
  if (edgeIndex < 0) return { removalSets: [], supportedFixes: [] };
  const uniqueFields = [...new Set(fields.filter((field) => edge[field] !== undefined))];
  for (let size = 1; size <= uniqueFields.length; size += 1) {
    const removalSets = combinations(uniqueFields, size).filter((fieldSet) => (
      acceptsFix((document) => {
        for (const field of fieldSet) delete document.edges[edgeIndex][field];
      })
    ));
    if (!removalSets.length) continue;
    const edgeName = workflowEdgeName(edge);
    return {
      removalSets,
      supportedFixes: removalSets.map((fieldSet) => (
        `エッジ "${edgeName}" から ${fieldSet.join(' と ')} を削除する${reason}`
      )),
    };
  }
  return { removalSets: [], supportedFixes: [] };
}

function conflictPinsFromRemovalSets(edge, removalSets, fallbackFields = []) {
  const fields = removalSets.length
    ? [...new Set(removalSets.flat())]
    : [...new Set(fallbackFields)];
  return fields.map((field) => authoredPinEvidence(edge, field));
}

function authoredRouteAssertionFields(edge) {
  return [
    ...(Array.isArray(edge?.via) ? ['via'] : []),
    ...(edge?.channelX !== undefined ? ['channelX'] : []),
    ...(edge?.channelY !== undefined ? ['channelY'] : []),
    ...(edge?.route && edge.route !== 'auto' ? ['route'] : []),
    ...(edge?.fromSide && edge.fromSide !== 'auto' ? ['fromSide'] : []),
    ...(edge?.toSide && edge.toSide !== 'auto' ? ['toSide'] : []),
  ];
}

function hasAuthoredRouteAssertions(edge) {
  return authoredRouteAssertionFields(edge).length > 0;
}

function verifiedPinReferenceAlternatives(candidateRefs, reason) {
  const seenRefs = new Set();
  const refs = candidateRefs.filter(({ edge, edgeIndex, field }) => {
    if (edgeIndex < 0 || edge?.[field] === undefined) return false;
    const key = `${edgeIndex}:${field}`;
    if (seenRefs.has(key)) return false;
    seenRefs.add(key);
    return true;
  });
  const fallbackPins = refs.map(({ edge, field }) => authoredPinEvidence(edge, field));
  if (!discoverFixes) {
    return {
      removalSets: [], conflictingRefs: refs, conflictingPins: fallbackPins, repairs: [], supportedFixes: [],
    };
  }

  for (let size = 1; size <= refs.length; size += 1) {
    const removalSets = combinations(refs, size).filter((removalSet) => (
      acceptsFix((document) => {
        for (const { edgeIndex, field } of removalSet) delete document.edges[edgeIndex][field];
      })
    ));
    if (!removalSets.length) continue;
    const conflictingRefs = [];
    const conflictingPins = [];
    const seenPins = new Set();
    for (const removalSet of removalSets) {
      for (const { edge, field } of removalSet) {
        const key = `${workflow.edges.indexOf(edge)}:${field}`;
        if (seenPins.has(key)) continue;
        seenPins.add(key);
        conflictingRefs.push({ edge, edgeIndex: workflow.edges.indexOf(edge), field });
        conflictingPins.push(authoredPinEvidence(edge, field));
      }
    }
    const repairs = removalSets.map((removalSet) => {
      const grouped = [];
      for (const ref of removalSet) {
        let group = grouped.find(({ edge }) => edge === ref.edge);
        if (!group) {
          group = { edge: ref.edge, fields: [] };
          grouped.push(group);
        }
        group.fields.push(ref.field);
      }
      const removals = grouped.map(({ edge, fields }) => (
        `エッジ "${workflowEdgeName(edge)}" から ${fields.join(' と ')} を削除する`
      ));
      return { removalSet, message: `${removals.join('、')}。${reason}` };
    });
    return {
      removalSets,
      conflictingRefs,
      conflictingPins,
      repairs,
      supportedFixes: repairs.map(({ message }) => message),
    };
  }
  return {
    removalSets: [], conflictingRefs: refs, conflictingPins: fallbackPins, repairs: [], supportedFixes: [],
  };
}

function verifiedRoutePairPinAlternatives(leftEdge, rightEdge, reason) {
  const refs = [leftEdge, rightEdge].flatMap((edge) => {
    const edgeIndex = workflow.edges.indexOf(edge);
    return authoredRouteAssertionFields(edge).map((field) => ({ edge, edgeIndex, field }));
  });
  return verifiedPinReferenceAlternatives(refs, reason);
}

function verifiedLabelRoutePinAlternatives(labelEdge, routeEdge) {
  const refs = [];
  const labelEdgeIndex = workflow.edges.indexOf(labelEdge);
  if (Array.isArray(labelEdge?.labelAt)) {
    refs.push({ edge: labelEdge, edgeIndex: labelEdgeIndex, field: 'labelAt' });
  }
  const routeEdgeIndex = workflow.edges.indexOf(routeEdge);
  for (const field of authoredRouteAssertionFields(routeEdge)) {
    refs.push({ edge: routeEdge, edgeIndex: routeEdgeIndex, field });
  }
  return verifiedPinReferenceAlternatives(
    refs,
    Array.isArray(labelEdge?.labelAt)
      ? 'ことで、readable-v2 が残りの作成済みラベル・経路固定値を再計画できるようにする'
      : 'ことで、readable-v2 が残りの作成済み経路指定を再計画できるようにする',
  );
}

function verifiedLabelPairPinAlternatives(leftEdge, rightEdge) {
  return verifiedPinReferenceAlternatives(
    [leftEdge, rightEdge].flatMap((edge) => (
      Array.isArray(edge?.labelAt)
        ? [{ edge, edgeIndex: workflow.edges.indexOf(edge), field: 'labelAt' }]
        : []
    )),
    'ことで、readable-v2 が残りの作成済みラベル固定値を再計画できるようにする',
  );
}

function verifiedRepairsWithLabelNudges(alternatives) {
  return alternatives.repairs.flatMap(({ removalSet, message }) => {
    if (removalSet.length !== 1 || removalSet[0].field !== 'labelAt') return [message];
    const nudges = verifiedLabelAtAlternatives(removalSet[0].edge);
    return nudges.length ? nudges : [message];
  });
}

function throwExplicitPinConflict(edge, invariant, evidence, supportedFixes = []) {
  const message = `ワークフローエッジ "${workflowEdgeName(edge)}" の明示的な形状が「${invariant}」に違反しています。`;
  const [onlyPin] = asArray(evidence?.conflictingPins);
  const authoredEdgeIndex = sourceIndexes.edges.get(edge);
  const pinPath = asArray(evidence?.conflictingPins).length === 1
    && Number.isInteger(authoredEdgeIndex)
    && onlyPin?.field
    ? onlyPin.path || `/edges/${authoredEdgeIndex}/${onlyPin.field}`
    : null;
  throwDiagnosticError(message, [{
    code: 'workflow/explicit-pin-conflict',
    severity: 'error',
    message,
    subject: {
      diagramType: 'workflow',
      edge: edge.id ?? null,
      from: edge.from,
      to: edge.to,
      ...(pinPath ? { path: pinPath } : {}),
    },
    evidence: { invariant, ...evidence },
    supportedFixes: supportedFixes.filter(Boolean),
  }]);
}

function hasAbsoluteRoutePins(edge) {
  return Array.isArray(edge?.via)
    || edge?.channelX !== undefined
    || edge?.channelY !== undefined;
}

function presentRouteGeometryFields(edge) {
  return [
    ...(Array.isArray(edge?.via) ? ['via'] : []),
    ...(edge?.channelX !== undefined ? ['channelX'] : []),
    ...(edge?.channelY !== undefined ? ['channelY'] : []),
  ];
}

function verifiedRouteGeometryPinAlternatives(
  edge,
  reason = 'ことで、readable-v2 が残りの明示的な経路指定を再計画できるようにする',
) {
  const edgeIndex = workflow.edges.indexOf(edge);
  return verifiedPinReferenceAlternatives(
    authoredRouteAssertionFields(edge).map((field) => ({ edge, edgeIndex, field })),
    reason,
  );
}

function properOrthogonalIntersection(leftStart, leftEnd, rightStart, rightEnd) {
  const leftOrientation = segmentOrientation(leftStart, leftEnd);
  const rightOrientation = segmentOrientation(rightStart, rightEnd);
  if (leftOrientation === rightOrientation
    || leftOrientation === 'diagonal'
    || rightOrientation === 'diagonal') return null;
  const horizontalStart = leftOrientation === 'horizontal' ? leftStart : rightStart;
  const horizontalEnd = leftOrientation === 'horizontal' ? leftEnd : rightEnd;
  const verticalStart = leftOrientation === 'vertical' ? leftStart : rightStart;
  const verticalEnd = leftOrientation === 'vertical' ? leftEnd : rightEnd;
  const point = [verticalStart[0], horizontalStart[1]];
  const epsilon = 0.0001;
  const insideHorizontal = point[0] > Math.min(horizontalStart[0], horizontalEnd[0]) + epsilon
    && point[0] < Math.max(horizontalStart[0], horizontalEnd[0]) - epsilon;
  const insideVertical = point[1] > Math.min(verticalStart[1], verticalEnd[1]) + epsilon
    && point[1] < Math.max(verticalStart[1], verticalEnd[1]) - epsilon;
  return insideHorizontal && insideVertical ? point : null;
}

function verifiedLabelAtAlternatives(edge) {
  if (!Array.isArray(edge.labelAt)) return [];
  const [x, y] = edge.labelAt;
  return [
    [0, 24], [0, -24], [24, 0], [-24, 0],
    [0, 48], [0, -48], [48, 0], [-48, 0],
  ].map(([dx, dy]) => {
    const next = [x + dx, y + dy];
    return verifiedEdgeFix(
      edge,
      `エッジ "${workflowEdgeName(edge)}" の labelAt を [${next[0]}, ${next[1]}] に設定する`,
      (candidate) => { candidate.labelAt = next; },
    );
  }).filter(Boolean);
}

function verifiedLabelAtNudge(edge) {
  const [alternative] = verifiedLabelAtAlternatives(edge);
  if (alternative) return alternative;
  return verifiedEdgeFix(
    edge,
    `readable-v2 が検証済みの自動ラベル配置を使用できるよう、エッジ "${workflowEdgeName(edge)}" から labelAt を削除する`,
    (candidate) => { delete candidate.labelAt; },
  );
}

function throwReadableLabelRoutePinConflict(hit, routePoints = null) {
  const labelEdge = hit.labelRelation;
  const routeEdge = hit.otherRelation;
  const labelPinned = Array.isArray(labelEdge?.labelAt);
  const routePinned = hasAuthoredRouteAssertions(routeEdge);
  if (!labelPinned && !routePinned) return false;
  const alternatives = verifiedLabelRoutePinAlternatives(labelEdge, routeEdge);
  const actualRoutePoints = routePoints
    || pathCache.get(routeEdge)?.points
    || pathFor(routeEdge).points;
  const diagnosticEdge = alternatives.conflictingRefs[0]?.edge
    || (labelPinned ? labelEdge : routeEdge);
  throwExplicitPinConflict(diagnosticEdge, '明示的なラベルと経路の間隔', {
    conflictingPins: alternatives.conflictingPins,
    ...(labelPinned ? { labelAt: [...labelEdge.labelAt] } : {}),
    labelRect: {
      x: hit.rect.x,
      y: hit.rect.y,
      width: hit.rect.width,
      height: hit.rect.height,
    },
    collidedRoute: {
      edge: routeEdge.id || `${routeEdge.from}->${routeEdge.to}`,
      from: routeEdge.from,
      to: routeEdge.to,
      points: actualRoutePoints.map((point) => [...point]),
    },
    routeSegmentIndex: hit.segmentIndex,
    routeSegment: { from: [...hit.start], to: [...hit.end] },
    clearancePx: Math.round(hit.clearance * 10) / 10,
    minimumPx: hit.threshold,
  }, [
    ...verifiedRepairsWithLabelNudges(alternatives),
  ]);
  return true;
}

function throwReadableLabelLabelPinConflict(left, right) {
  const leftEdge = left.relation;
  const rightEdge = right.relation;
  const pinnedEdges = [leftEdge, rightEdge].filter((edge) => Array.isArray(edge?.labelAt));
  if (!pinnedEdges.length) return false;
  const alternatives = verifiedLabelPairPinAlternatives(leftEdge, rightEdge);
  const causalLabelEdges = [...new Set(alternatives.conflictingRefs.map(({ edge }) => edge))];
  const diagnosticEdge = causalLabelEdges[0] || pinnedEdges[0];
  throwExplicitPinConflict(diagnosticEdge, '明示的なラベル間の間隔', {
    conflictingPins: alternatives.conflictingPins,
    labelRects: [left, right].map((rect) => ({
      edge: rect.relation.id ?? null,
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    })),
    minimumGapPx: -2,
  }, verifiedRepairsWithLabelNudges(alternatives));
  return true;
}

function classifyFailedAutomaticCandidatePins(edge, rawCandidates) {
  const relationIndex = workflow.edges.indexOf(edge);
  const priorRoutes = [...pathCache.entries()]
    .filter(([otherEdge]) => otherEdge !== edge)
    .map(([relation, routed]) => ({
      relation,
      relationIndex: workflow.edges.indexOf(relation),
      points: routed.points,
    }));
  if (!priorRoutes.length) return;
  const priorLabels = priorRoutes.map(({ relation, relationIndex }) => (
    labelRectFor(relation, relationIndex)
  )).filter(Boolean);

  for (const { points } of rawCandidates) {
    const candidateRect = candidateLabelRect(edge, points);
    const candidateLabel = candidateRect
      ? { ...candidateRect, relation: edge, relationIndex, label: edge.label }
      : null;
    if (candidateLabel) {
      const priorLabel = priorLabels.find((otherLabel) => (
        rectsOverlap(candidateLabel, otherLabel, -2)
        && (Array.isArray(edge.labelAt) || Array.isArray(otherLabel.relation?.labelAt))
      ));
      if (priorLabel) throwReadableLabelLabelPinConflict(candidateLabel, priorLabel);

      const labelRouteHit = collectLabelRouteClearance({
        labels: [candidateLabel],
        routedRelations: priorRoutes,
        threshold: 4,
      }).find((hit) => (
        Array.isArray(edge.labelAt) || hasAbsoluteRoutePins(hit.otherRelation)
      ));
      if (labelRouteHit) {
        const collidedRoute = priorRoutes.find(({ relation }) => relation === labelRouteHit.otherRelation);
        throwReadableLabelRoutePinConflict(labelRouteHit, collidedRoute?.points);
      }
    }

    const reverseHit = collectLabelRouteClearance({
      labels: priorLabels,
      routedRelations: [{ relation: edge, relationIndex, points }],
      threshold: 4,
    }).find((hit) => Array.isArray(hit.labelRelation?.labelAt));
    if (reverseHit) throwReadableLabelRoutePinConflict(reverseHit, points);
  }
}

function validateReadablePairwisePinConflicts() {
  const labels = workflow.edges.map((edge, relationIndex) => (
    labelRectFor(edge, relationIndex)
  )).filter(Boolean);
  const routedRelations = workflow.edges.map((edge, relationIndex) => (
    nodes.has(edge.from) && nodes.has(edge.to)
      ? { relation: edge, relationIndex, points: pathFor(edge).points }
      : null
  )).filter(Boolean);

  const labelRouteHit = collectLabelRouteClearance({
    labels,
    routedRelations,
    threshold: 4,
  }).find((hit) => (
    Array.isArray(hit.labelRelation?.labelAt) || hasAuthoredRouteAssertions(hit.otherRelation)
  ));
  if (labelRouteHit) throwReadableLabelRoutePinConflict(labelRouteHit);

  for (let leftIndex = 0; leftIndex < labels.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < labels.length; rightIndex += 1) {
      const left = labels[leftIndex];
      const right = labels[rightIndex];
      if (!rectsOverlap(left, right, -2)) continue;
      throwReadableLabelLabelPinConflict(left, right);
    }
  }

  const requestedProfile = workflow.meta?.quality_profile;
  if (requestedProfile !== 'showcase') return;
  for (let leftIndex = 0; leftIndex < routedRelations.length; leftIndex += 1) {
    const left = routedRelations[leftIndex];
    for (let rightIndex = leftIndex + 1; rightIndex < routedRelations.length; rightIndex += 1) {
      const right = routedRelations[rightIndex];
      const leftPinned = hasAuthoredRouteAssertions(left.relation);
      const rightPinned = hasAuthoredRouteAssertions(right.relation);
      if (!leftPinned && !rightPinned) continue;
      if ([left.relation.from, left.relation.to].some((id) => (
        id === right.relation.from || id === right.relation.to
      ))) continue;
      const leftAnalysis = forwardCollinearAnalysisSegments(left.points);
      const rightAnalysis = forwardCollinearAnalysisSegments(right.points);
      for (const leftSegment of leftAnalysis) {
        for (const rightSegment of rightAnalysis) {
          const point = properOrthogonalIntersection(
            leftSegment.start,
            leftSegment.end,
            rightSegment.start,
            rightSegment.end,
          );
          if (!point) continue;
          const leftSourceIndex = sourceSegmentIndexAtPoint(leftSegment, point);
          const rightSourceIndex = sourceSegmentIndexAtPoint(rightSegment, point);
          const leftSource = {
            from: left.points[leftSourceIndex],
            to: left.points[leftSourceIndex + 1],
          };
          const rightSource = {
            from: right.points[rightSourceIndex],
            to: right.points[rightSourceIndex + 1],
          };
          const alternatives = verifiedRoutePairPinAlternatives(
            left.relation,
            right.relation,
            'ことで、readable-v2 が残りの作成済み経路指定を再計画できるようにする',
          );
          const diagnosticEdge = leftPinned ? left.relation : right.relation;
          throwExplicitPinConflict(diagnosticEdge, '明示的な経路同士の交差', {
            conflictingPins: alternatives.conflictingPins,
            point,
            segmentIndex: leftSourceIndex,
            otherSegmentIndex: rightSourceIndex,
            routeSegments: [
              { edge: left.relation.id ?? null, from: [...leftSegment.start], to: [...leftSegment.end] },
              { edge: right.relation.id ?? null, from: [...rightSegment.start], to: [...rightSegment.end] },
            ],
            sourceRouteSegments: [
              { edge: left.relation.id ?? null, from: [...leftSource.from], to: [...leftSource.to] },
              { edge: right.relation.id ?? null, from: [...rightSource.from], to: [...rightSource.to] },
            ],
          }, alternatives.supportedFixes);
        }
      }
    }
  }

  const corridorHit = collectAmbiguousCorridors({
    routedRelations,
    minOverlapPx: 8,
  }).find((hit) => (
    hasAuthoredRouteAssertions(hit.left.relation)
    || hasAuthoredRouteAssertions(hit.right.relation)
  ));
  if (corridorHit) {
    const leftSegment = {
      from: corridorHit.left.points[corridorHit.leftSegment],
      to: corridorHit.left.points[corridorHit.leftSegment + 1],
    };
    const rightSegment = {
      from: corridorHit.right.points[corridorHit.rightSegment],
      to: corridorHit.right.points[corridorHit.rightSegment + 1],
    };
    const leftPinned = hasAuthoredRouteAssertions(corridorHit.left.relation);
    const alternatives = verifiedRoutePairPinAlternatives(
      corridorHit.left.relation,
      corridorHit.right.relation,
      'ことで、readable-v2 が残りの作成済み経路指定を再計画できるようにする',
    );
    const diagnosticEdge = leftPinned ? corridorHit.left.relation : corridorHit.right.relation;
    throwExplicitPinConflict(diagnosticEdge, '明示的な経路同士の経路帯間隔', {
      conflictingPins: alternatives.conflictingPins,
      segmentIndex: corridorHit.leftSegment,
      otherSegmentIndex: corridorHit.rightSegment,
      routeSegments: [
        {
          edge: corridorHit.left.relation.id ?? null,
          from: [...leftSegment.from],
          to: [...leftSegment.to],
        },
        {
          edge: corridorHit.right.relation.id ?? null,
          from: [...rightSegment.from],
          to: [...rightSegment.to],
        },
      ],
      overlapStart: [...corridorHit.overlapStart],
      overlapEnd: [...corridorHit.overlapEnd],
      overlapLengthPx: corridorHit.overlapLength,
      minimumClearancePx: 8,
    }, alternatives.supportedFixes);
  }
}

const READABLE_PRESET_PIN_FIELDS = Object.freeze({
  straight: [],
  drop: ['channelY'],
  'outside-right': ['channelX'],
  'return-left': ['channelX'],
  'bottom-channel': ['channelY'],
  'up-channel': ['channelY'],
});

function presentChannelPins(edge) {
  return ['channelX', 'channelY'].filter((field) => edge[field] !== undefined);
}

function validateReadableRouteControls(edge) {
  const channelPins = presentChannelPins(edge);
  const preset = edge.route || 'auto';
  if (preset === 'auto') return;
  const allowedPins = new Set(READABLE_PRESET_PIN_FIELDS[preset] || []);
  const conflictingPins = channelPins.filter((field) => !allowedPins.has(field));
  if (!conflictingPins.length) return;
  const edgeIndex = workflow.edges.indexOf(edge);
  const alternatives = verifiedPinReferenceAlternatives([
    { edge, edgeIndex, field: 'route' },
    ...conflictingPins.map((field) => ({ edge, edgeIndex, field })),
  ], 'ことで、残りの検証済み経路指定を維持する');
  throwExplicitPinConflict(edge, '経路プリセットの互換性', {
    route: preset,
    allowedPins: [...allowedPins],
    conflictingPins: alternatives.conflictingPins,
  }, alternatives.supportedFixes);
}

function segmentOrientation(start, end) {
  if (Math.abs(start[0] - end[0]) <= 0.0001) return 'vertical';
  if (Math.abs(start[1] - end[1]) <= 0.0001) return 'horizontal';
  return 'diagonal';
}

function routeSegments(points) {
  return points.slice(0, -1).map((start, index) => ({
    start,
    end: points[index + 1],
    orientation: segmentOrientation(start, points[index + 1]),
  }));
}

function endpointSideIsHonored(points, side, endpoint) {
  if (!side || side === 'auto' || points.length < 2) return true;
  const source = endpoint === 'source';
  const from = source ? points[0] : points.at(-2);
  const to = source ? points[1] : points.at(-1);
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  if (source) {
    if (side === 'right') return dx > 0 && Math.abs(dy) <= 0.0001;
    if (side === 'left') return dx < 0 && Math.abs(dy) <= 0.0001;
    if (side === 'bottom') return dy > 0 && Math.abs(dx) <= 0.0001;
    if (side === 'top') return dy < 0 && Math.abs(dx) <= 0.0001;
    return false;
  }
  if (side === 'right') return dx < 0 && Math.abs(dy) <= 0.0001;
  if (side === 'left') return dx > 0 && Math.abs(dy) <= 0.0001;
  if (side === 'bottom') return dy < 0 && Math.abs(dx) <= 0.0001;
  if (side === 'top') return dy > 0 && Math.abs(dx) <= 0.0001;
  return false;
}

function corridorTopologyMatches(points, axis, coordinate) {
  const collapsed = normalizeRoutePoints(points.map((point) => [...point]));
  const start = collapsed[0];
  const end = collapsed.at(-1);
  const via = axis === 'x'
    ? [[coordinate, start[1]], [coordinate, end[1]]]
    : [[start[0], coordinate], [end[0], coordinate]];
  const expected = normalizeRoutePoints([start, ...via, end]);
  const actualPattern = routeSegments(collapsed).map(({ orientation }) => orientation);
  const expectedPattern = routeSegments(expected).map(({ orientation }) => orientation);
  return actualPattern.length === expectedPattern.length
    && actualPattern.every((orientation, index) => orientation === expectedPattern[index])
    && routeContainsChannelPin(
      collapsed,
      axis === 'x' ? 'channelX' : 'channelY',
      coordinate,
    );
}

function routeMatchesPresetFamily(preset, points, from, to) {
  const collapsed = normalizeRoutePoints(points.map((point) => [...point]));
  const segments = routeSegments(collapsed);
  if (preset === 'straight') return collapsed.length === 2;
  if (preset === 'drop') {
    if (from.lane === to.lane) return false;
    if (collapsed.length === 2 && segments[0]?.orientation === 'vertical') return true;
    const upper = from.cy <= to.cy ? from : to;
    const lower = upper === from ? to : from;
    return segments.some(({ start, orientation }) => (
      orientation === 'horizontal'
      && start[1] >= upper.y + upper.height - 0.0001
      && start[1] <= lower.y + 0.0001
      && corridorTopologyMatches(points, 'y', start[1])
    ));
  }
  if (preset === 'outside-right' || preset === 'return-left') {
    const boundary = preset === 'outside-right'
      ? Math.max(from.x + from.width, to.x + to.width)
      : Math.min(from.x, to.x);
    return segments.some(({ start, orientation }) => (
      orientation === 'vertical'
      && (preset === 'outside-right'
        ? start[0] > boundary + 0.0001
        : start[0] < boundary - 0.0001)
      && corridorTopologyMatches(points, 'x', start[0])
    ));
  }
  if (preset === 'bottom-channel' || preset === 'up-channel') {
    const boundary = preset === 'bottom-channel'
      ? Math.max(from.y + from.height, to.y + to.height)
      : Math.min(from.y, to.y);
    return segments.some(({ start, orientation }) => (
      orientation === 'horizontal'
      && (preset === 'bottom-channel'
        ? start[1] > boundary + 0.0001
        : start[1] < boundary - 0.0001)
      && corridorTopologyMatches(points, 'y', start[1])
    ));
  }
  return false;
}

function routeContainsChannelPin(points, field, value) {
  return points.slice(0, -1).some((start, index) => {
    const end = points[index + 1];
    if (field === 'channelX') {
      return start[0] === value
        && end[0] === value
        && Math.abs(end[1] - start[1]) > 0.0001;
    }
    return start[1] === value
      && end[1] === value
      && Math.abs(end[0] - start[0]) > 0.0001;
  });
}

function validateReadablePinnedGeometry() {
  if (workflow.schema_version !== 2) return;
  for (const edge of workflow.edges) {
    if (!nodes.has(edge.from) || !nodes.has(edge.to)) continue;
    validateReadableRouteControls(edge);
    const edgeName = workflowEdgeName(edge);
    const edgeIndex = sourceIndexes.edges.get(edge);
    if (Array.isArray(edge.labelAt)) {
      const rect = labelRectFor(edge, workflow.edges.indexOf(edge));
      if (rect && (rect.x < 0 || rect.y < 0)) {
        throwExplicitPinConflict(edge, 'viewBox 原点内への収容', {
          conflictingPins: [{
            edge: edgeName,
            field: 'labelAt',
            path: `/edges/${edgeIndex}/labelAt`,
            value: [...edge.labelAt],
          }],
          offendingRect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          minimumCoordinate: 0,
        }, [verifiedLabelAtNudge(edge)]);
      }
    }
    const negativeViaIndex = asArray(edge.via).findIndex(([x, y]) => x < 0 || y < 0);
    const negativeRoutePin = negativeViaIndex >= 0
      ? {
          field: 'via',
          path: `/edges/${edgeIndex}/via/${negativeViaIndex}`,
          value: [...edge.via[negativeViaIndex]],
        }
      : edge.channelX < 0
        ? { field: 'channelX', path: `/edges/${edgeIndex}/channelX`, value: edge.channelX }
        : edge.channelY < 0
          ? { field: 'channelY', path: `/edges/${edgeIndex}/channelY`, value: edge.channelY }
          : null;
    if (negativeRoutePin) {
      throwExplicitPinConflict(edge, 'viewBox 原点内への収容', {
        conflictingPins: [{ edge: edgeName, ...negativeRoutePin }],
        minimumCoordinate: 0,
      }, [
        verifiedAutomaticRouteFix(edge),
        verifiedAutomaticRouteFix(edge, { clearSides: true }),
      ]);
    }
    const hasPinnedRoute = Array.isArray(edge.via)
      || edge.channelX !== undefined
      || edge.channelY !== undefined;
    const points = pathFor(edge).points;
    if (hasPinnedRoute) {
      const invalidPointIndex = points.findIndex((point) => (
        !Array.isArray(point) || point.length !== 2 || !isFinitePoint(...point)
      ));
      if (invalidPointIndex !== -1) {
        const alternatives = verifiedRouteGeometryPinAlternatives(edge);
        throwExplicitPinConflict(edge, '有限な経路座標', {
          conflictingPins: alternatives.conflictingPins,
          pointIndex: invalidPointIndex,
          point: points[invalidPointIndex],
        }, alternatives.supportedFixes);
      }
      for (let segmentIndex = 0; segmentIndex < points.length - 1; segmentIndex += 1) {
        const start = points[segmentIndex];
        const end = points[segmentIndex + 1];
        const dx = Math.abs(end[0] - start[0]);
        const dy = Math.abs(end[1] - start[1]);
        if (dx <= 0.0001 && dy <= 0.0001) {
          const duplicateFix = Array.isArray(edge.via) && edge.via.length
            ? verifiedEdgeFix(
              edge,
              `重複する via[${Math.min(segmentIndex, edge.via.length - 1)}] を削除し、残りの作成済み固定値は変更しない`,
              (candidate) => candidate.via.splice(Math.min(segmentIndex, candidate.via.length - 1), 1),
            )
            : verifiedAutomaticRouteFix(edge);
          const alternatives = Array.isArray(edge.via)
            ? null
            : verifiedRouteGeometryPinAlternatives(edge);
          throwExplicitPinConflict(edge, '長さが0ではない経路セグメント', {
            conflictingPins: alternatives?.conflictingPins
              || [authoredPinEvidence(edge, 'via')],
            segmentIndex,
            from: start,
            to: end,
          }, alternatives?.supportedFixes || [duplicateFix]);
        }
        if (dx > 0.0001 && dy > 0.0001) {
          const alternatives = verifiedRouteGeometryPinAlternatives(edge);
          throwExplicitPinConflict(edge, '直交する経路セグメント', {
            conflictingPins: alternatives.conflictingPins,
            segmentIndex,
            from: start,
            to: end,
          }, alternatives.supportedFixes);
        }
        const endpoint = segmentIndex === 0 || segmentIndex === points.length - 2;
        const minimumPx = points.length === 2 ? 28 : endpoint ? 8 : 16;
        const lengthPx = dx + dy;
        if (lengthPx + 0.0001 < minimumPx) {
          const alternatives = verifiedRouteGeometryPinAlternatives(edge);
          throwExplicitPinConflict(edge, endpoint ? '8px の端点スタブ間隔' : '16px の内部曲がり間隔', {
            conflictingPins: alternatives.conflictingPins,
            segmentIndex,
            position: segmentIndex === 0 ? 'source-stub' : segmentIndex === points.length - 2 ? 'target-stub' : 'interior',
            from: start,
            to: end,
            lengthPx,
            minimumPx,
          }, alternatives.supportedFixes);
        }
      }
      const { fromSide, toSide } = edgeSides(edge);
      if (Array.isArray(edge.via)) {
        const missingChannelPins = presentChannelPins(edge).filter((field) => (
          !routeContainsChannelPin(points, field, edge[field])
        ));
        if (missingChannelPins.length) {
          const candidateFields = ['via', ...missingChannelPins];
          const alternatives = verifiedPinRemovalAlternatives(
            edge,
            candidateFields,
            'ことで、残りの明示的な経路指定を再計画する',
          );
          throwExplicitPinConflict(edge, 'チャネル固定値の保持', {
            route: edge.route || 'auto',
            conflictingPins: conflictPinsFromRemovalSets(
              edge,
              alternatives.removalSets,
              candidateFields,
            ),
            points: points.map((point) => [...point]),
          }, alternatives.supportedFixes);
        }
      }
      if (edge.route
        && edge.route !== 'auto'
        && !routeMatchesPresetFamily(
          edge.route,
          points,
          nodes.get(edge.from),
          nodes.get(edge.to),
        )) {
        const authoredEdgeIndex = workflow.edges.indexOf(edge);
        const alternatives = verifiedPinReferenceAlternatives([
          { edge, edgeIndex: authoredEdgeIndex, field: 'route' },
          ...presentRouteGeometryFields(edge)
            .map((field) => ({ edge, edgeIndex: authoredEdgeIndex, field })),
        ], 'ことで、残りの検証済み経路指定を維持する');
        throwExplicitPinConflict(edge, '経路プリセットの互換性', {
          route: edge.route,
          conflictingPins: alternatives.conflictingPins,
          points: points.map((point) => [...point]),
        }, alternatives.supportedFixes);
      }
      if (!routeHonorsEndpointSides(points, fromSide, toSide)) {
        const mismatchedSideFields = [
          ...(edge.fromSide && edge.fromSide !== 'auto'
            && !endpointSideIsHonored(points, fromSide, 'source') ? ['fromSide'] : []),
          ...(edge.toSide && edge.toSide !== 'auto'
            && !endpointSideIsHonored(points, toSide, 'target') ? ['toSide'] : []),
        ];
        const candidateFields = [
          ...mismatchedSideFields,
          ...presentRouteGeometryFields(edge),
        ];
        const alternatives = verifiedPinRemovalAlternatives(
          edge,
          candidateFields,
          'ことで、残りの明示的な固定値を再計画する',
        );
        throwExplicitPinConflict(edge, '端点側面に対する垂直方向', {
          conflictingPins: conflictPinsFromRemovalSets(
            edge,
            alternatives.removalSets,
            candidateFields,
          ),
          points: points.map((point) => [...point]),
          fromSide,
          toSide,
        }, alternatives.supportedFixes);
      }
      const nodeCollision = firstRouteNodeCollision(edge, points);
      if (nodeCollision) {
        const alternatives = verifiedRouteGeometryPinAlternatives(edge);
        throwExplicitPinConflict(edge, 'ノードとの間隔', {
          conflictingPins: alternatives.conflictingPins,
          ...nodeCollision,
        }, alternatives.supportedFixes);
      }
      const legendObstacle = workflowLegendRects().find((rect) => points.slice(0, -1).some((point, index) => (
        segmentIntersectsRect({ start: point, end: points[index + 1] }, rect)
      )));
      if (legendObstacle) {
        const alternatives = verifiedRouteGeometryPinAlternatives(edge);
        throwExplicitPinConflict(edge, '凡例との間隔', {
          conflictingPins: alternatives.conflictingPins,
          points: points.map((point) => [...point]),
          legendObstacle,
        }, alternatives.supportedFixes);
      }
      const compositionObstacle = workflowSceneLabelObstacles().find((rect) => (
        points.slice(0, -1).some((point, index) => (
          segmentIntersectsRect({ start: point, end: points[index + 1] }, rect)
        ))
      ));
      if (compositionObstacle) {
        const alternatives = verifiedRouteGeometryPinAlternatives(edge);
        throwExplicitPinConflict(edge, 'レーン／フェーズ／グループラベルとの間隔', {
          conflictingPins: alternatives.conflictingPins,
          points: points.map((point) => [...point]),
          compositionObstacle,
        }, alternatives.supportedFixes);
      }
      const [frameRun] = collectBorderRuns({
        routedRelations: [{ points }],
        frames: workflowCompositionFrames(),
      });
      if (frameRun) {
        const alternatives = verifiedRouteGeometryPinAlternatives(edge);
        throwExplicitPinConflict(edge, '構造フレーム境界との間隔', {
          conflictingPins: alternatives.conflictingPins,
          points: points.map((point) => [...point]),
          frame: frameRun.frame?.id ?? frameRun.frameIndex,
          side: frameRun.side,
          overlapLengthPx: frameRun.overlapLength,
        }, alternatives.supportedFixes);
      }
    }

    if (edge.labelAt) {
      const rect = labelRectFor(edge, workflow.edges.indexOf(edge));
      const obstacle = rect && [...nodes.values()].find((node) => rectsOverlap(rect, node, -2));
      if (obstacle) {
        throwExplicitPinConflict(edge, 'エッジラベルとノードの間隔', {
          conflictingPins: [authoredPinEvidence(edge, 'labelAt')],
          labelAt: [...edge.labelAt],
          labelRect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          obstacleNode: obstacle.id,
        }, [verifiedEdgeFix(
          edge,
          'readable-v2 が検証済みの自動ラベル配置を使用できるよう labelAt を削除する',
          (candidate) => { delete candidate.labelAt; },
        )]);
      }
      const legendObstacle = rect && workflowLegendRects().find((legendRect) => (
        rectsOverlap(rect, legendRect)
      ));
      if (legendObstacle) {
        throwExplicitPinConflict(edge, 'エッジラベルと凡例の間隔', {
          conflictingPins: [authoredPinEvidence(edge, 'labelAt')],
          labelAt: [...edge.labelAt],
          labelRect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          legendObstacle,
        }, [verifiedEdgeFix(
          edge,
          'readable-v2 が検証済みの自動ラベル配置を使用できるよう labelAt を削除する',
          (candidate) => { delete candidate.labelAt; },
        )]);
      }
      const compositionObstacle = rect && workflowSceneLabelObstacles().find((candidate) => (
        rectsOverlap(rect, candidate)
      ));
      if (compositionObstacle) {
        throwExplicitPinConflict(edge, 'エッジラベルとレーン／フェーズ／グループの間隔', {
          conflictingPins: [authoredPinEvidence(edge, 'labelAt')],
          labelAt: [...edge.labelAt],
          labelRect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          compositionObstacle,
        }, [verifiedEdgeFix(
          edge,
          `readable-v2 が検証済みの自動ラベル配置を使用できるよう、エッジ "${workflowEdgeName(edge)}" から labelAt を削除する`,
          (candidate) => { delete candidate.labelAt; },
        )]);
      }
    }
  }
  validateReadablePairwisePinConflicts();
}

function validateWorkflow() {
  const problems = [];
  if (workflow.schema_version !== 1 && workflow.schema_version !== 2) {
    problems.push('ワークフローファイルの "schema_version" は 1 または 2 に設定する必要があります。');
  }
  if (workflow.diagram_type !== 'workflow') {
    problems.push(`diagram_type "${workflow.diagram_type}" はサポートされていません。"workflow" を指定してください。`);
  }
  if (!workflow.meta || !workflow.meta.title) {
    problems.push('ワークフローファイルには meta.title が必要です。');
  }
  if (!Array.isArray(workflow.lanes) || !workflow.lanes.length) {
    problems.push('ワークフローファイルには1つ以上のレーンが必要です。');
  }
  if (!Array.isArray(workflow.nodes)) {
    problems.push('ワークフローファイルには nodes 配列が必要です。');
  }
  if (!Array.isArray(workflow.edges)) {
    problems.push('ワークフローファイルには edges 配列が必要です。');
  }
  if (workflow.phases !== undefined && !Array.isArray(workflow.phases)) {
    problems.push('ワークフローの "phases" は配列である必要があります。');
  }
  if (workflow.groups !== undefined && !Array.isArray(workflow.groups)) {
    problems.push('ワークフローの "groups" は配列である必要があります。');
  }
  if (workflow.mainPath !== undefined && !Array.isArray(workflow.mainPath)) {
    problems.push('ワークフローの "mainPath" はノード id の配列である必要があります。');
  }
  if (workflow.cards !== undefined && !Array.isArray(workflow.cards)) {
    problems.push('ワークフローの "cards" は配列である必要があります。');
  }
  if (problems.length) {
    throwDiagnosticProblems('ワークフローのレイアウト検証に失敗しました', problems, {
      subject: { diagramType: 'workflow' },
    });
  }

  enforceLegacyColumnCapacity();

  const laneIds = new Set(workflow.lanes.map((lane) => lane.id));
  if (laneIds.size !== workflow.lanes.length) {
    problems.push('レーンの id は一意である必要があります。');
  }
  if (nodes.size !== workflow.nodes.length) {
    problems.push('ノードの id は一意である必要があります。');
  }
  const phaseIds = new Set(asArray(workflow.phases).map((phase) => phase.id));
  if (phaseIds.size !== asArray(workflow.phases).length) {
    problems.push('フェーズの id は一意である必要があります。');
  }
  const groupIds = new Set(asArray(workflow.groups).map((group) => group.id));
  if (groupIds.size !== asArray(workflow.groups).length) {
    problems.push('グループの id は一意である必要があります。');
  }

  for (const node of nodes.values()) {
    if (!laneIds.has(node.lane)) {
      problems.push(`ノード "${node.id}" が不明なレーン "${node.lane}" を使用しています。`);
      continue;
    }
    if (!Number.isInteger(node.col) || node.col < 0 || node.col >= layout.colXs.length) {
      problems.push(`ノード "${node.id}" の列 ${node.col} は無効です。有効な整数列は 0..${layout.colXs.length - 1} です。`);
      continue;
    }
    if (!isFinitePoint(node.x, node.y, node.cx, node.cy)) {
      problems.push(`ノード "${node.id}" の座標が有限値ではありません。col、width、height、yOffset が数値であることを確認してください。`);
      continue;
    }
    const estLabelW = textUnits(node.label) * 6.8;
    if (estLabelW > node.width + 6) {
      problems.push(`ラベル "${node.label}"（約 ${Math.round(estLabelW)}px）がノード "${node.id}"（${node.width}px）より広くなっています。ラベルを短くするか node.width を増やしてください。`);
    }
    const brandRailProblem = brandTopRailProblem(node, node.width, nodeTextFit.labelMinimum);
    if (brandRailProblem) problems.push(brandRailProblem);
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

    const top = laneTop(node.lane);
    const contentTop = top + layout.laneTitleH + laneGroupHeaderH(node.lane);
    const laneRight = layout.laneX + layout.laneW;
    if (node.x < layout.laneX || node.x + node.width > laneRight) {
      problems.push(`ノード "${node.id}" がレーン "${node.lane}" の水平方向の範囲を超えています。`);
    }
    if (node.y < contentTop || node.y + node.height > top + laneHeight(node.lane)) {
      problems.push(`ノード "${node.id}" がレーン "${node.lane}" のタイトルまたは境界と衝突しています。`);
    }
  }

  const phaseRanges = [];
  for (const phase of asArray(workflow.phases)) {
    if (!Number.isInteger(phase.fromCol) || !Number.isInteger(phase.toCol)) {
      problems.push(`フェーズ "${phase.id}" の fromCol/toCol は整数である必要があります。`);
      continue;
    }
    if (phase.fromCol < 0 || phase.toCol >= layout.colXs.length || phase.fromCol > phase.toCol) {
      problems.push(`フェーズ "${phase.id}" の列 ${phase.fromCol}..${phase.toCol} は無効です。0..${layout.colXs.length - 1} の範囲内で昇順に指定してください。`);
    } else {
      phaseRanges.push(phase);
    }
    const estLabelW = textUnits(phase.label) * 5.6;
    const width = phaseSpan(phase).width;
    if (estLabelW > width + 8) {
      problems.push(`フェーズラベル "${phase.label}"（約 ${Math.round(estLabelW)}px）が対象範囲 ${Math.round(width)}px より広くなっています。ラベルを短くするかフェーズ範囲を広げてください。`);
    }
  }
  phaseRanges.sort((a, b) => a.fromCol - b.fromCol || a.toCol - b.toCol);
  for (let i = 0; i < phaseRanges.length; i += 1) {
    for (let j = i + 1; j < phaseRanges.length; j += 1) {
      const earlier = phaseRanges[i];
      const later = phaseRanges[j];
      if (later.fromCol > earlier.toCol) break;
      problems.push(`フェーズ "${later.id}"（${later.fromCol}..${later.toCol}）がフェーズ "${earlier.id}"（${earlier.fromCol}..${earlier.toCol}）と重なっています。col ${earlier.toCol + 1} 以降から開始するか、前のフェーズを col ${later.fromCol - 1} までに終了してください。`);
    }
  }

  for (const group of asArray(workflow.groups)) {
    if (!laneIds.has(group.lane)) {
      problems.push(`グループ "${group.id}" が不明なレーン "${group.lane}" を使用しています。`);
      continue;
    }
    if (!Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)) {
      problems.push(`グループ "${group.id}" の fromCol/toCol は整数である必要があります。`);
      continue;
    }
    if (group.fromCol < 0 || group.toCol >= layout.colXs.length || group.fromCol > group.toCol) {
      problems.push(`グループ "${group.id}" の列 ${group.fromCol}..${group.toCol} は無効です。0..${layout.colXs.length - 1} の範囲内で昇順に指定してください。`);
    }
    const contained = [...nodes.values()].some((node) => node.lane === group.lane && node.col >= group.fromCol && node.col <= group.toCol);
    if (!contained) {
      problems.push(`グループ "${group.id}" にノードがありません。囲む並列処理または分岐処理と lane/columns を揃えてください。`);
    }
  }

  const byLane = new Map();
  for (const node of nodes.values()) {
    byLane.set(node.lane, [...(byLane.get(node.lane) || []), node]);
  }
  for (const [lane, laneNodes] of byLane) {
    for (let i = 0; i < laneNodes.length; i += 1) {
      for (let j = i + 1; j < laneNodes.length; j += 1) {
        if (rectsOverlap(laneNodes[i], laneNodes[j], 8)) {
          problems.push(`レーン "${lane}" のノード "${laneNodes[i].id}" と "${laneNodes[j].id}" の間隔が 8px 未満です。一方を別の col へ移動するか、yOffset を調整するか、width/height を減らしてください。`);
        }
      }
    }
  }

  for (const edge of workflow.edges) {
    if (!nodes.has(edge.from)) problems.push(`エッジ "${edge.label || edge.from}" が不明な接続元 "${edge.from}" を参照しています。`);
    if (!nodes.has(edge.to)) problems.push(`エッジ "${edge.label || edge.to}" が不明な接続先 "${edge.to}" を参照しています。`);
    if (nodes.has(edge.from) && nodes.has(edge.to)) {
      const routed = pathFor(edge);
      if (routed.points.length === 2) {
        const [start, end] = routed.points;
        const segmentLength = Math.hypot(end[0] - start[0], end[1] - start[1]);
        if (segmentLength < 28) {
          problems.push(`エッジ "${edge.from}" -> "${edge.to}" が短すぎます（${Math.round(segmentLength)}px、最小 28px）。ノード同士をさらに離すか、読み取れる間隔を持つ検証済みの直交経路を使用してください。`);
        }
      }
    }
  }

  problems.push(...cleanEndpointSideProblems({
    relations: workflow.edges,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    fromSideFor: (edge) => edgeSides(edge).fromSide,
    toSideFor: (edge) => edgeSides(edge).toSide,
    routeHint: '自動ルーティングを維持するか、最初と最後のセグメントがノード境界を垂直に横切る fromSide/toSide と via 点を選ぶ',
  }));
  problems.push(...cleanFlowProblems({
    relations: workflow.edges,
    obstacles: nodes.values(),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    obstacleKind: 'node',
    routeHint: 'fromSide/toSide を調整するか、route/via またはチャネル座標を設定するか、ノードをより空いている lane/column へ移動する'
  }));
  problems.push(...cleanCrossingProblems({
    relations: workflow.edges,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    profile: workflow.meta?.quality_profile,
    profileIsAuthoritative: true,
    mergeForwardCollinearWaypoints: workflow.schema_version === 2,
    routeHint: 'エッジが別々のレーン経路帯を使用するよう route/via、bias、またはチャネル座標を調整する'
  }));
  problems.push(...cleanAmbiguousCorridorProblems({
    relations: workflow.edges,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    profile: workflow.meta?.quality_profile,
    profileIsAuthoritative: true,
    routeHint: '無関係なエッジが視覚的に合流しないよう route/via、bias、またはチャネル座標を調整する'
  }));
  problems.push(...cleanBorderRunProblems({
    relations: workflow.edges,
    endpointIds: new Set(nodes.keys()),
    frames: workflowCompositionFrames(),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    profile: workflow.meta?.quality_profile,
    profileIsAuthoritative: true,
    routeHint: 'エッジがレーンやグループの境界線に沿わず垂直に横切るよう route/via、bias、またはチャネル座標を調整する'
  }));
  problems.push(...cleanRouteRhythmProblems({
    relations: workflow.edges,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    profile: workflow.meta?.quality_profile,
    profileIsAuthoritative: true,
    routeHint: '各曲がり角に読み取れる助走区間ができるよう route/via、bias、またはチャネル座標を調整する'
  }));

  if (Array.isArray(workflow.mainPath)) {
    for (const id of workflow.mainPath) {
      if (!nodes.has(id)) {
        problems.push(`mainPath が不明なノード "${id}" を参照しています。`);
      }
    }
    for (let i = 0; i < workflow.mainPath.length - 1; i += 1) {
      const fromId = workflow.mainPath[i];
      const toId = workflow.mainPath[i + 1];
      const from = nodes.get(fromId);
      const to = nodes.get(toId);
      if (!from || !to) continue;
      const linked = workflow.edges.some((edge) => edge.from === fromId && edge.to === toId);
      if (!linked) {
        problems.push(`mainPath のステップ "${fromId}" -> "${toId}" に一致するエッジがありません。エッジを追加するか、この組を mainPath から削除してください。`);
      }
      if (to.col < from.col) {
        problems.push(`mainPath のステップ "${fromId}" -> "${toId}" が col ${from.col} から ${to.col} へ逆行しています。ループには mainPath 外の return エッジを使用してください。`);
      }
    }
  }

  const labelRects = [];
  for (const [edgeIndex, edge] of workflow.edges.entries()) {
    const labelRect = labelRectFor(edge, edgeIndex);
    if (labelRect) labelRects.push(labelRect);
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
        problems.push(`ラベル "${labelRects[i].label}" と "${labelRects[j].label}" が重なっています。labelDx/labelDy/labelSegment を調整するか、一方の関係を別の経路帯へ通してください。\n${suggestLabelPairFix(labelRects[i], labelRects[j])}`);
      }
    }
  }
  problems.push(...cleanLabelRouteClearanceProblems({
    relations: workflow.edges,
    labels: labelRects,
    endpointIds: new Set(nodes.keys()),
    pathFor,
    diagramType: 'workflow',
    relationCollection: 'edges',
    profile: workflow.meta?.quality_profile,
    profileIsAuthoritative: true,
  }));

  if (workflow.schema_version === 1) {
    if (viewBox[0] < layout.laneX + layout.laneW + 16) {
      problems.push(`viewBox の幅 ${viewBox[0]} では幅 ${layout.laneW}px のレーンが切れます。meta.viewBox[0] を ${layout.laneX + layout.laneW + 16} 以上に設定してください。`);
    }
    if (legendY() + 18 > viewBox[1]) {
      problems.push(`凡例が viewBox の高さ ${viewBox[1]} を超えています。meta.viewBox[1] を ${legendY() + 18} 以上に設定してください。`);
    }
  }

  if (problems.length) {
    throwDiagnosticProblems('ワークフローのレイアウト検証に失敗しました', problems, {
      subject: { diagramType: 'workflow' },
    });
  }
}

function validateReadableInputsBeforeRouting() {
  if (workflow.schema_version !== 2) return;
  const fail = (diagnostic) => throwDiagnosticError(diagnostic.message, [diagnostic]);
  const unusedId = (base, used) => {
    for (let suffix = 2; ; suffix += 1) {
      const candidate = `${base}-${suffix}`;
      if (!used.has(candidate)) return candidate;
    }
  };
  const authoredLanes = [...workflow.lanes].sort((left, right) => (
    sourceIndexes.lanes.get(left) - sourceIndexes.lanes.get(right)
  ));
  const authoredNodes = [...workflow.nodes].sort((left, right) => (
    sourceIndexes.nodes.get(left) - sourceIndexes.nodes.get(right)
  ));
  const authoredEdges = [...workflow.edges].sort((left, right) => (
    sourceIndexes.edges.get(left) - sourceIndexes.edges.get(right)
  ));

  const firstLaneIndex = new Map();
  for (const lane of authoredLanes) {
    const laneIndex = sourceIndexes.lanes.get(lane);
    if (firstLaneIndex.has(lane.id)) {
      const message = `ワークフローのレーン id "${lane.id}" が重複しています。`;
      const replacement = unusedId(lane.id, new Set(workflow.lanes.map(({ id }) => id)));
      const canonicalLaneIndex = workflow.lanes.indexOf(lane);
      const supportedFixes = acceptsFix((document) => {
        document.lanes[canonicalLaneIndex].id = replacement;
      }) ? [`/lanes/${laneIndex}/id を検証済みの一意な id "${replacement}" に変更する`] : [];
      fail({
        code: 'workflow/duplicate-lane-id',
        severity: 'error',
        message,
        subject: { diagramType: 'workflow', lane: lane.id, path: `/lanes/${laneIndex}/id` },
        evidence: {
          duplicateLaneId: lane.id,
          firstPath: `/lanes/${firstLaneIndex.get(lane.id)}/id`,
          duplicatePath: `/lanes/${laneIndex}/id`,
        },
        supportedFixes,
      });
    }
    firstLaneIndex.set(lane.id, laneIndex);
  }

  const firstNodeIndex = new Map();
  for (const node of authoredNodes) {
    const nodeIndex = sourceIndexes.nodes.get(node);
    if (firstNodeIndex.has(node.id)) {
      const message = `ワークフローのノード id "${node.id}" が重複しています。`;
      const replacement = unusedId(node.id, new Set(workflow.nodes.map(({ id }) => id)));
      const canonicalNodeIndex = workflow.nodes.indexOf(node);
      const supportedFixes = acceptsFix((document) => {
        document.nodes[canonicalNodeIndex].id = replacement;
      }) ? [`/nodes/${nodeIndex}/id を検証済みの一意な id "${replacement}" に変更する`] : [];
      fail({
        code: 'workflow/duplicate-node-id',
        severity: 'error',
        message,
        subject: { diagramType: 'workflow', node: node.id, path: `/nodes/${nodeIndex}/id` },
        evidence: {
          duplicateNodeId: node.id,
          firstPath: `/nodes/${firstNodeIndex.get(node.id)}/id`,
          duplicatePath: `/nodes/${nodeIndex}/id`,
        },
        supportedFixes,
      });
    }
    firstNodeIndex.set(node.id, nodeIndex);
  }

  const availableNodeIds = [...nodes.keys()].sort(stableCompare);
  for (const edge of authoredEdges) {
    const edgeIndex = sourceIndexes.edges.get(edge);
    for (const [field, endpoint] of [['from', 'source'], ['to', 'target']]) {
      if (nodes.has(edge[field])) continue;
      const message = `ワークフローエッジ "${workflowEdgeName(edge)}" が不明な${endpoint === 'source' ? '接続元' : '接続先'} "${edge[field]}" を参照しています。`;
      const canonicalEdgeIndex = workflow.edges.indexOf(edge);
      const supportedFixes = availableNodeIds.flatMap((nodeId) => (
        acceptsFix((document) => {
          document.edges[canonicalEdgeIndex][field] = nodeId;
        })
          ? [`/edges/${edgeIndex}/${field} を検証済みのノード id "${nodeId}" に設定する`]
          : []
      ));
      fail({
        code: 'workflow/unknown-edge-endpoint',
        severity: 'error',
        message,
        subject: {
          diagramType: 'workflow',
          edge: edge.id ?? null,
          path: `/edges/${edgeIndex}/${field}`,
          from: edge.from,
          to: edge.to,
        },
        evidence: {
          endpoint,
          unknownNodeId: edge[field],
          availableNodeIds,
        },
        supportedFixes,
      });
    }
  }
  const laneIds = new Set(workflow.lanes.map((lane) => lane.id));
  const availableLaneIds = [...laneIds].sort(stableCompare);
  const nodeSourceIndexes = new Map(authoredNodes.map((node) => [
    node.id,
    sourceIndexes.nodes.get(node),
  ]));

  const byLane = new Map();
  for (const authoredNode of authoredNodes) {
    const nodeIndex = sourceIndexes.nodes.get(authoredNode);
    const node = nodes.get(authoredNode.id);
    if (!laneIds.has(node.lane)) {
      const message = `ワークフローノード "${node.id}" が不明なレーン "${node.lane}" を使用しています。`;
      const canonicalNodeIndex = workflow.nodes.findIndex((candidate) => candidate.id === node.id);
      const supportedFixes = availableLaneIds.flatMap((laneId) => (
        acceptsFix((document) => {
          document.nodes[canonicalNodeIndex].lane = laneId;
        })
          ? [`/nodes/${nodeIndex}/lane を検証済みのレーン id "${laneId}" に設定する`]
          : []
      ));
      fail({
        code: 'workflow/unknown-node-lane',
        severity: 'error',
        message,
        subject: { diagramType: 'workflow', node: node.id, path: `/nodes/${nodeIndex}/lane` },
        evidence: { unknownLaneId: node.lane, availableLaneIds },
        supportedFixes,
      });
    }
    if (!Number.isInteger(node.col) || node.col < 0 || node.col >= layout.colXs.length) {
      const message = `ワークフローノード "${node.id}" の列 ${node.col} は無効です。有効な整数列は 0..${layout.colXs.length - 1} です。`;
      const canonicalNodeIndex = workflow.nodes.findIndex((candidate) => candidate.id === node.id);
      const supportedFixes = layout.colXs.flatMap((_x, col) => (
        acceptsFix((document) => {
          document.nodes[canonicalNodeIndex].col = col;
        })
          ? [`/nodes/${nodeIndex}/col を検証済みの列 ${col} に設定する`]
          : []
      ));
      fail({
        code: 'workflow/invalid-node-column',
        severity: 'error',
        message,
        subject: { diagramType: 'workflow', node: node.id, path: `/nodes/${nodeIndex}/col` },
        evidence: { actualColumn: node.col, minimumColumn: 0, maximumColumn: layout.colXs.length - 1 },
        supportedFixes,
      });
    }
    if (!isFinitePoint(node.x, node.y, node.cx, node.cy)) {
      const message = `ワークフローノード "${node.id}" の座標が有限値ではありません。`;
      fail({
        code: 'workflow/non-finite-node-geometry',
        severity: 'error',
        message,
        subject: { diagramType: 'workflow', node: node.id, path: `/nodes/${nodeIndex}` },
        evidence: {
          measuredRect: { x: node.x, y: node.y, width: node.width, height: node.height },
          authored: {
            col: authoredNode.col,
            width: authoredNode.width ?? null,
            height: authoredNode.height ?? null,
            yOffset: authoredNode.yOffset ?? null,
          },
        },
        supportedFixes: [],
      });
    }
    byLane.set(node.lane, [...(byLane.get(node.lane) || []), node]);
  }
  for (const [lane, laneNodes] of byLane) {
    for (let left = 0; left < laneNodes.length; left += 1) {
      for (let right = left + 1; right < laneNodes.length; right += 1) {
        if (rectsOverlap(laneNodes[left], laneNodes[right], 8)) {
          const leftNode = laneNodes[left];
          const rightNode = laneNodes[right];
          const rightIndex = nodeSourceIndexes.get(rightNode.id);
          const canonicalNodeIndex = workflow.nodes.findIndex((candidate) => (
            candidate.id === rightNode.id
          ));
          const supportedFixes = layout.colXs.flatMap((_x, col) => {
            if (col === rightNode.col) return [];
            return acceptsFix((document) => {
              document.nodes[canonicalNodeIndex].col = col;
            })
              ? [`/nodes/${rightIndex}/col を検証済みの空き列 ${col} に設定する`]
              : [];
          });
          const message = `レーン "${lane}" のワークフローノード "${leftNode.id}" と "${rightNode.id}" の間隔が 8px 未満です。`;
          fail({
            code: 'workflow/node-overlap',
            severity: 'error',
            message,
            subject: { diagramType: 'workflow', node: rightNode.id, path: `/nodes/${rightIndex}` },
            evidence: {
              lane,
              minimumClearancePx: 8,
              nodes: [
                { id: leftNode.id, rect: { x: leftNode.x, y: leftNode.y, width: leftNode.width, height: leftNode.height } },
                { id: rightNode.id, rect: { x: rightNode.x, y: rightNode.y, width: rightNode.width, height: rightNode.height } },
              ],
            },
            supportedFixes,
          });
        }
      }
    }
  }
}

function gapYBetween(fromLane, toLane, bias = 0.5) {
  const a = laneTop(fromLane) + laneHeight(fromLane);
  const b = laneTop(toLane);
  return a + (b - a) * bias;
}

function spanForCols(fromCol, toCol, pad = 46, minimumWidth = 0) {
  const start = layout.colXs[fromCol] - pad;
  const end = layout.colXs[toCol] + pad;
  const width = Math.max(end - start, minimumWidth);
  if (fromCol === toCol && width > end - start) {
    return { x: start, width, cx: start + width / 2 };
  }
  const cx = (start + end) / 2;
  return { x: cx - width / 2, width, cx };
}

function phaseSpan(phase) {
  return spanForCols(
    phase.fromCol,
    phase.toCol,
    46,
    workflow.schema_version === 2 ? textUnits(phase.label) * 5.6 + 8 : 0,
  );
}

function groupSpan(group) {
  if (workflow.schema_version === 2) {
    return readableGroupBounds(workflow, group, layout.colXs);
  }
  return spanForCols(
    group.fromCol,
    group.toCol,
    50,
    0,
  );
}

function sameLaneAutoVia(start, end) {
  if (start[0] === end[0] || start[1] === end[1]) return [];
  const midX = (start[0] + end[0]) / 2;
  return [[midX, start[1]], [midX, end[1]]];
}

function routeClearsUnrelatedNodes(edge, points, clearance = 2) {
  const endpointIds = new Set([edge.from, edge.to]);
  for (const node of nodes.values()) {
    if (endpointIds.has(node.id)) continue;
    for (let index = 0; index < points.length - 1; index += 1) {
      if (segmentIntersectsRect({ start: points[index], end: points[index + 1] }, node, clearance)) {
        return false;
      }
    }
  }
  return true;
}

function firstRouteNodeCollision(edge, points) {
  const lastSegment = points.length - 2;
  for (const node of nodes.values()) {
    const endpointRole = node.id === edge.from
      ? 'source-endpoint'
      : node.id === edge.to ? 'target-endpoint' : 'unrelated';
    for (let segmentIndex = 0; segmentIndex <= lastSegment; segmentIndex += 1) {
      if (endpointRole === 'source-endpoint' && segmentIndex === 0) continue;
      if (endpointRole === 'target-endpoint' && segmentIndex === lastSegment) continue;
      const clearancePx = endpointRole === 'unrelated' ? 2 : 0;
      const from = points[segmentIndex];
      const to = points[segmentIndex + 1];
      if (segmentIntersectsRect({ start: from, end: to }, node, clearancePx)) {
        return {
          obstacleNode: node.id,
          obstacleRole: endpointRole,
          segmentIndex,
          from: [...from],
          to: [...to],
          clearancePx,
        };
      }
    }
  }
  return null;
}

function oneBendCrossLaneVia(edge, start, end, fromSide, toSide) {
  const fromVertical = fromSide === 'top' || fromSide === 'bottom';
  const toVertical = toSide === 'top' || toSide === 'bottom';
  if (fromVertical === toVertical) return null;

  const corner = fromVertical ? [start[0], end[1]] : [end[0], start[1]];
  const points = normalizeRoutePoints([start, corner, end]);
  if (points.length !== 3 || !routeHonorsEndpointSides(points, fromSide, toSide)) return null;

  const segmentsAreReadable = points.slice(0, -1).every((point, index) => (
    Math.hypot(
      points[index + 1][0] - point[0],
      points[index + 1][1] - point[1],
    ) >= 8
  ));
  if (!segmentsAreReadable || !routeClearsUnrelatedNodes(edge, points)) return null;
  return points.slice(1, -1);
}

const pathCache = new Map();
const readableSideCache = new Map();

function legacyAutomaticOneBendSides(edge, from, to) {
  const automaticRoute = !edge.via && (!edge.route || edge.route === 'auto');
  const automaticFrom = !edge.fromSide || edge.fromSide === 'auto';
  const automaticTo = !edge.toSide || edge.toSide === 'auto';
  if (!automaticRoute || !automaticFrom || !automaticTo || from.lane === to.lane) return null;
  if (from.cx === to.cx || from.cy === to.cy) return null;
  const verticalFrom = to.cy < from.cy ? 'top' : 'bottom';
  const horizontalTo = to.cx < from.cx ? 'right' : 'left';
  const horizontalFrom = to.cx < from.cx ? 'left' : 'right';
  const verticalTo = to.cy < from.cy ? 'bottom' : 'top';
  const candidates = [
    { fromSide: verticalFrom, toSide: horizontalTo },
    { fromSide: horizontalFrom, toSide: verticalTo },
  ];

  return candidates.find(({ fromSide, toSide }) => {
    const start = anchor(from, fromSide);
    const end = anchor(to, toSide);
    return oneBendCrossLaneVia(edge, start, end, fromSide, toSide);
  }) || null;
}

function readableAutomaticSides(edge, from, to) {
  const automaticRoute = !edge.via
    && edge.channelX === undefined
    && edge.channelY === undefined
    && (!edge.route || edge.route === 'auto');
  const authoredFrom = edge.fromSide && edge.fromSide !== 'auto' ? edge.fromSide : null;
  const authoredTo = edge.toSide && edge.toSide !== 'auto' ? edge.toSide : null;
  if (!automaticRoute || (authoredFrom && authoredTo)) return null;
  if (readableSideCache.has(edge)) return readableSideCache.get(edge);

  const preferred = [];
  const legacyPreferred = legacyAutomaticOneBendSides(edge, from, to);
  if (legacyPreferred) preferred.push(legacyPreferred);
  preferred.push({
    fromSide: authoredFrom || defaultFromSide(from, to),
    toSide: authoredTo || defaultToSide(from, to),
  });
  const sideOrder = ['right', 'bottom', 'left', 'top'];
  for (const fromSide of authoredFrom ? [authoredFrom] : sideOrder) {
    for (const toSide of authoredTo ? [authoredTo] : sideOrder) {
      preferred.push({ fromSide, toSide });
    }
  }

  const seen = new Set();
  const sidePairs = [];
  for (const candidate of preferred) {
    if (authoredFrom && candidate.fromSide !== authoredFrom) continue;
    if (authoredTo && candidate.toSide !== authoredTo) continue;
    const key = `${candidate.fromSide}:${candidate.toSide}`;
    if (seen.has(key)) continue;
    seen.add(key);
    sidePairs.push(candidate);
  }

  const naturalFromSide = authoredFrom || defaultFromSide(from, to);
  const naturalToSide = authoredTo || defaultToSide(from, to);
  const planFor = (candidate, pairOrdinal) => {
    const start = anchor(from, candidate.fromSide);
    const end = anchor(to, candidate.toSide);
    return {
      start,
      end,
      planned: readableAutomaticCandidateSet(
        edge,
        from,
        to,
        start,
        end,
        candidate.fromSide,
        candidate.toSide,
        {
          ordinalOffset: pairOrdinal * 9,
          naturalFromSide,
          naturalToSide,
        },
      ),
    };
  };

  const primary = sidePairs[0];
  if (primary) {
    const { planned } = planFor(primary, 0);
    if (planned.candidates.length) {
      readableSideCache.set(edge, primary);
      return primary;
    }
  }

  const candidates = [];
  for (const [pairOrdinal, candidate] of sidePairs.entries()) {
    const { planned } = planFor(candidate, pairOrdinal);
    candidates.push(...planned.candidates.map((route) => ({ ...route, ...candidate })));
  }
  candidates.sort((left, right) => compareCost(left.cost, right.cost));
  if (candidates.length) {
    const selected = {
      fromSide: candidates[0].fromSide,
      toSide: candidates[0].toSide,
    };
    readableSideCache.set(edge, selected);
    return selected;
  }
  readableSideCache.set(edge, null);
  return null;
}

function automaticOneBendSides(edge, from, to) {
  return workflow.schema_version === 2
    ? readableAutomaticSides(edge, from, to)
    : legacyAutomaticOneBendSides(edge, from, to);
}

const OUTWARD_SIDE_VECTOR = Object.freeze({
  left: [-1, 0],
  right: [1, 0],
  top: [0, -1],
  bottom: [0, 1],
});

function outwardStub(point, side, distance = 16) {
  const [dx, dy] = OUTWARD_SIDE_VECTOR[side] || [0, 0];
  return [point[0] + dx * distance, point[1] + dy * distance];
}

function orthogonalRoute(points) {
  return points.every((point, index) => {
    if (!Array.isArray(point) || point.length !== 2 || !isFinitePoint(...point)) return false;
    if (index === 0) return true;
    const previous = points[index - 1];
    const dx = Math.abs(point[0] - previous[0]);
    const dy = Math.abs(point[1] - previous[1]);
    return (dx <= 0.0001) !== (dy <= 0.0001);
  });
}

function routeClearsEndpointNodes(points, from, to) {
  const lastSegment = points.length - 2;
  for (let index = 0; index <= lastSegment; index += 1) {
    const segment = { start: points[index], end: points[index + 1] };
    if (index > 0 && segmentIntersectsRect(segment, from)) return false;
    if (index < lastSegment && segmentIntersectsRect(segment, to)) return false;
  }
  return true;
}

function routeMeetsHardRhythm(points) {
  if (points.length === 2) {
    return Math.hypot(points[1][0] - points[0][0], points[1][1] - points[0][1]) + 0.0001 >= 28;
  }
  return points.slice(0, -1).every((point, index) => {
    const length = Math.abs(points[index + 1][0] - point[0]) + Math.abs(points[index + 1][1] - point[1]);
    const endpoint = index === 0 || index === points.length - 2;
    return length + 0.0001 >= (endpoint ? 8 : 16);
  });
}

function routeLabelClearsNodes(edge, points) {
  if (!edge.label || edge.labelAt) return true;
  const [lx, ly] = workflowEdgeLabelPoint(edge, points);
  const rect = {
    x: lx - workflowLabelWidth(edge.label) / 2,
    y: ly - 10,
    width: workflowLabelWidth(edge.label),
    height: 14,
  };
  return [...nodes.values()].every((node) => !rectsOverlap(rect, node, -2));
}

function candidateLabelRect(edge, points) {
  if (!edge.label) return null;
  const [lx, ly] = workflowEdgeLabelPoint(edge, points);
  const width = workflowLabelWidth(edge.label);
  return { x: lx - width / 2, y: ly - 10, width, height: 14 };
}

function labelRouteClearanceDeficit(edge, points, threshold = 8) {
  const candidateLabel = candidateLabelRect(edge, points);
  let deficit = 0;
  for (const [otherEdge, routed] of pathCache) {
    const otherIndex = workflow.edges.indexOf(otherEdge);
    const otherLabel = labelRectFor(otherEdge, otherIndex);
    if (candidateLabel) {
      for (let index = 0; index < routed.points.length - 1; index += 1) {
        const clearance = segmentRectClearance({
          start: routed.points[index],
          end: routed.points[index + 1],
        }, candidateLabel);
        if (clearance != null) deficit += Math.max(0, threshold - clearance);
      }
    }
    if (otherLabel) {
      for (let index = 0; index < points.length - 1; index += 1) {
        const clearance = segmentRectClearance({
          start: points[index],
          end: points[index + 1],
        }, otherLabel);
        if (clearance != null) deficit += Math.max(0, threshold - clearance);
      }
    }
  }
  return deficit;
}

function routeClearsPlacedLabels(edge, points) {
  const candidateLabel = candidateLabelRect(edge, points);
  for (const [otherEdge, routed] of pathCache) {
    const otherIndex = workflow.edges.indexOf(otherEdge);
    const otherLabel = labelRectFor(otherEdge, otherIndex);
    if (candidateLabel && otherLabel && rectsOverlap(candidateLabel, otherLabel, -2)) return false;
    if (candidateLabel) {
      for (let index = 0; index < routed.points.length - 1; index += 1) {
        const clearance = segmentRectClearance({
          start: routed.points[index],
          end: routed.points[index + 1],
        }, candidateLabel);
        if (clearance != null && clearance + 0.0001 < 4) return false;
      }
    }
    if (otherLabel) {
      for (let index = 0; index < points.length - 1; index += 1) {
        const clearance = segmentRectClearance({
          start: points[index],
          end: points[index + 1],
        }, otherLabel);
        if (clearance != null && clearance + 0.0001 < 4) return false;
      }
    }
  }
  return true;
}

function routeClearsLegend(edge, points) {
  if (!workflowLegendEntries.length) return true;
  const legendRects = workflowLegendRects();
  for (const rect of legendRects) {
    for (let index = 0; index < points.length - 1; index += 1) {
      if (segmentIntersectsRect({ start: points[index], end: points[index + 1] }, rect)) return false;
    }
    const label = candidateLabelRect(edge, points);
    if (label && rectsOverlap(label, rect)) return false;
  }
  return true;
}

function routeClearsSceneLabelObstacles(edge, points) {
  const label = candidateLabelRect(edge, points);
  for (const obstacle of workflowSceneLabelObstacles()) {
    for (let index = 0; index < points.length - 1; index += 1) {
      if (segmentIntersectsRect({ start: points[index], end: points[index + 1] }, obstacle)) {
        return false;
      }
    }
    if (label && rectsOverlap(label, obstacle)) return false;
  }
  return true;
}

function routeClearsFrameBorders(points) {
  return collectBorderRuns({
    routedRelations: [{ points }],
    frames: workflowCompositionFrames(),
  }).length === 0;
}

function routeExtentCoordinates(edge, points) {
  const coordinates = [...points];
  if (!edge.labelAt) {
    const label = candidateLabelRect(edge, points);
    if (label) {
      coordinates.push([label.x, label.y], [label.x + label.width, label.y + label.height]);
    }
  }
  return coordinates;
}

function routeFitsCanvasOrigin(edge, points) {
  return routeExtentCoordinates(edge, points).every(([x, y]) => x >= 0 && y >= 0);
}

function readableCandidateIsFeasible(edge, points, from, to, fromSide, toSide) {
  return points.length >= 2
    && orthogonalRoute(points)
    && routeHonorsEndpointSides(points, fromSide, toSide)
    && routeMeetsHardRhythm(points)
    && routeClearsEndpointNodes(points, from, to)
    && routeClearsUnrelatedNodes(edge, points)
    && routeLabelClearsNodes(edge, points)
    && routeClearsPlacedLabels(edge, points)
    && routeClearsLegend(edge, points)
    && routeClearsSceneLabelObstacles(edge, points)
    && routeClearsFrameBorders(points)
    && routeFitsCanvasOrigin(edge, points);
}

function corridorViaY(start, end, fromSide, toSide, y) {
  const startStub = outwardStub(start, fromSide);
  const endStub = outwardStub(end, toSide);
  return [startStub, [startStub[0], y], [endStub[0], y], endStub];
}

function corridorViaX(start, end, fromSide, toSide, x) {
  const startStub = outwardStub(start, fromSide);
  const endStub = outwardStub(end, toSide);
  return [startStub, [x, startStub[1]], [x, endStub[1]], endStub];
}

function axisOverlapLength(a, b, c, d) {
  const horizontal = Math.abs(a[1] - b[1]) <= 0.0001
    && Math.abs(c[1] - d[1]) <= 0.0001
    && Math.abs(a[1] - c[1]) <= 0.0001;
  const vertical = Math.abs(a[0] - b[0]) <= 0.0001
    && Math.abs(c[0] - d[0]) <= 0.0001
    && Math.abs(a[0] - c[0]) <= 0.0001;
  if (!horizontal && !vertical) return 0;
  const axis = horizontal ? 0 : 1;
  return Math.max(0, Math.min(Math.max(a[axis], b[axis]), Math.max(c[axis], d[axis]))
    - Math.max(Math.min(a[axis], b[axis]), Math.min(c[axis], d[axis])));
}

function properAxisCrossing(a, b, c, d) {
  const firstHorizontal = Math.abs(a[1] - b[1]) <= 0.0001;
  const secondHorizontal = Math.abs(c[1] - d[1]) <= 0.0001;
  if (firstHorizontal === secondHorizontal) return false;
  const horizontal = firstHorizontal ? [a, b] : [c, d];
  const vertical = firstHorizontal ? [c, d] : [a, b];
  const x = vertical[0][0];
  const y = horizontal[0][1];
  return x > Math.min(horizontal[0][0], horizontal[1][0]) + 0.0001
    && x < Math.max(horizontal[0][0], horizontal[1][0]) - 0.0001
    && y > Math.min(vertical[0][1], vertical[1][1]) + 0.0001
    && y < Math.max(vertical[0][1], vertical[1][1]) - 0.0001;
}

function routeInteractionMetrics(edge, points) {
  let properCrossingCount = 0;
  let sharedCorridorPx = 0;
  for (const [otherEdge, routed] of pathCache) {
    if ([edge.from, edge.to].some((id) => id === otherEdge.from || id === otherEdge.to)) continue;
    for (let left = 0; left < points.length - 1; left += 1) {
      for (let right = 0; right < routed.points.length - 1; right += 1) {
        if (properAxisCrossing(points[left], points[left + 1], routed.points[right], routed.points[right + 1])) {
          properCrossingCount += 1;
        }
        sharedCorridorPx += axisOverlapLength(
          points[left], points[left + 1], routed.points[right], routed.points[right + 1],
        );
      }
    }
  }
  return { properCrossingCount, sharedCorridorPx };
}

function automaticForwardReversePx(edge, points) {
  const from = nodes.get(edge.from);
  const to = nodes.get(edge.to);
  if (!from || !to || ['return', 'error'].includes(edge.role) || to.col <= from.col) return 0;
  return points.slice(0, -1).reduce((total, point, index) => (
    total + Math.max(0, point[0] - points[index + 1][0])
  ), 0);
}

function readableCandidateCost(
  edge,
  points,
  ordinal,
  naturalFromSide,
  naturalToSide,
) {
  const interaction = routeInteractionMetrics(edge, points);
  const segmentLengths = points.slice(0, -1).map((point, index) => (
    Math.abs(points[index + 1][0] - point[0]) + Math.abs(points[index + 1][1] - point[1])
  ));
  const routeLength = segmentLengths.reduce((total, length) => total + length, 0);
  const directLength = Math.abs(points.at(-1)[0] - points[0][0]) + Math.abs(points.at(-1)[1] - points[0][1]);
  const interiorPreferred28Deficit = segmentLengths.slice(1, -1)
    .reduce((total, length) => total + Math.max(0, 28 - length), 0);
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const canvasGrowthPx = Math.max(0, -Math.min(...xs))
    + Math.max(0, Math.max(...xs) - minimumCanvasWidth)
    + Math.max(0, -Math.min(...ys))
    + Math.max(0, Math.max(...ys) - autoHeight);
  const from = nodes.get(edge.from);
  const to = nodes.get(edge.to);
  const naturalStart = anchor(from, naturalFromSide);
  const naturalEnd = anchor(to, naturalToSide);
  const portDisplacementPx = Math.abs(points[0][0] - naturalStart[0])
    + Math.abs(points[0][1] - naturalStart[1])
    + Math.abs(points.at(-1)[0] - naturalEnd[0])
    + Math.abs(points.at(-1)[1] - naturalEnd[1]);
  const legacyCoordinateDisplacement = Math.abs(from.cx - LEGACY_COLUMN_CENTERS[from.col])
    + Math.abs(to.cx - LEGACY_COLUMN_CENTERS[to.col]);
  return {
    automaticForwardReversePx: automaticForwardReversePx(edge, points),
    properCrossingCount: interaction.properCrossingCount,
    sharedCorridorPx: interaction.sharedCorridorPx,
    labelRouteClearanceDeficit: labelRouteClearanceDeficit(edge, points),
    interiorPreferred28Deficit,
    bendCount: Math.max(0, points.length - 2),
    stretchMilli: Math.round((directLength > 0 ? routeLength / directLength : 1) * 1000),
    canvasGrowthPx,
    portDisplacementMilli: Math.round(portDisplacementPx * 1000),
    legacyCoordinateDisplacement,
    stableCandidateOrdinal: ordinal,
  };
}

function compareCost(left, right) {
  for (const dimension of READABLE_CANDIDATE_COST_PRIORITY) {
    if ((left[dimension] || 0) !== (right[dimension] || 0)) {
      return (left[dimension] || 0) - (right[dimension] || 0);
    }
  }
  return 0;
}

function readableAutomaticCandidateSet(
  edge,
  from,
  to,
  start,
  end,
  fromSide,
  toSide,
  {
    ordinalOffset = 0,
    naturalFromSide = fromSide,
    naturalToSide = toSide,
  } = {},
) {
  const midX = (start[0] + end[0]) / 2;
  const laneGapY = from.lane === to.lane
    ? laneTop(from.lane) - 16
    : gapYBetween(from.lane, to.lane, edge.bias ?? 0.5);
  const topY = Math.max(8, Math.min(laneTop(from.lane), laneTop(to.lane)) - 16);
  const bottomY = Math.max(
    laneTop(from.lane) + laneHeight(from.lane),
    laneTop(to.lane) + laneHeight(to.lane),
  ) + 16;
  const outsideLeft = layout.laneX - 20;
  const outsideRight = layout.laneX + layout.laneW + 12;
  const rawCandidates = [
    { family: 'facing-straight', via: [] },
    { family: 'horizontal-then-vertical', via: [[end[0], start[1]]] },
    { family: 'vertical-then-horizontal', via: [[start[0], end[1]]] },
    { family: 'lane-gap-corridor', via: corridorViaY(start, end, fromSide, toSide, laneGapY) },
    { family: 'column-gap-corridor', via: corridorViaX(start, end, fromSide, toSide, midX) },
    { family: 'outside-left', via: corridorViaX(start, end, fromSide, toSide, outsideLeft) },
    { family: 'outside-right', via: corridorViaX(start, end, fromSide, toSide, outsideRight) },
    { family: 'top-corridor', via: corridorViaY(start, end, fromSide, toSide, topY) },
    { family: 'bottom-corridor', via: corridorViaY(start, end, fromSide, toSide, bottomY) },
  ];
  const candidates = rawCandidates.map((candidate, ordinal) => ({
    ...candidate,
    ordinal: ordinalOffset + ordinal,
    points: normalizeRoutePoints([start, ...candidate.via, end]),
  })).filter(({ points }) => (
    readableCandidateIsFeasible(edge, points, from, to, fromSide, toSide)
  )).map((candidate) => ({
    ...candidate,
    cost: readableCandidateCost(
      edge,
      candidate.points,
      candidate.ordinal,
      naturalFromSide,
      naturalToSide,
    ),
  })).sort((left, right) => compareCost(left.cost, right.cost));
  return { rawCandidates, candidates, outsideRight };
}

function readableAutomaticVia(edge, from, to, start, end, fromSide, toSide) {
  const { rawCandidates, candidates, outsideRight } = readableAutomaticCandidateSet(
    edge,
    from,
    to,
    start,
    end,
    fromSide,
    toSide,
  );

  if (candidates.length) return candidates[0].points.slice(1, -1);
  const outsideRightCandidate = rawCandidates.find(({ family }) => family === 'outside-right');
  if (outsideRightCandidate) {
    const currentPoints = normalizeRoutePoints([start, ...outsideRightCandidate.via, end]);
    const labelRect = candidateLabelRect(edge, currentPoints);
    let outsideRightMinX = outsideRight;
    for (const node of nodes.values()) {
      if (!labelRect || !rectsOverlap(labelRect, node, -2)) continue;
      const rightwardLabelDeficit = node.x + node.width - 2 - labelRect.x;
      if (rightwardLabelDeficit > 0) {
        outsideRightMinX = Math.max(
          outsideRightMinX,
          outsideRight + rightwardLabelDeficit * 2,
        );
      }
    }
    for (const [otherEdge, routed] of pathCache) {
      const otherIndex = workflow.edges.indexOf(otherEdge);
      const otherLabel = labelRectFor(otherEdge, otherIndex);
      if (labelRect && otherLabel && rectsOverlap(labelRect, otherLabel, -2)) {
        const rightwardLabelDeficit = otherLabel.x + otherLabel.width - 2 - labelRect.x;
        if (rightwardLabelDeficit > 0) {
          outsideRightMinX = Math.max(
            outsideRightMinX,
            outsideRight + rightwardLabelDeficit * 2,
          );
        }
      }
      if (!labelRect) continue;
      for (let index = 0; index < routed.points.length - 1; index += 1) {
        const segment = {
          start: routed.points[index],
          end: routed.points[index + 1],
        };
        const clearance = segmentRectClearance(segment, labelRect);
        if (clearance == null || clearance + 0.0001 >= 4) continue;
        const rightwardLabelDeficit = Math.max(segment.start[0], segment.end[0])
          + 4 - labelRect.x;
        if (rightwardLabelDeficit > 0) {
          outsideRightMinX = Math.max(
            outsideRightMinX,
            outsideRight + rightwardLabelDeficit * 2,
          );
        }
      }
    }
    outsideRightMinX = Math.ceil(outsideRightMinX * 1000) / 1000;
    let rightmostPlacedX = outsideRight;
    for (const node of nodes.values()) {
      rightmostPlacedX = Math.max(rightmostPlacedX, node.x + node.width);
    }
    for (const [otherEdge, routed] of pathCache) {
      for (const [x] of routed.points) rightmostPlacedX = Math.max(rightmostPlacedX, x);
      const otherLabel = labelRectFor(otherEdge, workflow.edges.indexOf(otherEdge));
      if (otherLabel) {
        rightmostPlacedX = Math.max(rightmostPlacedX, otherLabel.x + otherLabel.width);
      }
    }
    let probeGrowth = Math.max(
      32,
      labelRect?.width ?? 0,
      rightmostPlacedX + 16 - outsideRightMinX,
    );
    let lastInfeasibleX = outsideRight;
    for (let probe = 0; probe < 7; probe += 1) {
      if (outsideRightMinX > outsideRight + 0.0001) {
        const expandedPoints = normalizeRoutePoints([
          start,
          ...corridorViaX(start, end, fromSide, toSide, outsideRightMinX),
          end,
        ]);
        if (readableCandidateIsFeasible(edge, expandedPoints, from, to, fromSide, toSide)) {
          let feasibleX = outsideRightMinX;
          let feasiblePoints = expandedPoints;
          let infeasibleX = lastInfeasibleX;
          for (let refinement = 0;
            refinement < 53 && feasibleX - infeasibleX > 0.001;
            refinement += 1) {
            const midpointX = Math.ceil(((infeasibleX + feasibleX) / 2) * 1000) / 1000;
            if (midpointX >= feasibleX - 0.0001) break;
            const midpointPoints = normalizeRoutePoints([
              start,
              ...corridorViaX(start, end, fromSide, toSide, midpointX),
              end,
            ]);
            if (readableCandidateIsFeasible(
              edge,
              midpointPoints,
              from,
              to,
              fromSide,
              toSide,
            )) {
              feasibleX = midpointX;
              feasiblePoints = midpointPoints;
            } else {
              infeasibleX = midpointX;
            }
          }
          return feasiblePoints.slice(1, -1);
        }
        lastInfeasibleX = outsideRightMinX;
      }
      outsideRightMinX = Math.ceil((outsideRightMinX + probeGrowth) * 1000) / 1000;
      probeGrowth *= 2;
    }
  }
  const hasRelevantAbsolutePin = Array.isArray(edge.labelAt)
    || [...pathCache.keys()].some((otherEdge) => (
      Array.isArray(otherEdge.labelAt) || hasAbsoluteRoutePins(otherEdge)
    ));
  if (hasRelevantAbsolutePin) classifyFailedAutomaticCandidatePins(edge, rawCandidates);
  const horizontallyFacing = (
    fromSide === 'right' && toSide === 'left' && end[0] > start[0]
  ) || (
    fromSide === 'left' && toSide === 'right' && start[0] > end[0]
  );
  if (horizontallyFacing && from.col !== to.col) {
    const fromCol = Math.min(from.col, to.col);
    const toCol = Math.max(from.col, to.col);
    const requiredRankGap = from.width / 2 + 32 + to.width / 2;
    const actualRankGap = layout.colXs[toCol] - layout.colXs[fromCol];
    if (actualRankGap + 0.0001 < requiredRankGap) {
      throw new WorkflowLayoutFeedback({
        kind: 'rank-gap-minimum',
        fromCol,
        toCol,
        minimum: Math.ceil(requiredRankGap * 1000) / 1000,
        edge: edge.id ?? null,
        from: edge.from,
        to: edge.to,
        attemptedCandidateFamilies: rawCandidates.map(({ family }) => family),
        candidateCount: rawCandidates.length,
      });
    }
  }
  if (from.lane !== to.lane && layout.laneGap < 32) {
    throw new WorkflowLayoutFeedback({
      kind: 'lane-gap-minimum',
      minimum: 32,
      edge: edge.id ?? null,
      from: edge.from,
      to: edge.to,
      attemptedCandidateFamilies: rawCandidates.map(({ family }) => family),
      candidateCount: rawCandidates.length,
    });
  }
  const message = `ワークフローエッジ "${workflowEdgeName(edge)}" には実行可能な readable-v2 自動経路がありません。`;
  throwDiagnosticError(message, [{
    code: 'workflow/solver-budget-exhausted',
    severity: 'error',
    message,
    subject: {
      diagramType: 'workflow',
      edge: edge.id ?? null,
      from: edge.from,
      to: edge.to,
    },
    evidence: {
      attemptedCandidateFamilies: rawCandidates.map(({ family }) => family),
      candidateCount: rawCandidates.length,
    },
    supportedFixes: [],
  }]);
}

function readablePresetVia(edge, from, to, start, end, fromSide, toSide) {
  const preset = edge.route;
  let via;
  switch (preset) {
    case 'straight':
      via = [];
      break;
    case 'drop': {
      const y = gapYBetween(from.lane, to.lane, edge.bias ?? 0.5);
      via = [[start[0], y], [end[0], y]];
      break;
    }
    case 'outside-right': {
      const x = layout.laneX + layout.laneW + 12;
      via = [[x, start[1]], [x, end[1]]];
      break;
    }
    case 'return-left': {
      const x = Math.min(from.x, to.x) - 28;
      via = [[x, start[1]], [x, end[1]]];
      break;
    }
    case 'bottom-channel': {
      const y = Math.max(from.y + from.height, to.y + to.height) + 32;
      via = [[start[0], y], [end[0], y]];
      break;
    }
    case 'up-channel': {
      const y = Math.min(from.y, to.y) - 28;
      via = [[start[0], y], [end[0], y]];
      break;
    }
    default:
      return readableAutomaticVia(edge, from, to, start, end, fromSide, toSide);
  }
  const points = normalizeRoutePoints([start, ...via, end]);
  if (readableCandidateIsFeasible(edge, points, from, to, fromSide, toSide)
    && routeMatchesPresetFamily(preset, points, from, to)) {
    return points.slice(1, -1);
  }
  const message = `ワークフローエッジ "${workflowEdgeName(edge)}" は readable-v2 の制約（端点スタブ最小 8px、内部の曲がり最小 16px、直接間隔最小 28px）では経路プリセット "${preset}" を満たせません。`;
  const edgeIndex = workflow.edges.indexOf(edge);
  const edgeName = workflowEdgeName(edge);
  const supportedFixes = [];
  for (const candidatePreset of ['straight', 'drop', 'outside-right', 'return-left', 'bottom-channel', 'up-channel']) {
    if (candidatePreset === preset) continue;
    if (acceptsFix((document) => {
      document.edges[edgeIndex].route = candidatePreset;
    })) {
      supportedFixes.push(`エッジ "${edgeName}" の route を検証済みプリセット "${candidatePreset}" に設定する`);
    }
  }
  if (acceptsFix((document) => {
    delete document.edges[edgeIndex].route;
  })) {
    supportedFixes.push(`readable-v2 が検証済みの自動候補を使用できるよう、エッジ "${edgeName}" から route を削除する`);
  }
  throwDiagnosticError(message, [{
    code: 'workflow/route-preset-conflict',
    severity: 'error',
    message,
    subject: {
      diagramType: 'workflow',
      edge: edge.id ?? null,
      from: edge.from,
      to: edge.to,
      route: preset,
    },
    evidence: {
      attemptedCandidateFamily: preset,
      points,
      fromSide,
      toSide,
      requiredEndpointStubPx: 8,
      requiredInteriorSegmentPx: 16,
      requiredDirectClearancePx: 28,
    },
    supportedFixes,
  }]);
}

function routeVia(
  edge,
  from,
  to,
  start,
  end,
  fromSide,
  toSide,
  { validateReadablePreset = true } = {},
) {
  if (edge.via) return edge.via;
  const hasCoordinatePins = edge.channelX !== undefined || edge.channelY !== undefined;
  if (workflow.schema_version === 2
    && edge.route
    && edge.route !== 'auto'
    && !hasCoordinatePins
    && validateReadablePreset) {
    return readablePresetVia(edge, from, to, start, end, fromSide, toSide);
  }
  switch (edge.route || 'auto') {
    case 'straight':
      return [];
    case 'drop': {
      const y = edge.channelY ?? gapYBetween(from.lane, to.lane, edge.bias ?? 0.5);
      return [[start[0], y], [end[0], y]];
    }
    case 'outside-right': {
      const x = edge.channelX ?? layout.laneX + layout.laneW + 12;
      return [[x, start[1]], [x, end[1]]];
    }
    case 'return-left': {
      const x = edge.channelX ?? Math.min(from.x, to.x) - 28;
      return [[x, start[1]], [x, end[1]]];
    }
    case 'bottom-channel': {
      const y = edge.channelY ?? Math.max(from.y + from.height, to.y + to.height) + 32;
      return [[start[0], y], [end[0], y]];
    }
    case 'up-channel': {
      const y = edge.channelY ?? Math.min(from.y, to.y) - 28;
      return [[start[0], y], [end[0], y]];
    }
    case 'auto':
    default: {
      if (workflow.schema_version === 2) {
        if (edge.channelX !== undefined && edge.channelY !== undefined) {
          return [[edge.channelX, start[1]], [edge.channelX, edge.channelY], [end[0], edge.channelY]];
        }
        if (edge.channelX !== undefined) return [[edge.channelX, start[1]], [edge.channelX, end[1]]];
        if (edge.channelY !== undefined) return [[start[0], edge.channelY], [end[0], edge.channelY]];
        return readableAutomaticVia(edge, from, to, start, end, fromSide, toSide);
      }
      if (from.lane === to.lane) return sameLaneAutoVia(start, end);
      const oneBendVia = oneBendCrossLaneVia(edge, start, end, fromSide, toSide);
      if (oneBendVia) return oneBendVia;
      const y = gapYBetween(from.lane, to.lane, edge.bias ?? 0.5);
      return [[start[0], y], [end[0], y]];
    }
  }
}

function workflowEdgeLabelPoint(edge, points) {
  if (workflow.schema_version === 1) {
    if (edge.labelAt || Number.isInteger(edge.labelSegment) || points.length !== 3) {
      return labelPoint(edge, points);
    }
    const segmentLengths = [0, 1].map((index) => Math.hypot(
      points[index + 1][0] - points[index][0],
      points[index + 1][1] - points[index][1],
    ));
    const labelSegment = segmentLengths[0] >= segmentLengths[1] ? 0 : 1;
    const point = labelPoint({ ...edge, labelSegment }, points);
    if (points[labelSegment][0] === points[labelSegment + 1][0]) point[1] += 10;
    return point;
  }
  if (edge.labelAt || Number.isInteger(edge.labelSegment) || points.length <= 2) {
    return labelPoint(edge, points);
  }
  const segments = points.slice(0, -1).map((point, index) => ({
    index,
    horizontal: Math.abs(points[index + 1][1] - point[1]) <= 0.0001,
    length: Math.hypot(
      points[index + 1][0] - point[0],
      points[index + 1][1] - point[1],
    ),
  })).sort((left, right) => (
    Number(right.horizontal) - Number(left.horizontal)
    || right.length - left.length
    || left.index - right.index
  ));
  const labelSegment = segments[0]?.index ?? 0;
  const point = labelPoint({ ...edge, labelSegment }, points);
  if (points[labelSegment][0] === points[labelSegment + 1][0]) point[1] += 10;
  return point;
}

function edgeSides(edge) {
  const from = nodes.get(edge.from);
  const to = nodes.get(edge.to);
  const resolved = workflow.schema_version === 2 ? readableSideCache.get(edge) : null;
  if (resolved) return resolved;
  const oneBendSides = automaticOneBendSides(edge, from, to);
  if (oneBendSides) return oneBendSides;
  if (workflow.schema_version === 2
    && layout.channelLabelEdgeKeys?.has(stableValueKey(edge))
    && !edge.fromSide
    && !edge.toSide) {
    return { fromSide: 'top', toSide: 'top' };
  }
  return {
    fromSide: chosenSide(edge.fromSide, defaultFromSide(from, to)),
    toSide: chosenSide(edge.toSide, defaultToSide(from, to)),
  };
}

const automaticPorts = automaticPortSpread(workflow.edges, nodes, {
  sideFor: (edge, endpoint) => edgeSides(edge)[endpoint === 'source' ? 'fromSide' : 'toSide'],
});

function readableAutomaticRoute(edge, from, to, primarySides, primaryPorts) {
  const authoredFrom = edge.fromSide && edge.fromSide !== 'auto' ? edge.fromSide : null;
  const authoredTo = edge.toSide && edge.toSide !== 'auto' ? edge.toSide : null;
  const sideOrder = ['right', 'bottom', 'left', 'top'];
  const sidePairs = [primarySides];
  for (const fromSide of authoredFrom ? [authoredFrom] : sideOrder) {
    for (const toSide of authoredTo ? [authoredTo] : sideOrder) {
      sidePairs.push({ fromSide, toSide });
    }
  }

  const naturalFromSide = authoredFrom || defaultFromSide(from, to);
  const naturalToSide = authoredTo || defaultToSide(from, to);
  const seen = new Set();
  const plans = [];
  const feedback = [];
  let firstFailure = null;
  for (const candidateSides of sidePairs) {
    if (authoredFrom && candidateSides.fromSide !== authoredFrom) continue;
    if (authoredTo && candidateSides.toSide !== authoredTo) continue;
    const key = `${candidateSides.fromSide}:${candidateSides.toSide}`;
    if (seen.has(key)) continue;
    const pairOrdinal = seen.size;
    seen.add(key);
    const primary = pairOrdinal === 0;
    const start = primaryPorts?.from && primary
      ? primaryPorts.from
      : anchor(from, candidateSides.fromSide);
    const end = primaryPorts?.to && primary
      ? primaryPorts.to
      : anchor(to, candidateSides.toSide);
    const planned = readableAutomaticCandidateSet(
      edge,
      from,
      to,
      start,
      end,
      candidateSides.fromSide,
      candidateSides.toSide,
      {
        ordinalOffset: pairOrdinal * 9,
        naturalFromSide,
        naturalToSide,
      },
    );
    plans.push(...planned.candidates.map((candidate) => ({
      ...candidate,
      ...candidateSides,
    })));
    if (planned.candidates.length) continue;
    try {
      const expandedVia = withDiagnosticRecordingSuppressed(() => readableAutomaticVia(
        edge,
        from,
        to,
        start,
        end,
        candidateSides.fromSide,
        candidateSides.toSide,
      ));
      const expandedPoints = normalizeRoutePoints([start, ...expandedVia, end]);
      const outsideRightOrdinal = planned.rawCandidates.findIndex(({ family }) => (
        family === 'outside-right'
      ));
      const ordinal = pairOrdinal * 9 + Math.max(0, outsideRightOrdinal);
      plans.push({
        family: 'outside-right',
        ordinal,
        points: expandedPoints,
        cost: readableCandidateCost(
          edge,
          expandedPoints,
          ordinal,
          naturalFromSide,
          naturalToSide,
        ),
        ...candidateSides,
      });
    } catch (error) {
      if (error instanceof WorkflowLayoutFeedback) {
        feedback.push({ error, pairOrdinal });
      } else if (!firstFailure) {
        firstFailure = error;
      }
    }
  }

  plans.sort((left, right) => compareCost(left.cost, right.cost));
  if (plans.length) {
    const selected = plans[0];
    return {
      points: selected.points,
      fromSide: selected.fromSide,
      toSide: selected.toSide,
    };
  }

  const feedbackPriority = {
    'rank-gap-minimum': 0,
    'lane-gap-minimum': 1,
  };
  feedback.sort((left, right) => (
    (feedbackPriority[left.error.request?.kind] ?? 99)
      - (feedbackPriority[right.error.request?.kind] ?? 99)
    || left.pairOrdinal - right.pairOrdinal
  ));
  if (feedback.length) throw feedback[0].error;
  const authoredSideFields = [
    ...(authoredFrom ? ['fromSide'] : []),
    ...(authoredTo ? ['toSide'] : []),
  ];
  if (authoredSideFields.length) {
    const alternatives = verifiedPinRemovalAlternatives(
      edge,
      authoredSideFields,
      'ことで、readable-v2 が残りの端点側面固定値を再計画できるようにする',
    );
    const sourceAnchor = primaryPorts?.from || anchor(from, primarySides.fromSide);
    const targetAnchor = primaryPorts?.to || anchor(to, primarySides.toSide);
    const attemptedEvidence = firstFailure?.archifyDiagnostics?.[0]?.evidence || {};
    throwExplicitPinConflict(edge, '作成済み端点側面を使用した可読経路の実現可能性', {
      conflictingPins: conflictPinsFromRemovalSets(
        edge,
        alternatives.removalSets,
        authoredSideFields,
      ),
      actualCoordinates: {
        sourceAnchor: [...sourceAnchor],
        targetAnchor: [...targetAnchor],
      },
      fromSide: primarySides.fromSide,
      toSide: primarySides.toSide,
      ...(attemptedEvidence.attemptedCandidateFamilies
        ? { attemptedCandidateFamilies: attemptedEvidence.attemptedCandidateFamilies }
        : {}),
      ...(attemptedEvidence.candidateCount !== undefined
        ? { candidateCount: attemptedEvidence.candidateCount }
        : {}),
    }, alternatives.supportedFixes);
  }
  if (firstFailure) throw firstFailure;
  throw new Error('readable-v2 の自動経路列挙で結果が生成されませんでした');
}

function isReadableControlledRoute(edge) {
  return workflow.schema_version === 2 && (
    Array.isArray(edge.via)
    || edge.channelX !== undefined
    || edge.channelY !== undefined
    || (edge.route && edge.route !== 'auto')
  );
}

function readableControlledRoute(edge, from, to) {
  const authoredFrom = edge.fromSide && edge.fromSide !== 'auto' ? edge.fromSide : null;
  const authoredTo = edge.toSide && edge.toSide !== 'auto' ? edge.toSide : null;
  const naturalFromSide = authoredFrom || defaultFromSide(from, to);
  const naturalToSide = authoredTo || defaultToSide(from, to);
  const sideOrder = ['right', 'bottom', 'left', 'top'];
  const preferredPairs = [{
    fromSide: naturalFromSide,
    toSide: naturalToSide,
  }];
  for (const fromSide of authoredFrom ? [authoredFrom] : sideOrder) {
    for (const toSide of authoredTo ? [authoredTo] : sideOrder) {
      preferredPairs.push({ fromSide, toSide });
    }
  }

  const seen = new Set();
  const sidePairs = preferredPairs.filter(({ fromSide, toSide }) => {
    if (authoredFrom && fromSide !== authoredFrom) return false;
    if (authoredTo && toSide !== authoredTo) return false;
    const key = `${fromSide}:${toSide}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const hasAbsoluteRoutePins = Array.isArray(edge.via)
    || edge.channelX !== undefined
    || edge.channelY !== undefined;
  const candidates = [];
  const diagnosticCandidates = [];
  const materializedCandidates = [];
  for (const [ordinal, { fromSide, toSide }] of sidePairs.entries()) {
    const start = anchor(from, fromSide);
    const end = anchor(to, toSide);
    const via = routeVia(
      edge,
      from,
      to,
      start,
      end,
      fromSide,
      toSide,
      { validateReadablePreset: false },
    );
    const authoredPoints = [start, ...via, end];
    const points = hasAbsoluteRoutePins
      ? authoredPoints
      : normalizeRoutePoints(authoredPoints);
    const materialized = { points, fromSide, toSide, ordinal };
    materializedCandidates.push(materialized);
    if (points.length >= 2
      && points.every((point) => (
        Array.isArray(point) && point.length === 2 && isFinitePoint(...point)
      ))
      && routeHonorsEndpointSides(points, fromSide, toSide)) {
      diagnosticCandidates.push(materialized);
    }
    if (!readableCandidateIsFeasible(edge, points, from, to, fromSide, toSide)) continue;
    if (edge.route && edge.route !== 'auto' && !routeMatchesPresetFamily(
      edge.route,
      points,
      from,
      to,
    )) continue;
    if (presentChannelPins(edge).some((field) => (
      !routeContainsChannelPin(points, field, edge[field])
    ))) continue;
    candidates.push({
      points,
      fromSide,
      toSide,
      cost: readableCandidateCost(
        edge,
        points,
        ordinal,
        naturalFromSide,
        naturalToSide,
      ),
    });
  }
  candidates.sort((left, right) => compareCost(left.cost, right.cost));
  if (candidates.length) return candidates[0];

  // Absolute geometry is authoritative even when it is invalid. Preserve the
  // best endpoint-side inference so validation can diagnose the authored
  // segment or preset that actually failed instead of silently falling back to
  // default sides and changing the route's meaning.
  if (hasAbsoluteRoutePins) {
    return diagnosticCandidates[0] || materializedCandidates[0] || null;
  }

  // Preset-only routes retain their dedicated typed conflict (and verified
  // alternative search) when exhaustive side inference found no valid plan.
  const fallback = materializedCandidates[0];
  if (!fallback) return null;
  const fallbackVia = readablePresetVia(
    edge,
    from,
    to,
    fallback.points[0],
    fallback.points.at(-1),
    fallback.fromSide,
    fallback.toSide,
  );
  return {
    ...fallback,
    points: normalizeRoutePoints([
      fallback.points[0],
      ...fallbackVia,
      fallback.points.at(-1),
    ]),
  };
}

function pathFor(edge) {
  if (pathCache.has(edge)) return pathCache.get(edge);
  const from = nodes.get(edge.from);
  const to = nodes.get(edge.to);
  if (isReadableControlledRoute(edge)) {
    const planned = readableControlledRoute(edge, from, to);
    if (planned) {
      readableSideCache.set(edge, {
        fromSide: planned.fromSide,
        toSide: planned.toSide,
      });
      const routed = { d: polylinePath(planned.points), points: planned.points };
      pathCache.set(edge, routed);
      return routed;
    }
  }
  const ports = automaticPorts.get(edge);
  const { fromSide, toSide } = edgeSides(edge);
  const readableAutomatic = workflow.schema_version === 2
    && !Array.isArray(edge.via)
    && edge.channelX === undefined
    && edge.channelY === undefined
    && (!edge.route || edge.route === 'auto');
  if (readableAutomatic) {
    const planned = readableAutomaticRoute(
      edge,
      from,
      to,
      { fromSide, toSide },
      ports,
    );
    readableSideCache.set(edge, {
      fromSide: planned.fromSide,
      toSide: planned.toSide,
    });
    const routed = { d: polylinePath(planned.points), points: planned.points };
    pathCache.set(edge, routed);
    return routed;
  }
  const start = ports?.from || anchor(from, fromSide);
  const end = ports?.to || anchor(to, toSide);
  const authoredPoints = [start, ...routeVia(edge, from, to, start, end, fromSide, toSide), end];
  const hasAbsoluteRoutePins = Array.isArray(edge.via)
    || edge.channelX !== undefined
    || edge.channelY !== undefined;
  const points = workflow.schema_version === 2 && !hasAbsoluteRoutePins
    ? normalizeRoutePoints(authoredPoints)
    : authoredPoints;
  const routed = { d: polylinePath(points), points };
  pathCache.set(edge, routed);
  return routed;
}

function labelRectFor(edge, relationIndex) {
  if (!edge.label || !nodes.has(edge.from) || !nodes.has(edge.to)) return null;
  const [lx, ly] = workflowEdgeLabelPoint(edge, pathFor(edge).points);
  const width = workflowLabelWidth(edge.label);
  return {
    relation: edge,
    relationIndex,
    label: edge.label,
    x: lx - width / 2,
    y: ly - 10,
    width,
    height: 14,
    lx,
    ly,
  };
}

function measuredContentBounds() {
  let left = layout.laneX;
  let top = 27;
  let right = layout.laneX + layout.laneW;
  let bottom = legendY() + 18;
  const owners = {
    left: 'ワークフローレーン',
    top: asArray(workflow.phases).length ? 'フェーズヘッダーバンド' : 'ワークフロー上部の余白',
    right: 'ワークフローレーン',
    bottom: workflowLegendEntries.length ? '凡例' : 'ワークフローレーンと下部の余白',
  };
  const includePoint = ([x, y], contributor) => {
    if (x < left) {
      left = x;
      owners.left = contributor;
    }
    if (y < top) {
      top = y;
      owners.top = contributor;
    }
    if (x > right) {
      right = x;
      owners.right = contributor;
    }
    if (y > bottom) {
      bottom = y;
      owners.bottom = contributor;
    }
  };
  const includeRect = (rect, contributor) => {
    includePoint([rect.x, rect.y], contributor);
    includePoint([rect.x + rect.width, rect.y + rect.height], contributor);
  };

  for (const node of nodes.values()) includeRect(node, `ノード ${node.id}`);
  for (const [index, edge] of workflow.edges.entries()) {
    if (!nodes.has(edge.from) || !nodes.has(edge.to)) continue;
    for (const point of pathFor(edge).points) includePoint(point, `エッジ ${edge.id || index}`);
    const label = labelRectFor(edge, index);
    if (label) includeRect(label, `エッジ ${edge.id || index} のラベルマスク`);
  }
  for (const phase of asArray(workflow.phases)) {
    if (!Number.isInteger(phase.fromCol) || !Number.isInteger(phase.toCol)
      || phase.fromCol < 0 || phase.toCol >= layout.colXs.length || phase.fromCol > phase.toCol) continue;
    const span = phaseSpan(phase);
    includeRect({ x: span.x, y: 27, width: span.width, height: 16 }, `フェーズ ${phase.id}`);
  }
  for (const group of asArray(workflow.groups)) {
    if (!laneIndex.has(group.lane) || !Number.isInteger(group.fromCol) || !Number.isInteger(group.toCol)
      || group.fromCol < 0 || group.toCol >= layout.colXs.length || group.fromCol > group.toCol) continue;
    const span = groupSpan(group);
    includeRect({
      x: span.x,
      y: laneTop(group.lane) + layout.laneTitleH + GROUP_FRAME_TOP_INSET,
      width: span.width,
      height: workflow.schema_version === 2
        ? laneHeight(group.lane) - layout.laneTitleH
          - GROUP_FRAME_TOP_INSET - GROUP_FRAME_BOTTOM_INSET
        : layout.laneH - layout.laneTitleH - 16,
    }, `グループ ${group.id}`);
    if (workflow.schema_version === 2) {
      const frameY = laneTop(group.lane) + layout.laneTitleH + GROUP_FRAME_TOP_INSET;
      const labelBaseline = frameY + GROUP_LABEL_BASELINE_OFFSET;
      includeRect({
        x: span.x + 10,
        y: labelBaseline - GROUP_LABEL_MASK_ASCENT,
        width: textUnits(group.label) * 5.6,
        height: GROUP_LABEL_MASK_H,
      }, `グループ ${group.id} のラベル`);
    }
  }
  if (workflowLegendEntries.length) {
    for (const rect of workflowLegendRects()) includeRect(rect, `凡例 ${rect.kind}`);
  }
  return {
    left,
    top,
    right,
    bottom,
    contributors: [...new Set([
      ...Object.values(owners),
      ...asArray(layout.widthContributors),
      ...asArray(layout.heightContributors),
    ])],
  };
}

function finalizeReadableViewBox() {
  if (workflow.schema_version !== 2) {
    requiredViewBox = [...viewBox];
    return;
  }
  const bounds = measuredContentBounds();
  requiredViewBox = [
    Math.max(minimumCanvasWidth, Math.ceil(bounds.right + 16)),
    Math.max(autoHeight, Math.ceil(bounds.bottom + 18)),
  ];
  const outsideOrigin = bounds.left < 0 || bounds.top < 0;
  if (outsideOrigin) {
    const hasAbsolutePins = workflow.edges.some((edge) => (
      Array.isArray(edge.via)
      || Array.isArray(edge.labelAt)
      || edge.channelX !== undefined
      || edge.channelY !== undefined
    ));
    const message = `ワークフローの形状が viewBox の原点より上または左へはみ出しています（${Math.round(bounds.left)}, ${Math.round(bounds.top)}）。`;
    throwDiagnosticError(message, [{
      code: hasAbsolutePins ? 'workflow/explicit-pin-conflict' : 'workflow/solver-budget-exhausted',
      severity: 'error',
      message,
      subject: { diagramType: 'workflow', path: '/meta/viewBox' },
      evidence: {
        actualViewBox: [...viewBox],
        requiredViewBox: [...requiredViewBox],
        contentBounds: [bounds.left, bounds.top, bounds.right, bounds.bottom],
        contributors: bounds.contributors,
      },
      supportedFixes: [],
    }]);
  }
  if (!workflow.meta?.viewBox) {
    viewBox = [...requiredViewBox];
    return;
  }
  const tooNarrow = viewBox[0] < requiredViewBox[0];
  const tooShort = viewBox[1] < requiredViewBox[1];
  if (!tooNarrow && !tooShort) return;
  const message = `ワークフローの viewBox ${viewBox[0]}×${viewBox[1]} には readable-v2 レイアウトを収容できません。最小サイズは ${requiredViewBox[0]}×${requiredViewBox[1]} です。`;
  const supportedFixes = [];
  if (acceptsFix((document) => {
    document.meta.viewBox = [...requiredViewBox];
  })) {
    supportedFixes.push(`meta.viewBox を [${requiredViewBox[0]}, ${requiredViewBox[1]}] 以上に設定する`);
  }
  if (acceptsFix((document) => {
    delete document.meta.viewBox;
  })) {
    supportedFixes.push('コンパイラーが計測済みの固有キャンバスを使用できるよう meta.viewBox を省略する');
  }
  throwDiagnosticError(message, [{
    code: 'workflow/viewbox-capacity',
    severity: 'error',
    message,
    subject: { diagramType: 'workflow', path: '/meta/viewBox' },
    evidence: {
      actualViewBox: [...viewBox],
      requiredViewBox: [...requiredViewBox],
      contentBounds: [bounds.left, bounds.top, bounds.right, bounds.bottom],
      contributors: bounds.contributors,
    },
    supportedFixes,
  }]);
}

function renderLane(lane, index) {
  const y = laneTop(lane.id);
  const height = laneHeight(index);
  const exception = lane.variant === 'exception'
    ? `\n        <rect data-graph-role="structural-frame" data-composition-frame-kind="exception-lane" data-composition-frame-id="lane-${index}-exception" x="${layout.laneX + 6}" y="${y + 6}" width="${layout.laneW - 12}" height="${height - 12}" rx="8" class="c-security-group" stroke-width="1"/>`
    : '';
  const labelClass = lane.variant === 'exception' ? 't-security' : 't-dim';
  const prefix = lane.variant === 'exception' ? 'EX' : String(index + 1).padStart(2, '0');
  return `        <rect data-graph-role="structural-frame" data-composition-frame-kind="lane" data-composition-frame-id="lane-${index}" x="${layout.laneX}" y="${y}" width="${layout.laneW}" height="${height}" rx="10" class="c-lane" stroke-width="1"/>${exception}
        <text x="${layout.laneX + 14}" y="${y + 22}" class="${labelClass}" font-size="10" font-weight="600">${prefix} / ${esc(lane.label)}</text>`;
}

function renderPhase(phase) {
  const span = phaseSpan(phase);
  const accent = variantAccent(phase.variant);
  const [lineClass] = arrowClassMap[phase.variant || 'default'] || arrowClassMap.default;
  return `        <line x1="${span.x}" y1="35" x2="${span.x + span.width}" y2="35" class="${lineClass}" stroke-width="1.1"/>
        <rect x="${span.x}" y="27" width="${span.width}" height="16" rx="4" class="c-mask"/>
        <text x="${span.cx}" y="39" class="${accent}" font-size="8" font-weight="600" text-anchor="middle">${esc(phase.label)}</text>`;
}

function renderGroup(group, index) {
  const span = groupSpan(group);
  const y = laneTop(group.lane) + layout.laneTitleH + GROUP_FRAME_TOP_INSET;
  const height = workflow.schema_version === 2
    ? laneHeight(group.lane) - layout.laneTitleH
      - GROUP_FRAME_TOP_INSET - GROUP_FRAME_BOTTOM_INSET
    : layout.laneH - layout.laneTitleH - 16;
  const cls = group.variant === 'security' ? 'c-security-group' : 'c-lane';
  const textClass = variantAccent(group.variant);
  const labelY = workflow.schema_version === 2 ? y + GROUP_LABEL_BASELINE_OFFSET : y + 14;
  return `        <rect data-graph-role="structural-frame" data-composition-frame-kind="group" data-composition-frame-id="group-${index}" x="${span.x}" y="${y}" width="${span.width}" height="${height}" rx="9" class="${cls}" stroke-width="1"/>
        <text x="${span.x + 10}" y="${labelY}" class="${textClass}" font-size="7" font-weight="600">${esc(group.label)}</text>`;
}

function renderNode(node) {
  const fill = componentFill[node.type] || 'c-external';
  const accent = componentText[node.type] || 't-muted';
  const hasSub = node.sublabel != null && node.sublabel !== '';
  const labelFontSize = fittedNodeFontSize(node.label, brandLabelFitWidth(node, node.width), nodeTextFit.labelPreferred, nodeTextFit.labelMinimum);
  const sublabelFontSize = hasSub
    ? fittedNodeFontSize(node.sublabel, node.width, nodeTextFit.sublabelPreferred, nodeTextFit.sublabelMinimum)
    : nodeTextFit.sublabelPreferred;
  const sub = hasSub
    ? `\n          <text data-detail="context" x="${node.cx}" y="${node.y + 38}" class="t-muted" font-size="${sublabelFontSize}" text-anchor="middle">${esc(node.sublabel)}</text>`
    : '';
  const tag = node.tag
    ? `\n        <text data-detail="fine" x="${node.cx}" y="${node.y + node.height - 12}" class="${accent}" font-size="${fittedNodeFontSize(node.tag, node.width, nodeTextFit.tagPreferred, nodeTextFit.tagMinimum)}" text-anchor="middle">${esc(node.tag)}</text>`
    : '';
  const brand = renderBrandMark(node, { x: node.x + node.width - 22, y: node.y + 6 });
  const passport = { kind: node.type, sublabel: node.sublabel, tag: node.tag, context: nodeContext(node), ...brandMetadataFor(node) };
  return `        <g ${focusNodeAttrs(node.id, node.label, passport, workflow.meta.locale)}>
          ${focusNodeTitle(node.label, passport)}
          <rect x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" rx="6" class="c-mask"/>
          <rect x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" rx="6" class="${fill}"${animateAttr(workflow.meta, 'node', nodeStep(node))} stroke-width="1.5"/>
          ${renderSemanticSigil(node.type, { x: node.x + 6, y: node.y + 6 })}${brand ? `\n          ${brand}` : ''}
          <text data-node-label=""${hasSub ? ' data-detail-anchor=""' : ''} x="${node.cx}" y="${node.y + 21}" class="t-primary" font-size="${labelFontSize}" font-weight="600" text-anchor="middle">${esc(node.label)}</text>${sub}${tag}
        </g>`;
}

function renderEdgePath(edge, index) {
  const [cls, marker] = arrowClassMap[edge.variant || 'default'] || arrowClassMap.default;
  const routed = pathFor(edge);
  const strokeWidth = edge.width || (edge.variant === 'emphasis' ? 1.8 : 1.4);
  return `        <path ${focusEdgeAttrs(edge.from, edge.to, edge.label, index, edge.id)} data-composition-points="${routePointsValue(routed.points)}" d="${routed.d}" class="${cls}"${animateAttr(workflow.meta, 'edge', edgeSteps.get(edge))} stroke-width="${strokeWidth}" marker-end="url(#${marker})"/>`;
}

function renderEdgeLabel(edge, index) {
  if (!edge.label) return '';
  const routed = pathFor(edge);
  const [lx, ly] = workflowEdgeLabelPoint(edge, routed.points);
  const labelW = workflowLabelWidth(edge.label);
  return `        <g data-detail="context" ${focusEdgeAttrs(edge.from, edge.to, edge.label, index, edge.id)}>
          <rect x="${lx - labelW / 2}" y="${ly - 10}" width="${labelW}" height="14" rx="3" class="c-mask"/>
          <text x="${lx}" y="${ly}" class="${variantAccent(edge.variant, { dashed: 't-database' })}" font-size="8" text-anchor="middle">${esc(edge.label)}</text>
        </g>`;
}

function renderLegend() {
  const obstacles = workflow.schema_version === 2
    ? relationshipLegendObstacles(workflow.edges, {
        pointsFor: (edge) => pathFor(edge).points,
        labelRectFor,
      })
    : [];
  return renderResolvedLegend({
    entries: workflowLegendEntries,
    locale: workflow.meta.locale,
    layout: workflowLegendLayout(obstacles),
    renderSwatch: (entry) => `<rect x="${entry.x}" y="${entry.baseline - 8}" width="14" height="9" rx="2" class="${componentFill[entry.kind] || 'c-external'}" stroke-width="1"/>`,
  });
}

function renderSvg() {
  return `      <svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}" ${svgRootAttrs(workflow.meta, 'ワークフロー図')}>
${svgAccessibleText(workflow.meta, 'workflow')}
${renderDefinitions()}

        <!-- Background Grid -->
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- Swimlanes -->
${workflow.lanes.map(renderLane).join('\n\n')}

        <!-- Phase headers -->
${asArray(workflow.phases).map(renderPhase).join('\n')}

        <!-- Workflow groups -->
${asArray(workflow.groups).map(renderGroup).join('\n')}

        <!-- Edge paths -->
${workflow.edges.map(renderEdgePath).join('\n')}

        <!-- Nodes -->
${[...nodes.values()].map(renderNode).join('\n\n')}

        <!-- Edge labels -->
${workflow.edges.map(renderEdgeLabel).join('\n')}

        <!-- Legend -->
${renderLegend()}
      </svg>`;
}


  try {
    validateReadableInputsBeforeRouting();
    validateReadablePinnedGeometry();
    validateWorkflow();
    finalizeReadableViewBox();
    const svg = renderSvg();
    const receipt = {
      contract: layout.contract,
      viewBox: [...viewBox],
      requiredViewBox: [...requiredViewBox],
      columns: [...layout.colXs],
      nodes: [...nodes.values()].map((node) => ({
        id: node.id,
        lane: node.lane,
        col: node.col,
        x: node.x,
        y: node.y,
        width: node.width,
        height: node.height,
      })),
      edges: workflow.edges.map((edge) => ({
        id: edge.id ?? null,
        from: edge.from,
        to: edge.to,
        points: pathFor(edge).points.map((point) => [...point]),
      })),
      labels: workflow.edges.flatMap((edge) => {
        if (!edge.label || !nodes.has(edge.from) || !nodes.has(edge.to)) return [];
        const [x, y] = workflowEdgeLabelPoint(edge, pathFor(edge).points);
        return [{ edge: edge.id ?? null, label: edge.label, x, y, width: workflowLabelWidth(edge.label), height: 14 }];
      }),
      diagnostics: [],
    };
    return { ok: true, svg, receipt };
  } catch (error) {
    if (!Array.isArray(error?.archifyDiagnostics)) throw error;
    const diagnostics = error.archifyDiagnostics.map((diagnostic) => ({ ...diagnostic }));
    return compilerFailure(layout.contract, diagnostics, error.message);
  }
}

function feedbackFailure(request) {
  const message = `ワークフローエッジ "${request.edge || `${request.from}->${request.to}`}" は実行可能な自動経路を得られないまま、上限付き readable-v2 レイアウトフィードバックを使い切りました。`;
  const diagnostics = [{
    code: 'workflow/solver-budget-exhausted',
    severity: 'error',
    message,
    subject: {
      diagramType: 'workflow',
      edge: request.edge,
      from: request.from,
      to: request.to,
    },
    evidence: {
      attemptedCandidateFamilies: request.attemptedCandidateFamilies,
      candidateCount: request.candidateCount,
    },
    supportedFixes: [],
  }];
  return compilerFailure('readable-v2', diagnostics, message);
}

function compileWorkflowWithFeedback({ workflow, qualityProfile, discoverFixes = true } = {}) {
  let layoutFeedback = {};
  for (let attempt = 0; attempt <= MAX_READABLE_LAYOUT_FEEDBACK_ROUNDS; attempt += 1) {
    try {
      return compileWorkflowInternal({
        workflow,
        qualityProfile,
        discoverFixes,
        layoutFeedback,
      });
    } catch (error) {
      if (!(error instanceof WorkflowLayoutFeedback)) throw error;
      const request = error.request;
      let nextFeedback = null;
      if (request.kind === 'rank-gap-minimum'
        && Number.isInteger(request.fromCol)
        && Number.isInteger(request.toCol)
        && Number.isFinite(request.minimum)) {
        const key = `${request.fromCol}:${request.toCol}`;
        const current = layoutFeedback.rankGapMinimums?.[key] ?? -Infinity;
        if (request.minimum > current + 0.0001) {
          nextFeedback = {
            ...layoutFeedback,
            rankGapMinimums: {
              ...(layoutFeedback.rankGapMinimums || {}),
              [key]: request.minimum,
            },
            rankGapContributors: {
              ...(layoutFeedback.rankGapContributors || {}),
              [key]: [
                `ランク ${request.fromCol}→${request.toCol} の経路間隔`,
                `エッジ ${request.edge || `${request.from}->${request.to}`} の経路`,
              ],
            },
          };
        }
      } else if (request.kind === 'lane-gap-minimum'
        && Number.isFinite(request.minimum)
        && request.minimum > (layoutFeedback.laneGapMin ?? -Infinity) + 0.0001) {
        nextFeedback = {
          ...layoutFeedback,
          laneGapMin: request.minimum,
          laneGapContributors: [
            `エッジ ${request.edge || `${request.from}->${request.to}`} のレーン間経路間隔`,
          ],
        };
      }
      if (!nextFeedback || attempt === MAX_READABLE_LAYOUT_FEEDBACK_ROUNDS) {
        return feedbackFailure(request);
      }
      layoutFeedback = nextFeedback;
    }
  }
  throw new Error('到達不能な readable-v2 レイアウトフィードバック状態です');
}

export function compileWorkflow({ workflow, qualityProfile } = {}) {
  return compileWorkflowWithFeedback({ workflow, qualityProfile });
}
