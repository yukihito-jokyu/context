import { compileWorkflow } from '../renderers/workflow/workflow-compiler.mjs';
import {
  createMappedWorkflowCandidate,
  intrinsicWorkflow,
  planningWorkflow,
} from '../renderers/workflow/workflow-migration-geometry.mjs';
import { validateSchema } from '../renderers/shared/validator.mjs';

export { createHorizontalRankMapper } from '../renderers/workflow/workflow-migration-geometry.mjs';

const TARGET_SCHEMA_VERSION = 2;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function diagnostic({ code, message, subject = {}, evidence = {}, supportedFixes = [] }) {
  return {
    code,
    severity: 'error',
    message,
    subject,
    evidence,
    supportedFixes,
  };
}

function schemaDiagnostics(workflow) {
  try {
    validateSchema('workflow', workflow);
    return [];
  } catch (error) {
    if (Array.isArray(error?.archifyDiagnostics)) {
      return error.archifyDiagnostics.map((entry) => ({ ...entry }));
    }
    throw error;
  }
}

function legacyLayoutProbe(workflow, qualityProfile) {
  // The probe discovers fixed-v1 rank centers, not authored canvas capacity.
  // Omitting viewBox lets a capacity-only legacy failure reach the v2 compiler,
  // which can measure and monotonically expand the real migrated document.
  const probe = {
    schema_version: 1,
    diagram_type: 'workflow',
    meta: {
      title: workflow.meta.title,
      ...(workflow.meta.locale ? { locale: workflow.meta.locale } : {}),
      legend: { mode: 'hidden' },
    },
    lanes: clone(workflow.lanes),
    nodes: [{
      id: 'migration_probe',
      lane: workflow.lanes[0].id,
      col: 0,
      type: 'backend',
      label: 'Probe',
    }],
    edges: [],
  };
  return compileWorkflow({ workflow: probe, qualityProfile });
}

function legacyRequirementProbe(workflow, qualityProfile) {
  // Measure the complete fixed-v1 document without treating an authored
  // viewBox as its intrinsic requirement. The authored viewBox remains a
  // migration capacity and is preserved separately on the migrated document.
  const probe = clone(workflow);
  delete probe.meta.viewBox;
  return compileWorkflow({ workflow: probe, qualityProfile });
}

function requiredViewBoxFrom(result) {
  if (Array.isArray(result?.receipt?.requiredViewBox)) {
    return [...result.receipt.requiredViewBox];
  }
  const required = result?.diagnostics
    ?.map((entry) => entry?.evidence?.requiredViewBox)
    .find((candidate) => Array.isArray(candidate) && candidate.length === 2);
  return required ? [...required] : null;
}

function expandableViewBox(result) {
  if (result.ok || !result.diagnostics?.length) return null;
  if (!result.diagnostics.every((entry) => entry.code === 'workflow/viewbox-capacity')) return null;
  return requiredViewBoxFrom(result);
}

function result({
  ok,
  document,
  fromSchemaVersion = 1,
  preExistingDiagnostics = [],
  migrationDiagnostics = [],
  newSchemaDiagnostics = [],
  changedCoordinates = [],
  oldRequiredViewBox = null,
  newRequiredViewBox = null,
}) {
  return {
    ok,
    ...(document ? { document } : {}),
    fromSchemaVersion,
    toSchemaVersion: TARGET_SCHEMA_VERSION,
    preExistingDiagnostics,
    migrationDiagnostics,
    newSchemaDiagnostics,
    changedCoordinates,
    oldRequiredViewBox,
    newRequiredViewBox,
  };
}

export function migrateWorkflowDocument(inputWorkflow) {
  if (!inputWorkflow || typeof inputWorkflow !== 'object' || Array.isArray(inputWorkflow)) {
    return result({
      ok: false,
      migrationDiagnostics: [diagnostic({
        code: 'migration/source-document',
        message: 'ワークフローの移行には、解析済みJSONオブジェクトが1つ必要です。',
        supportedFixes: ['workflowスキーマv1のJSON文書を1つ指定する'],
      })],
    });
  }
  // Migration has no quality override: the authored policy (or effective
  // standard default) must validate the document after it leaves this process.
  const qualityProfile = inputWorkflow.meta?.quality_profile || 'standard';

  const workflow = clone(inputWorkflow);
  const preExistingDiagnostics = schemaDiagnostics(workflow);
  if (preExistingDiagnostics.length) {
    return result({
      ok: false,
      fromSchemaVersion: workflow.schema_version,
      preExistingDiagnostics,
    });
  }
  if (workflow.schema_version === TARGET_SCHEMA_VERSION) {
    const compiled = compileWorkflow({ workflow: clone(workflow), qualityProfile });
    const requiredViewBox = requiredViewBoxFrom(compiled);
    if (!compiled.ok) {
      return result({
        ok: false,
        fromSchemaVersion: TARGET_SCHEMA_VERSION,
        preExistingDiagnostics: compiled.diagnostics,
        oldRequiredViewBox: requiredViewBox,
        newRequiredViewBox: requiredViewBox,
      });
    }
    return result({
      ok: true,
      document: workflow,
      fromSchemaVersion: TARGET_SCHEMA_VERSION,
      oldRequiredViewBox: requiredViewBox,
      newRequiredViewBox: requiredViewBox,
    });
  }
  if (workflow.schema_version !== 1) {
    return result({
      ok: false,
      fromSchemaVersion: workflow.schema_version,
      migrationDiagnostics: [diagnostic({
        code: 'migration/source-schema-version',
        message: 'workflowスキーマv2への移行には、スキーマv1またはv2のソースが必要です。',
        subject: { path: '/schema_version' },
        evidence: { actual: workflow.schema_version, expected: [1, 2] },
        supportedFixes: ['未変更のスキーマv1 workflow、または移行済みのスキーマv2 workflowをソースとして使用する'],
      })],
    });
  }

  const legacy = compileWorkflow({ workflow: clone(workflow), qualityProfile });
  const legacyProbe = legacyLayoutProbe(workflow, qualityProfile);
  if (!legacyProbe.ok) {
    return result({
      ok: false,
      preExistingDiagnostics: legacy.ok ? [] : legacy.diagnostics,
      migrationDiagnostics: legacyProbe.diagnostics,
    });
  }
  const legacyRequirement = legacyRequirementProbe(workflow, qualityProfile);
  const oldRequiredViewBox = requiredViewBoxFrom(legacyRequirement)
    || requiredViewBoxFrom(legacyProbe)
    || requiredViewBoxFrom(legacy);
  const preExistingLayoutDiagnostics = legacy.ok ? [] : legacy.diagnostics;

  let planned = compileWorkflow({ workflow: intrinsicWorkflow(workflow), qualityProfile });
  if (!planned.ok) {
    // Old absolute pins can be invalid at the new rank centers before their X
    // coordinates are mapped. Obtain the same rank plan from an automatic-route
    // projection, then validate every authored pin again after mapping.
    planned = compileWorkflow({ workflow: planningWorkflow(workflow), qualityProfile });
  }
  if (!planned.ok) {
    return result({
      ok: false,
      preExistingDiagnostics: preExistingLayoutDiagnostics,
      newSchemaDiagnostics: planned.diagnostics,
      oldRequiredViewBox,
      newRequiredViewBox: requiredViewBoxFrom(planned),
    });
  }

  let mappedCandidate;
  try {
    mappedCandidate = createMappedWorkflowCandidate(
      workflow,
      legacyProbe.receipt.columns,
      planned.receipt.columns,
    );
  } catch (error) {
    return result({
      ok: false,
      preExistingDiagnostics: preExistingLayoutDiagnostics,
      migrationDiagnostics: [diagnostic({
        code: 'migration/rank-mapping',
        message: '安定した水平方向のランク対応を構築できませんでした。',
        evidence: { reason: error.message },
        supportedFixes: ['workflowとコンパイラーレシートをArchifyのメンテナーへ報告する'],
      })],
      oldRequiredViewBox,
      newRequiredViewBox: requiredViewBoxFrom(planned),
    });
  }

  const { document: migrated, changedCoordinates } = mappedCandidate;

  let compiled = compileWorkflow({ workflow: migrated, qualityProfile });
  const requiredExpansion = migrated.meta.viewBox ? expandableViewBox(compiled) : null;
  if (requiredExpansion) {
    const current = migrated.meta.viewBox;
    const expanded = [
      Math.max(current[0], requiredExpansion[0]),
      Math.max(current[1], requiredExpansion[1]),
    ];
    if (expanded[0] > current[0] || expanded[1] > current[1]) {
      migrated.meta.viewBox = expanded;
      compiled = compileWorkflow({ workflow: migrated, qualityProfile });
    }
  }

  const newRequiredViewBox = requiredViewBoxFrom(compiled) || requiredViewBoxFrom(planned);
  if (!compiled.ok) {
    return result({
      ok: false,
      preExistingDiagnostics: preExistingLayoutDiagnostics,
      newSchemaDiagnostics: compiled.diagnostics,
      changedCoordinates,
      oldRequiredViewBox,
      newRequiredViewBox,
    });
  }

  const migratedSchemaDiagnostics = schemaDiagnostics(migrated);
  if (migratedSchemaDiagnostics.length) {
    return result({
      ok: false,
      preExistingDiagnostics: preExistingLayoutDiagnostics,
      newSchemaDiagnostics: migratedSchemaDiagnostics,
      changedCoordinates,
      oldRequiredViewBox,
      newRequiredViewBox,
    });
  }

  return result({
    ok: true,
    document: migrated,
    preExistingDiagnostics: preExistingLayoutDiagnostics,
    changedCoordinates,
    oldRequiredViewBox,
    newRequiredViewBox,
  });
}

export function serializeMigratedWorkflow(workflow) {
  return `${JSON.stringify(workflow, null, 2)}\n`;
}
