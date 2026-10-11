import { throwDiagnosticProblems } from './diagnostics.mjs';

// Where each diagram type keeps its focusable nodes. Composite types expose
// the nodes of both halves, matching what the viewer can focus.
const NODE_COLLECTIONS = {
  architecture: [['components']],
  workflow: [['nodes']],
  sequence: [['participants']],
  dataflow: [['nodes']],
  lifecycle: [['states']],
  class: [['classes']],
  er: [['entities']],
  'sequence-er': [['sequence', 'participants'], ['er', 'entities']],
  'workflow-er': [['workflow', 'nodes'], ['er', 'entities']],
};

export function hierarchyNodes(diagramType, diagram) {
  const paths = NODE_COLLECTIONS[diagramType] || [];
  return paths.flatMap((segments) => {
    const collection = segments.reduce((value, key) => value?.[key], diagram);
    return Array.isArray(collection) ? collection.filter((node) => node && typeof node.id === 'string') : [];
  });
}

// Composite diagrams namespace the ids of each half in the rendered SVG
// (renderers/sequence-er/compose.mjs); the viewer, focus anchors and rendered
// links all use those ids.
const RENDERED_PREFIXES = {
  'sequence-er': ['seq-', 'er-'],
  'workflow-er': ['flow-', 'er-'],
};

// Each node with the id it carries in the rendered SVG.
export function hierarchyNodeEntries(diagramType, diagram) {
  const paths = NODE_COLLECTIONS[diagramType] || [];
  const prefixes = RENDERED_PREFIXES[diagramType] || [];
  return paths.flatMap((segments, index) => {
    const collection = segments.reduce((value, key) => value?.[key], diagram);
    if (!Array.isArray(collection)) return [];
    return collection.filter((node) => node && typeof node.id === 'string')
      .map((node) => ({ node, renderedId: `${prefixes[index] || ''}${node.id}` }));
  });
}

// Architecture boundaries can carry one link for the nodes they wrap: several
// nodes that together make up one detail diagram link once, as a group. The
// group is returned as a link carrier with its member ids; its `link` object
// is the spec's own, so sync writes land in the boundary.
export function hierarchyGroups(diagramType, diagram) {
  if (diagramType !== 'architecture' || !Array.isArray(diagram?.boundaries)) return [];
  return diagram.boundaries
    .filter((boundary) => boundary && boundary.link && typeof boundary.id === 'string')
    .map((boundary) => ({ id: boundary.id, label: boundary.label, link: boundary.link, members: [...(boundary.wraps || [])], group: true }));
}

// Everything that can carry a link: nodes, then groups.
export function hierarchyLinkCarriers(diagramType, diagram) {
  const groups = hierarchyGroups(diagramType, diagram);
  return [...hierarchyNodes(diagramType, diagram), ...groups];
}

// In-diagram facts only. Whether a link target exists is a cross-file fact
// owned by scripts/check-hierarchy.mjs, because a single render cannot see
// the sibling artifacts.
export function validateHierarchy(diagramType, diagram) {
  const hierarchy = diagram?.meta?.hierarchy;
  const nodes = hierarchyNodes(diagramType, diagram);
  const ids = new Set(nodes.map((node) => node.id));
  const subject = { diagramType, path: '/meta/hierarchy' };
  const groups = hierarchyGroups(diagramType, diagram);
  const groupProblems = [];
  const groupIds = new Set();
  groups.forEach((group) => {
    if (ids.has(group.id) || groupIds.has(group.id)) groupProblems.push(`囲み ${JSON.stringify(group.id)} の id がノードまたは他の囲みと重複しています`);
    groupIds.add(group.id);
    group.members.filter((member) => nodes.find((node) => node.id === member)?.link)
      .forEach((member) => groupProblems.push(`囲み ${JSON.stringify(group.id)} がリンクを持つため、中のノード ${JSON.stringify(member)} には link を書けません`));
  });
  if (groupProblems.length) {
    throwDiagnosticProblems('階層リンクの検証に失敗しました', groupProblems, { code: 'hierarchy/group-link', subject });
  }
  // Nodes inside a linked boundary are covered by the boundary's link.
  const grouped = new Set(groups.flatMap((group) => group.members));

  const leafProblems = [];
  const leafIds = new Set();
  (hierarchy?.leaf_nodes || []).forEach((leaf, index) => {
    if (!ids.has(leaf.id)) leafProblems.push(`/meta/hierarchy/leaf_nodes/${index} の id ${JSON.stringify(leaf.id)} は図のノードに存在しません`);
    if (leafIds.has(leaf.id)) leafProblems.push(`/meta/hierarchy/leaf_nodes/${index} の id ${JSON.stringify(leaf.id)} が重複しています`);
    leafIds.add(leaf.id);
  });
  nodes.forEach((node) => {
    if (node.link && leafIds.has(node.id)) leafProblems.push(`ノード ${JSON.stringify(node.id)} は link を持つため leaf_nodes に含められません`);
  });
  if (leafProblems.length) {
    throwDiagnosticProblems('階層リンクの検証に失敗しました', leafProblems, { code: 'hierarchy/leaf-node', subject });
  }

  if (hierarchy?.require_links === true) {
    const missing = nodes.filter((node) => !node.link && !leafIds.has(node.id) && !grouped.has(node.id))
      .map((node) => `ノード ${JSON.stringify(node.id)}（${node.label ?? node.name ?? node.id}）に遷移先がありません。link を追加して詳細図を作るか、理由付きで leaf_nodes に登録してください`);
    if (missing.length) {
      throwDiagnosticProblems('階層リンクの検証に失敗しました', missing, { code: 'hierarchy/missing-link', subject });
    }
  }
}

// Only navigation the viewer renders outside the SVG travels as JSON; node
// links already live on the nodes as data attributes.
export function hierarchyViewerPayload(meta) {
  const hierarchy = meta?.hierarchy;
  if (!hierarchy || (!hierarchy.parent && !hierarchy.map && !hierarchy.trail?.length && !hierarchy.siblings?.length && !hierarchy.incoming?.length && !hierarchy.role)) return null;
  return {
    parent: hierarchy.parent ? { href: hierarchy.parent.href, label: hierarchy.parent.label } : null,
    map: hierarchy.map ? { href: hierarchy.map.href, label: hierarchy.map.label || null } : null,
    trail: (hierarchy.trail || []).map((crumb) => ({ href: crumb.href, label: crumb.label, focus: crumb.focus || null })),
    siblings: (hierarchy.siblings || []).map((crumb) => ({ href: crumb.href, label: crumb.label })),
    incoming: (hierarchy.incoming || []).map((entry) => ({ href: entry.href, label: entry.label, node: entry.node, nodeLabel: entry.node_label || entry.node, focus: entry.focus || null })),
    level: (hierarchy.trail || []).length,
    title: meta.title,
    role: hierarchy.role || null,
  };
}
