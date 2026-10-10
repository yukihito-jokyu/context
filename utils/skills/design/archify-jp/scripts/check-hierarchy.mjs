#!/usr/bin/env node
// 階層化した図（ノードの link で詳細図へ遷移する図の集合）の整合性チェックとマップ生成。
//
//   node scripts/check-hierarchy.mjs <root.json> [--scan dir] [--json] [--strict]
//   node scripts/check-hierarchy.mjs --sync <root.json> [--check] [--json]
//     パンくず（meta.hierarchy.trail）と子図の数（link.onward）をリンク構造から各仕様へ書き込む。
//     --check は書き込まずに、更新が必要な仕様があれば終了コード 1 を返す。
//   node scripts/check-hierarchy.mjs --map <root.json> <map.html> [--scan dir] [--json]
//     マップは architecture 図として <map>.architecture.json と <map>.html に出力する。
//
// 終了コード: 0 = エラーなし（--strict では警告もなし）、1 = 整合性エラー、2 = 使い方の誤り。

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkHierarchy, syncHierarchy } from '../renderers/shared/hierarchy-graph.mjs';
import { buildHierarchyMap } from '../renderers/shared/hierarchy-map.mjs';

function parseArgs(argv) {
  const options = { positional: [], json: false, strict: false, scan: null, map: false, sync: false, check: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') options.json = true;
    else if (arg === '--strict') options.strict = true;
    else if (arg === '--map') options.map = true;
    else if (arg === '--sync') options.sync = true;
    else if (arg === '--check') options.check = true;
    else if (arg === '--scan') {
      const value = argv[i + 1];
      if (value === undefined || value.startsWith('--')) throw new UsageError(`${arg} には値が必要です`);
      options[arg.slice(2)] = value;
      i += 1;
    } else if (arg.startsWith('--')) throw new UsageError(`不明なオプションです: ${arg}`);
    else options.positional.push(arg);
  }
  return options;
}

class UsageError extends Error {}

function receipt(command, result, extra = {}) {
  return {
    schemaVersion: 1,
    ok: result.ok,
    command,
    root: result.root ? path.relative(process.cwd(), result.root) : null,
    diagrams: result.diagrams.map((diagram) => ({
      title: diagram.title,
      type: diagram.type,
      spec: path.relative(process.cwd(), diagram.specPath),
      html: path.relative(process.cwd(), diagram.htmlPath),
      nodes: diagram.nodes.length,
      linked: diagram.nodes.filter((node) => node.link).length,
    })),
    summary: result.summary,
    diagnostics: result.diagnostics,
    ...extra,
  };
}

function printHuman(result) {
  console.log(`図 ${result.diagrams.length} 件 / エラー ${result.summary.errors} 件 / 警告 ${result.summary.warnings} 件`);
  for (const d of result.diagnostics) {
    console.log(`  ${d.severity === 'error' ? 'ERROR' : 'WARN '} [${d.code}] ${d.message}`);
  }
}

function exitCodeFor(result, strict) {
  if (result.summary.errors) return 1;
  if (strict && result.summary.warnings) return 1;
  return 0;
}

export function runHierarchyCheck(argv) {
  let options;
  try {
    options = parseArgs(argv);
  } catch (error) {
    console.error(error.message);
    return 2;
  }

  if (options.sync) {
    const [rootSpec] = options.positional;
    if (!rootSpec || options.positional.length > 1) {
      console.error('使用方法: --sync <root.json> [--check] [--json]');
      return 2;
    }
    const { result, changed } = syncHierarchy(rootSpec, { write: !options.check });
    const files = changed.map((file) => path.relative(process.cwd(), file));
    if (options.json) console.log(JSON.stringify({ schemaVersion: 1, ok: !(options.check && files.length), command: 'hierarchy-sync', check: options.check, changed: files, diagrams: result.diagrams.length }, null, 2));
    else {
      console.log(`${options.check ? '更新が必要な仕様' : '更新した仕様'}: ${files.length} 件 / 図 ${result.diagrams.length} 件`);
      for (const file of files) console.log(`  ${file}`);
      if (files.length && !options.check) console.log('更新した仕様は deliver で HTML を出し直してください。');
    }
    return options.check && files.length ? 1 : 0;
  }

  if (options.map) {
    const [rootSpec, outPath] = options.positional;
    if (!rootSpec || !outPath) {
      console.error('使用方法: --map <root.json> <map.html> [--scan dir] [--json]');
      return 2;
    }
    const { result, written, delivery, specPath } = buildHierarchyMap(rootSpec, outPath, { scanDir: options.scan });
    if (options.json) {
      console.log(JSON.stringify(receipt('map', result, {
        output: written ? path.relative(process.cwd(), outPath) : null,
        spec: specPath ? path.relative(process.cwd(), specPath) : null,
        delivery,
      }), null, 2));
    } else {
      if (written) console.log(path.resolve(outPath));
      else console.error(`マップ図の出力に失敗しました: ${JSON.stringify(delivery?.diagnostics || delivery?.error || delivery, null, 2)}`);
      printHuman(result);
    }
    return written ? exitCodeFor(result, options.strict) : 1;
  }

  const [rootSpec] = options.positional;
  if (!rootSpec || options.positional.length > 1) {
    console.error('使用方法: <root.json> [--scan dir] [--json] [--strict]');
    return 2;
  }
  const result = checkHierarchy(rootSpec, { scanDir: options.scan });
  if (options.json) console.log(JSON.stringify(receipt('hierarchy-check', result), null, 2));
  else printHuman(result);
  return exitCodeFor(result, options.strict);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = runHierarchyCheck(process.argv.slice(2));
}
