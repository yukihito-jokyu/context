import { resolveLegend, legendFootprint } from '../shared/legend.mjs';
import { translateMessage } from '../shared/i18n.mjs';
import { terminology } from './model.mjs';

const colorKinds = ['start', 'active', 'waiting', 'decision', 'success', 'failure', 'neutral', 'external'];
export const elementColorTypes = { state: 'success', phase: 'waiting', event: 'start', activity: 'active' };

export function lifecycleElementColorType(node) {
  return node.type || elementColorTypes[node.kind];
}

// Semantic keys describe the diagram. Optional color keys describe only an
// explicitly authored type; an omitted type never invents a neutral state.
export function lifecycleLegendEntries(doc) {
  const terms = terminology(doc.meta.locale);
  const en = doc.meta.locale === 'en', zh = doc.meta.locale === 'zh-CN';
  const label = (ja, english, chinese) => en ? english : zh ? chinese : ja;
  const keys = ['state', 'phase', 'event', 'activity', 'initial', 'terminal', 'transition', 'sequence', 'association', 'scope', 'repeat', 'parallel'];
  const catalog = keys.map(kind => ({
    kind, label: terms[kind], interactive: false, swatchWidth: 22,
    // Explicit status colors have their own entries. A shape-only key avoids
    // suggesting that all states with overridden colors share one palette.
    colorType: elementColorTypes[kind] && !doc.states.some(node => node.kind === kind && node.type)
      ? elementColorTypes[kind] : undefined,
  }));
  catalog.push({ kind: 'group-phase', label: label('フェーズの囲み', 'Phase scope', '阶段范围'), interactive: false, swatchWidth: 22 });
  catalog.push(...colorKinds.map(kind => ({
    kind, interactive: false, swatchWidth: 22,
    label: `${label('配色', 'Color', '配色')}: ${kind === 'failure'
      ? label('失敗（終端とは限らない）', 'Failure (not necessarily final)', '失败（不一定终止）')
      : translateMessage(doc.meta.locale, `legend.lifecycle.${kind}`)}`,
  })));
  const present = new Set(doc.states.flatMap(node => [node.kind, ...(node.type ? [node.type] : [])]));
  if (doc.initial.length) present.add('initial');
  if (doc.terminal.length) present.add('terminal');
  doc.transitions.forEach(edge => present.add(edge.kind));
  (doc.groups || []).forEach(group => present.add(group.kind === 'phase' ? 'group-phase' : group.kind));
  return resolveLegend(doc.meta.legend, catalog, present);
}

export function lifecycleLegendReserve(doc, width) {
  const footprint = legendFootprint(lifecycleLegendEntries(doc), { width: width - 80 });
  return 122 + Math.max(0, footprint.rowCount - 3) * 22;
}
