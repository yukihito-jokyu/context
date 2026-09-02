#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import standaloneCode from 'ajv/dist/standalone/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const schemasDir = path.join(root, 'schemas');
const output = path.join(root, 'renderers/shared/generated-validators.mjs');
const diagramTypes = ['workflow', 'sequence', 'dataflow', 'lifecycle', 'architecture', 'class', 'er'];

const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  code: { source: true, esm: true },
});
ajv.addSchema(JSON.parse(fs.readFileSync(path.join(schemasDir, 'common.schema.json'), 'utf8')));

const schemaIds = {};
for (const type of diagramTypes) {
  const schema = JSON.parse(fs.readFileSync(path.join(schemasDir, `${type}.schema.json`), 'utf8'));
  ajv.addSchema(schema);
  // `class` is a reserved binding name in JavaScript. AJV receives a safe
  // local binding and we re-export it under the diagram-type key below.
  schemaIds[type === 'class' ? 'classDiagram' : type] = schema.$id;
}

const banner = '// scripts/generate-validators.mjs により生成されました。手動で編集しないでください。\n';
const ajvUcs2Import = 'require("ajv/dist/runtime/ucs2length").default';
const inlineUcs2Length = `function ucs2length(str) {
  const len = str.length;
  let length = 0;
  let pos = 0;
  while (pos < len) {
    length += 1;
    const value = str.charCodeAt(pos++);
    if (value >= 0xd800 && value <= 0xdbff && pos < len
      && (str.charCodeAt(pos) & 0xfc00) === 0xdc00) pos += 1;
  }
  return length;
}`;
let validatorCode = standaloneCode(ajv, schemaIds);
if (!validatorCode.includes(ajvUcs2Import)) {
  throw new Error('AJVの単体出力に想定されるucs2lengthヘルパーが含まれていません');
}
validatorCode = validatorCode.replaceAll(ajvUcs2Import, inlineUcs2Length);
if (validatorCode.includes('require(')) {
  throw new Error('AJVの単体出力に想定外の実行時依存関係が含まれています');
}
const generated = `${banner}${validatorCode}\nexport { classDiagram as class };\n`;

if (process.argv.includes('--check')) {
  const current = fs.existsSync(output)
    ? fs.readFileSync(output, 'utf8').replace(/\r\n?/g, '\n')
    : '';
  if (current !== generated) {
    console.error('生成済みバリデーターが古くなっています — npm run generate:validators を実行してください');
    process.exit(1);
  }
} else {
  const temporary = `${output}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, generated);
  fs.renameSync(temporary, output);
  console.log(`${path.relative(root, output)} を生成しました`);
}
