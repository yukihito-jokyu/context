import * as validators from './generated-validators.mjs';
import { throwDiagnosticError } from './diagnostics.mjs';

// "/nodes/3/label" reads much better as "/nodes/3 (id: "router") /label" for the
// LLM fixing the JSON; resolve the nearest enclosing element's id or label.
function annotatedPath(instancePath, data) {
  if (!instancePath) return { path: '/', identity: null };
  let node = data;
  let hint = null;
  for (const seg of instancePath.split('/').slice(1)) {
    if (node == null || typeof node !== 'object') break;
    node = node[/^\d+$/.test(seg) ? Number(seg) : seg];
    if (node && typeof node === 'object' && !Array.isArray(node)) {
      const tag = node.id ?? node.label;
      if (tag != null) hint = String(tag);
    }
  }
  return { path: instancePath, identity: hint };
}

function annotatePath(instancePath, data) {
  const annotated = annotatedPath(instancePath, data);
  return annotated.identity != null
    ? `${annotated.path} (id/label: ${JSON.stringify(annotated.identity)})`
    : annotated.path;
}

function schemaErrorMessage(error) {
  return {
    additionalProperties: `未対応のプロパティ ${JSON.stringify(error.params?.additionalProperty)} を含めることはできません`,
    required: `必須プロパティ ${JSON.stringify(error.params?.missingProperty)} が必要です`,
    type: `${JSON.stringify(error.params?.type)} 型でなければなりません`,
    enum: `許可された値 ${JSON.stringify(error.params?.allowedValues || [])} のいずれかでなければなりません`,
    pattern: `パターン ${JSON.stringify(error.params?.pattern)} に一致しなければなりません`,
    minimum: `${error.params?.comparison || '>='} ${error.params?.limit} を満たさなければなりません`,
    maximum: `${error.params?.comparison || '<='} ${error.params?.limit} を満たさなければなりません`,
    minItems: `少なくとも${error.params?.limit}項目が必要です`,
    maxItems: `最大${error.params?.limit}項目まで指定できます`,
    minLength: `少なくとも${error.params?.limit}文字が必要です`,
    maxLength: `最大${error.params?.limit}文字まで指定できます`,
  }[error.keyword] || `スキーマ条件 ${JSON.stringify(error.keyword)} を満たしていません`;
}

function formatErrors(errors, data) {
  return errors.map((e) => {
    const where = annotatePath(e.instancePath, data);
    const detail = e.params && Object.keys(e.params).length
      ? ' ' + JSON.stringify(e.params)
      : '';
    return `  ${where} ${schemaErrorMessage(e)}${detail}`;
  }).join('\n');
}

export function validateSchema(diagramType, data) {
  const validate = validators[diagramType];
  if (!validate) {
    throw new Error(`validateSchema: 不明な図の種類 "${diagramType}"`);
  }
  if (!validate(data)) {
    const diagnostics = validate.errors.map((error) => {
      const annotated = annotatedPath(error.instancePath, data);
      const subject = {
        diagramType,
        path: annotated.path,
        ...(annotated.identity != null ? { identity: String(annotated.identity) } : {}),
      };
      const evidence = {
        keyword: error.keyword,
        expected: error.schema,
        ...error.params,
      };
      const supportedFixes = {
        additionalProperties: [`未対応のプロパティ ${JSON.stringify(error.params?.additionalProperty)} を削除する`],
        required: [`必須プロパティ ${JSON.stringify(error.params?.missingProperty)} を追加する`],
        type: [`${annotated.path} で ${JSON.stringify(error.params?.type)} を使用する`],
        enum: [`${JSON.stringify(error.params?.allowedValues || [])} のいずれかを選択する`],
        pattern: [`必須パターン ${JSON.stringify(error.params?.pattern)} に一致させる`],
        minimum: [`${error.params?.comparison || '>='} ${error.params?.limit} を満たす値を使用する`],
        maximum: [`${error.params?.comparison || '<='} ${error.params?.limit} を満たす値を使用する`],
        minItems: [`少なくとも${error.params?.limit}項目を指定する`],
        maxItems: [`最大${error.params?.limit}項目を指定する`],
        minLength: [`少なくとも${error.params?.limit}文字を指定する`],
        maxLength: [`最大${error.params?.limit}文字を指定する`],
      }[error.keyword] || [];
      const detail = error.params && Object.keys(error.params).length
        ? ` ${JSON.stringify(error.params)}`
        : '';
      return {
        code: `schema/${error.keyword}`,
        severity: 'error',
        message: `${annotatePath(error.instancePath, data)} ${schemaErrorMessage(error)}${detail}`,
        subject,
        evidence,
        supportedFixes,
      };
    });
    throwDiagnosticError(
      `${diagramType}スキーマの検証に失敗しました:\n${formatErrors(validate.errors, data)}`,
      diagnostics,
    );
  }
}
