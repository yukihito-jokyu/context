import { throwDiagnosticError } from './diagnostics.mjs';

const DEPLOYMENT_PROFILE = 'deployment-ownership';
const DEPLOYMENT_BOUNDARY_KINDS = new Set(['region', 'security-group']);
const PRIVATE_STATE_TYPES = new Set(['database']);

function subject(collection, index, item = {}) {
  return {
    diagramType: 'architecture',
    profile: DEPLOYMENT_PROFILE,
    collection,
    index,
    ...(item.id ? { id: item.id } : {}),
  };
}

function membership(boundaries, componentId, kind) {
  return boundaries
    .map((boundary, index) => ({ boundary, index }))
    .filter(({ boundary }) => boundary.kind === kind && boundary.wraps.includes(componentId));
}

export function deploymentOwnershipDiagnostics(diagram) {
  const components = Array.isArray(diagram.components) ? diagram.components : [];
  const boundaries = (Array.isArray(diagram.boundaries) ? diagram.boundaries : [])
    .map((boundary) => ({ ...boundary, wraps: Array.isArray(boundary.wraps) ? boundary.wraps : [] }));
  const connections = Array.isArray(diagram.connections) ? diagram.connections : [];
  const diagnostics = [];

  for (const kind of DEPLOYMENT_BOUNDARY_KINDS) {
    const count = boundaries.filter((boundary) => boundary.kind === kind).length;
    if (count > 0) continue;
    diagnostics.push({
      code: 'engineering/deployment-boundary-kind',
      severity: 'error',
      message: `デプロイメント所有権には${kind}境界が少なくとも1つ必要です。`,
      subject: subject('boundaries', -1),
      evidence: { requiredKind: kind, found: count },
      supportedFixes: [`明示的なwrapsリストを持つ${kind}境界を1つ追加する`],
    });
  }

  components.forEach((component, index) => {
    if (component.type === 'external') return;
    if (typeof component.tag !== 'string' || component.tag.trim() === '') {
      diagnostics.push({
        code: 'engineering/deployment-owner-missing',
        severity: 'error',
        message: `デプロイメントコンポーネント ${JSON.stringify(component.id)} のtagに所有者が記載されていません。`,
        subject: subject('components', index, component),
        evidence: { componentType: component.type, ownerField: 'tag' },
        supportedFixes: [`/components/${index}/tagに担当チームまたは所有者を設定する`],
      });
    }

    const regions = membership(boundaries, component.id, 'region');
    if (regions.length === 0) {
      diagnostics.push({
        code: 'engineering/deployment-region-scope',
        severity: 'error',
        message: `デプロイメントコンポーネント ${JSON.stringify(component.id)} がregion境界に割り当てられていません。`,
        subject: subject('components', index, component),
        evidence: { componentType: component.type, regionMemberships: 0 },
        supportedFixes: ['実際のregion境界のwrapsリストへコンポーネントIDを追加する'],
      });
    } else if (regions.length > 1) {
      diagnostics.push({
        code: 'engineering/deployment-region-ambiguous',
        severity: 'error',
        message: `デプロイメントコンポーネント ${JSON.stringify(component.id)} が複数のregion境界に属しています。`,
        subject: subject('components', index, component),
        evidence: {
          componentType: component.type,
          regions: regions.map(({ boundary, index: boundaryIndex }) => ({ boundaryIndex, label: boundary.label })),
        },
        supportedFixes: ['コンポーネントIDを実際のregion境界1つだけのwrapsリストに残す'],
      });
    }

    if (PRIVATE_STATE_TYPES.has(component.type)) {
      const privateScopes = membership(boundaries, component.id, 'security-group');
      if (privateScopes.length === 0) {
        diagnostics.push({
          code: 'engineering/deployment-private-state',
          severity: 'error',
          message: `ステートフルコンポーネント ${JSON.stringify(component.id)} が非公開security-group境界に割り当てられていません。`,
          subject: subject('components', index, component),
          evidence: { componentType: component.type, privateMemberships: 0 },
          supportedFixes: ['実際の非公開security-group境界のwrapsリストへコンポーネントIDを追加する'],
        });
      }
    }
  });

  boundaries.forEach((boundary, index) => {
    if (boundary.kind !== 'security-group') return;
    const members = boundary.wraps.map((id) => ({
      id,
      regions: membership(boundaries, id, 'region').map(({ boundary: region, index: boundaryIndex }) => ({
        boundaryIndex,
        label: region.label,
      })),
    }));
    const regionIndexes = new Set(members.flatMap((member) => member.regions.map((region) => region.boundaryIndex)));
    const consistent = members.length > 0
      && members.every((member) => member.regions.length === 1)
      && regionIndexes.size === 1;
    if (consistent) return;
    diagnostics.push({
      code: 'engineering/deployment-private-region-consistency',
      severity: 'error',
      message: `非公開境界 ${JSON.stringify(boundary.label)} には、共有regionが1つだけのコンポーネントを含める必要があります。`,
      subject: subject('boundaries', index, boundary),
      evidence: { boundaryKind: boundary.kind, members },
      supportedFixes: ['すべての非公開境界コンポーネントを共有region境界1つだけに割り当てる'],
    });
  });

  connections.forEach((connection, index) => {
    const crossedBoundaries = boundaries
      .map((boundary, boundaryIndex) => ({
        boundaryIndex,
        kind: boundary.kind,
        label: boundary.label,
        fromInside: boundary.wraps.includes(connection.from),
        toInside: boundary.wraps.includes(connection.to),
      }))
      .filter((boundary) => DEPLOYMENT_BOUNDARY_KINDS.has(boundary.kind) && boundary.fromInside !== boundary.toInside);
    if (crossedBoundaries.length === 0 || (typeof connection.label === 'string' && connection.label.trim() !== '')) return;
    diagnostics.push({
      code: 'engineering/deployment-crossing-mechanism',
      severity: 'error',
      message: `境界をまたぐ接続 ${JSON.stringify(connection.id || `${connection.from}->${connection.to}`)} に仕組みの名称がありません。`,
      subject: subject('connections', index, connection),
      evidence: {
        from: connection.from,
        to: connection.to,
        crossedBoundaries: crossedBoundaries.map(({ boundaryIndex, kind, label }) => ({ boundaryIndex, kind, label })),
      },
      supportedFixes: [`/connections/${index}/labelに実際の境界間の仕組みを設定する`],
    });
  });

  return diagnostics;
}

export function validateEngineeringProfile(diagramType, diagram) {
  const profile = diagram.meta?.engineering_profile;
  if (!profile) return;
  if (diagramType !== 'architecture' || profile !== DEPLOYMENT_PROFILE) return;
  const diagnostics = deploymentOwnershipDiagnostics(diagram);
  if (!diagnostics.length) return;
  throwDiagnosticError(
    `エンジニアリングプロファイル ${JSON.stringify(profile)} に失敗しました:\n${diagnostics.map((entry) => `- ${entry.message}`).join('\n')}`,
    diagnostics,
  );
}
