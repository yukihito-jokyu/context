// Domain rules only. No coordinates, DOM, network, or external state engine.
import { throwDiagnosticProblems } from '../shared/diagnostics.mjs';

export const elementKinds = { state: '状態', phase: 'フェーズ', event: 'イベント', activity: '活動' };
export const relationKinds = { transition: '遷移', sequence: '順序', association: '関連' };

export function terminology(locale = 'ja') {
  if (locale === 'en') return { state: 'State', phase: 'Phase', event: 'Event', activity: 'Activity', transition: 'Transition', sequence: 'Sequence', association: 'Association', initial: 'Start', terminal: 'End', complete: 'Whole lifecycle', partial: 'Partial lifecycle', scope: 'Scope', repeat: 'Repeat', parallel: 'Parallel' };
  if (locale === 'zh-CN') return { state: '状态', phase: '阶段', event: '事件', activity: '活动', transition: '转换', sequence: '顺序', association: '关联', initial: '开始', terminal: '结束', complete: '完整生命周期', partial: '部分生命周期', scope: '范围', repeat: '重复', parallel: '并行' };
  return { ...elementKinds, ...relationKinds, initial: '開始', terminal: '終端', complete: '全体のライフサイクル', partial: '部分のライフサイクル', scope: '範囲', repeat: '反復', parallel: '並行' };
}

export function relationLabel(relation) {
  if (relation.kind === 'association') return relation.label || '';
  return [relation.label, relation.event, relation.condition && `[${relation.condition}]`, relation.action && `/ ${relation.action}`]
    .filter(Boolean).join(' · ');
}

export function lifecycleProblems(doc) {
  if (doc.schema_version !== 2) return [];
  const problems = [];
  const nodes = new Map(doc.states.map(node => [node.id, node]));
  const lanes = new Set(doc.lanes.map(lane => lane.id));
  const groups = new Map((doc.groups || []).map(group => [group.id, group]));
  const progression = doc.transitions.filter(edge => edge.kind !== 'association');
  if (nodes.size !== doc.states.length) problems.push('要素IDが重複しています。');
  if (lanes.size !== doc.lanes.length) problems.push('レーンIDが重複しています。');
  if (groups.size !== (doc.groups || []).length) problems.push('囲みIDが重複しています。');
  if (new Set(doc.transitions.map(edge => edge.id)).size !== doc.transitions.length) problems.push('関係IDが重複しています。');
  for (const node of doc.states) {
    if (!lanes.has(node.lane)) problems.push(`要素 "${node.id}" のレーン "${node.lane}" が存在しません。`);
  }
  const checkRefs = (ids, owner) => {
    if (new Set(ids).size !== ids.length) problems.push(`${owner}の要素IDが重複しています。`);
    for (const id of ids) if (!nodes.has(id)) problems.push(`${owner}の要素 "${id}" が存在しません。`);
  };
  checkRefs(doc.initial, '開始');
  checkRefs(doc.terminal, '終端');
  if (doc.subject.coverage === 'complete' && !doc.terminal.length) problems.push('全体を記述する場合は終端を指定してください。終了が範囲外ならcoverageをpartialにします。');
  for (const edge of doc.transitions) {
    checkRefs([...new Set([edge.from, edge.to])], `関係 "${edge.id}"`);
    const from = nodes.get(edge.from), to = nodes.get(edge.to);
    if (!from || !to) continue;
    if (edge.kind === 'transition' && !edge.event && !edge.condition) problems.push(`遷移 "${edge.id}" にはeventまたはconditionが必要です。`);
    if (edge.kind === 'transition' && [from, to].some(node => !['state', 'phase'].includes(node.kind))) {
      problems.push(`遷移 "${edge.id}" の両端は状態またはフェーズにしてください。イベントや活動の順序はsequenceで表します。`);
    }
    if (edge.kind === 'transition' && from.kind !== to.kind) problems.push(`遷移 "${edge.id}" は状態とフェーズの粒度を混在させています。両端のkindを揃えてください。`);
    if (edge.kind === 'association' && edge.from === edge.to) problems.push(`関連 "${edge.id}" は異なる要素に結び付けてください。`);
    if (edge.kind === 'association' && [edge.event, edge.condition, edge.action].some(Boolean)) {
      problems.push(`関連 "${edge.id}" に遷移のevent/condition/actionは指定できません。発火条件は要素のdescriptionで説明してください。`);
    }
    if (doc.terminal.includes(edge.from) && edge.kind !== 'association') problems.push(`全体の終端 "${edge.from}" から関係 "${edge.id}" が続いています。部分完了は囲みのterminalに指定してください。`);
  }
  // Directed reachability for progression; associations explain an already
  // reachable element but never make their far endpoint a new progression root.
  const reached = new Set(doc.initial.filter(id => nodes.has(id)));
  let changed = true;
  while (changed) {
    changed = false;
    for (const edge of progression) if (reached.has(edge.from) && nodes.has(edge.to) && !reached.has(edge.to)) {
      reached.add(edge.to); changed = true;
    }
  }
  const attached = new Set(reached);
  for (const edge of doc.transitions.filter(edge => edge.kind === 'association')) {
    if (reached.has(edge.from)) attached.add(edge.to);
    if (reached.has(edge.to)) attached.add(edge.from);
  }
  for (const node of doc.states) if (!attached.has(node.id)) problems.push(`要素 "${node.id}" は開始から到達できず、到達可能な要素への関連もありません。別の開始または省略範囲を明示してください。`);
  for (const id of doc.terminal) if (!reached.has(id)) problems.push(`終端 "${id}" は開始から到達できません。`);
  if (doc.subject.coverage === 'complete') {
    const canEnd = new Set(doc.terminal);
    let changed = true;
    while (changed) {
      changed = false;
      for (const edge of progression) if (canEnd.has(edge.to) && !canEnd.has(edge.from)) { canEnd.add(edge.from); changed = true; }
    }
    for (const id of reached) if (!canEnd.has(id)) problems.push(`要素 "${id}" から全体の終端へ到達する経路がありません。終了を範囲外にする場合はcoverageをpartialにしてください。`);
  }

  for (const group of groups.values()) {
    checkRefs(group.members, `囲み "${group.id}"`);
    if (nodes.has(group.id)) problems.push(`囲み "${group.id}" と要素のIDを分けてください。`);
    const members = new Set(group.members);
    if (group.parent) {
      const parent = groups.get(group.parent);
      if (!parent) problems.push(`囲み "${group.id}" の親 "${group.parent}" が存在しません。`);
      else if (group.members.some(id => !parent.members.includes(id))) problems.push(`囲み "${group.id}" の要素は親 "${group.parent}" にも含めてください。`);
    }
    const seen = new Set([group.id]);
    let parent = groups.get(group.parent);
    while (parent) {
      if (seen.has(parent.id)) { problems.push(`囲み "${group.id}" の親子関係が循環しています。`); break; }
      seen.add(parent.id); parent = groups.get(parent.parent);
    }
    for (const field of ['initial', 'terminal']) {
      checkRefs(group[field] || [], `囲み "${group.id}" の${field}`);
      for (const id of group[field] || []) if (!members.has(id)) problems.push(`囲み "${group.id}" の${field} "${id}" はmembers内に指定してください。`);
    }
    for (const edge of progression) {
      if ((group.terminal || []).includes(edge.from) && members.has(edge.to)) problems.push(`囲み "${group.id}" の終端 "${edge.from}" から囲み内の処理が続いています。`);
    }
    if (group.initial && group.terminal) {
      const reached = new Set(group.initial);
      let changed = true;
      while (changed) {
        changed = false;
        for (const edge of progression) if (members.has(edge.from) && members.has(edge.to) && reached.has(edge.from) && !reached.has(edge.to)) { reached.add(edge.to); changed = true; }
      }
      for (const id of group.terminal) if (!reached.has(id)) problems.push(`囲み "${group.id}" の終端 "${id}" は局所的な開始から到達できません。`);
    }
    if (group.kind === 'repeat') {
      if (!group.condition) problems.push(`反復の囲み "${group.id}" に継続または終了のconditionが必要です。`);
      const visiting = new Set(), visited = new Set();
      const hasCycle = id => {
        if (visiting.has(id)) return true;
        if (visited.has(id)) return false;
        visiting.add(id);
        if (progression.filter(edge => edge.from === id && members.has(edge.to)).some(edge => hasCycle(edge.to))) return true;
        visiting.delete(id); visited.add(id); return false;
      };
      if (!group.members.some(hasCycle)) problems.push(`反復の囲み "${group.id}" に戻り関係がありません。条件だけで反復を捏造せず、実際の関係を指定してください。`);
    }
    if (group.kind === 'parallel' && !group.completion) problems.push(`並行の囲み "${group.id}" にcompletion（全枝完了など）が必要です。`);
    if (group.kind === 'parallel' && progression.some(edge => members.has(edge.from) && members.has(edge.to))) {
      problems.push(`並行の囲み "${group.id}" の枝どうしを順序線で直列化できません。membersには独立した枝の代表要素を指定してください。`);
    }
  }
  const ancestors = (group) => {
    const ids = new Set(); let current = groups.get(group.parent);
    while (current && !ids.has(current.id)) { ids.add(current.id); current = groups.get(current.parent); }
    return ids;
  };
  const list = [...groups.values()];
  for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
    if (list[i].members.some(id => list[j].members.includes(id)) && !ancestors(list[i]).has(list[j].id) && !ancestors(list[j]).has(list[i].id)) {
      problems.push(`囲み "${list[i].id}" と "${list[j].id}" が同じ要素を共有しています。包含関係はparentで明示してください。`);
    }
  }
  return problems;
}

export function validateLifecycleModel(doc) {
  const problems = lifecycleProblems(doc);
  if (problems.length) throwDiagnosticProblems('ライフサイクルの意味検証に失敗しました', problems, {
    code: 'lifecycle/model', subject: { diagramType: 'lifecycle' },
  });
}
