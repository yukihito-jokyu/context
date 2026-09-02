/** Grid placement for architecture IR (#8). Not auto-layout — fixed cell math only. */

export const DEFAULT_GRID = {
  mode: 'grid',
  origin: [40, 80],
  cols: 4,
  gapX: 30,
  gapY: 40,
  cellW: 130,
  cellH: 64,
};

export function gridLayout(arch) {
  const raw = arch.layout;
  if (!raw || raw.mode !== 'grid') return null;
  return { ...DEFAULT_GRID, ...raw };
}

export function resolveComponentPos(component, grid) {
  if (Array.isArray(component.pos) && component.pos.length === 2) {
    return component.pos;
  }
  if (!grid) return [NaN, NaN];
  if (!Number.isInteger(component.row) || !Number.isInteger(component.col)) {
    return [NaN, NaN];
  }
  const [ox, oy] = grid.origin;
  const stepX = grid.cellW + grid.gapX;
  const stepY = grid.cellH + grid.gapY;
  return [ox + component.col * stepX, oy + component.row * stepY];
}

export function validateGridPlacement(arch, grid, problems) {
  if (!grid) return;
  if (arch.layout !== undefined && arch.layout.mode !== 'grid') {
    problems.push('layout を指定する場合、layout.mode は "grid" である必要があります（自由配置では layout 自体を省略します）。');
    return;
  }
  const seen = new Map();
  for (const c of arch.components ?? []) {
    const hasPos = Array.isArray(c.pos) && c.pos.length === 2;
    const hasCell = Number.isInteger(c.row) && Number.isInteger(c.col);
    if (hasPos) continue; // pos wins; row/col are optional hints only
    if (!hasPos && !hasCell) {
      problems.push(`コンポーネント "${c.id}" には pos [x,y]、または layout.mode が "grid" の場合は row/col が必要です。`);
      continue;
    }
    if (c.row < 0 || c.col < 0) {
      problems.push(`コンポーネント "${c.id}" の row/col は0以上の整数である必要があります。`);
      continue;
    }
    if (c.col >= grid.cols) {
      problems.push(`コンポーネント "${c.id}" の col ${c.col} が layout.cols ${grid.cols} を超えています（有効範囲: 0..${grid.cols - 1}）。`);
    }
    const key = `${c.row},${c.col}`;
    if (seen.has(key)) {
      problems.push(`コンポーネント "${seen.get(key)}" と "${c.id}" が同じグリッドセル row ${c.row}、col ${c.col} を使用しています。`);
    } else {
      seen.set(key, c.id);
    }
  }
}
