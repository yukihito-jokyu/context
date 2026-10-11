import { textUnits } from '../shared/utils.mjs';
import { lifecycleLegendReserve } from './legend.mjs';

// Grid coordinates affect presentation only: they never create relations.
export function layoutLifecycle(doc) {
  const cellWidth = Math.max(210, ...doc.states.map(node => Math.max(
    node.width || 0, textUnits(node.label) * 8 + 36,
    textUnits(node.sublabel || '') * 6 + 36,
  )));
  const cellHeight = Math.max(80, ...doc.states.map(node => node.height || 0));
  const colStep = cellWidth + 120;
  const rowStep = cellHeight + 90;
  const lanePositions = new Map();
  let nextY = 120;
  for (const lane of doc.lanes) {
    const rows = Math.max(0, ...doc.states.filter(node => node.lane === lane.id).map(node => node.row)) + 1;
    lanePositions.set(lane.id, { y: nextY, rows });
    nextY += rows * rowStep + 70;
  }
  const states = new Map(doc.states.map(node => {
    const width = node.width || cellWidth, height = node.height || cellHeight;
    const x = 110 + node.col * colStep + (cellWidth - width) / 2;
    const y = lanePositions.get(node.lane).y + node.row * rowStep;
    return [node.id, { ...node, width, height, x, y, cx: x + width / 2, cy: y + height / 2 }];
  }));
  const groups = new Map();
  const measureGroup = group => {
    if (groups.has(group.id)) return groups.get(group.id);
    const children = (doc.groups || []).filter(child => child.parent === group.id).map(measureGroup);
    const members = group.members.map(id => states.get(id));
    const boxes = [...members, ...children];
    const x = Math.min(...boxes.map(box => box.x)) - 24;
    const y = Math.min(...boxes.map(box => box.y)) - 40;
    const right = Math.max(...boxes.map(box => box.x + box.width)) + 24;
    const bottom = Math.max(...boxes.map(box => box.y + box.height)) + 24;
    const box = { ...group, x, y, width: right - x, height: bottom - y };
    groups.set(group.id, box);
    return box;
  };
  (doc.groups || []).forEach(measureGroup);
  const allBoxes = [...states.values(), ...groups.values()];
  const width = Math.max(760, textUnits(`${doc.subject.label} · ${doc.subject.beginning} → ${doc.subject.ending}`) * 6 + 80, ...allBoxes.map(box => box.x + box.width + 110));
  const height = Math.max(360, ...allBoxes.map(box => box.y + box.height + 130)) + lifecycleLegendReserve(doc, width) - 122;
  return { states, groups, lanes: lanePositions, viewBox: doc.meta.viewBox || [width, height] };
}
