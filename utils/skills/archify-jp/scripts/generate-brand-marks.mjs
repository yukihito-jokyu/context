#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as simpleIcons from 'simple-icons';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const catalogPath = path.join(root, 'brand-marks', 'catalog.json');
const outputPath = path.join(root, 'renderers', 'shared', 'generated-brand-marks.mjs');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
const simpleIconsVersion = JSON.parse(fs.readFileSync(
  path.join(root, 'node_modules', 'simple-icons', 'package.json'),
  'utf8',
)).version;
const simpleBySlug = new Map(Object.values(simpleIcons)
  .filter((icon) => icon && typeof icon === 'object' && icon.slug && icon.path)
  .map((icon) => [icon.slug, icon]));

function normalizedList(value) {
  return [...new Set((Array.isArray(value) ? value : [])
    .map((item) => String(item).trim())
    .filter(Boolean))];
}

function lookupForms(value) {
  const raw = String(value ?? '').trim().toLocaleLowerCase('en-US');
  if (!raw) return [];
  return [...new Set([
    raw,
    raw.replace(/[\s_]+/g, '-'),
    raw.replace(/[\s_.-]+/g, ''),
  ])];
}

function fail(message) {
  console.error(`ブランドカタログ: ${message}`);
  process.exit(1);
}

if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.marks) || catalog.marks.length === 0) {
  fail('catalog.jsonには空でないschemaVersion 1のmarks配列が必要です');
}

const ids = new Set();
const lookupKeys = new Map();
const domains = new Map();
const generated = catalog.marks.map((entry, index) => {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(entry.id || '')) fail(`marks[${index}]のidが無効です`);
  if (ids.has(entry.id)) fail(`id ${entry.id} が重複しています`);
  ids.add(entry.id);

  const aliases = normalizedList(entry.aliases);
  const entryDomains = normalizedList(entry.domains).map((domain) => domain.toLowerCase());
  for (const key of [entry.id, ...aliases]) {
    for (const form of lookupForms(key)) {
      if (lookupKeys.has(form) && lookupKeys.get(form) !== entry.id) {
        fail(`検索キー ${JSON.stringify(key)} が ${lookupKeys.get(form)} と ${entry.id} で共有されています`);
      }
      lookupKeys.set(form, entry.id);
    }
  }
  for (const domain of entryDomains) {
    if (domains.has(domain) && domains.get(domain) !== entry.id) {
      fail(`ドメイン ${domain} が ${domains.get(domain)} と ${entry.id} で共有されています`);
    }
    domains.set(domain, entry.id);
  }

  let mark;
  if (entry.simpleIcon) {
    const icon = simpleBySlug.get(entry.simpleIcon);
    if (!icon) fail(`${entry.id} が存在しないSimple Iconsスラッグ ${entry.simpleIcon} を参照しています`);
    mark = {
      id: entry.id,
      title: entry.title || icon.title,
      category: entry.category,
      aliases,
      domains: entryDomains,
      viewBox: 24,
      hex: icon.hex,
      path: icon.path,
      provenance: {
        provider: 'Simple Icons',
        providerVersion: simpleIconsVersion,
        source: icon.source,
        ...(icon.guidelines ? { guidelines: icon.guidelines } : {}),
        ...(icon.license ? { license: icon.license } : {}),
      },
    };
  } else if (entry.custom) {
    const custom = entry.custom;
    if (!entry.title || !custom.path || !custom.source || !/^[0-9A-F]{6}$/i.test(custom.hex || '')) {
      fail(`${entry.id} のカスタムマークにはtitle、path、source、6桁のhexが必要です`);
    }
    mark = {
      id: entry.id,
      title: entry.title,
      category: entry.category,
      aliases,
      domains: entryDomains,
      viewBox: custom.viewBox || 24,
      hex: custom.hex.toUpperCase(),
      path: custom.path,
      provenance: {
        provider: 'Official brand asset',
        source: custom.source,
        ...(custom.guidelines ? { guidelines: custom.guidelines } : {}),
      },
    };
  } else {
    fail(`${entry.id} にはsimpleIconまたはcustomが必要です`);
  }
  if (!mark.category || !mark.title) fail(`${entry.id} にcategoryまたはtitleがありません`);
  for (const form of lookupForms(mark.title)) {
    if (lookupKeys.has(form) && lookupKeys.get(form) !== entry.id) {
      fail(`title ${JSON.stringify(mark.title)} が ${lookupKeys.get(form)} と ${entry.id} で共有されています`);
    }
    lookupKeys.set(form, entry.id);
  }
  return mark;
}).sort((left, right) => left.id.localeCompare(right.id));

const banner = `// brand-marks/catalog.jsonからscripts/generate-brand-marks.mjsにより生成されました。\n// Simple Icons ${simpleIconsVersion}。手動で編集しないでください。\n`;
const source = `${banner}export const BRAND_MARKS = Object.freeze(${JSON.stringify(generated, null, 2)});\n`;

if (process.argv.includes('--check')) {
  const current = fs.existsSync(outputPath)
    ? fs.readFileSync(outputPath, 'utf8').replace(/\r\n?/g, '\n')
    : '';
  if (current !== source) {
    console.error('生成済みブランドマークが古くなっています — npm run generate:brand-marks を実行してください');
    process.exit(1);
  }
} else {
  const temporary = `${outputPath}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, source);
  fs.renameSync(temporary, outputPath);
  console.log(`${path.relative(root, outputPath)} を生成しました（${generated.length}件のマーク）`);
}
