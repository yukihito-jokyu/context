#!/usr/bin/env node
// 階層化した図の一式を、正しい順序で出力して検査する。
//
//   node scripts/build-hierarchy.mjs <root.json> [--scan dir] [--quality showcase|standard]
//     [--repo-root dir] [--strict] [--no-preview-check] [--no-visual-check] [--json]
//
// 手順:
//   1. hierarchy-sync（パンくず・同じ階層の図・参照元・子図の数を仕様へ書き込む）
//   2. 親の図から順に deliver（子の図は親の図の縮図を埋め込むため）
//   3. 横断リンクでつながる図をもう一度 deliver（互いの縮図を埋め込むため）
//   4. meta.hierarchy.map があればマップ図を生成
//   5. hierarchy-check（--scan の既定はルート仕様のディレクトリ）
//   6. 遷移先プレビューの見た目の検査（Chrome がなければスキップと報告）
//   7. 各図の visual-check（画面に収まるか。Chrome がなければスキップと報告）
//
// 終了コード: 0 = すべて合格（--strict では警告もなし）、1 = 失敗あり、2 = 使い方の誤り。

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkHierarchy, syncHierarchy, treeParents } from '../renderers/shared/hierarchy-graph.mjs';
import { buildHierarchyMap } from '../renderers/shared/hierarchy-map.mjs';
import { checkLinkPreviews } from './check-link-preview.mjs';

const cli = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../bin/archify.mjs');
// Paths under the working directory read relative; others stay absolute.
const rel = (file) => {
  const relative = path.relative(process.cwd(), file);
  return relative.startsWith('..') || path.isAbsolute(relative) ? path.resolve(file) : relative;
};

class UsageError extends Error {}

function parseArgs(argv) {
  const options = { positional: [], json: false, strict: false, scan: null, quality: 'showcase', repoRoot: null, preview: true, visual: true };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') options.json = true;
    else if (arg === '--strict') options.strict = true;
    else if (arg === '--no-preview-check') options.preview = false;
    else if (arg === '--no-visual-check') options.visual = false;
    else if (arg === '--scan' || arg === '--quality' || arg === '--repo-root') {
      const value = argv[i + 1];
      if (value === undefined || value.startsWith('--')) throw new UsageError(`${arg} には値が必要です`);
      if (arg === '--quality' && !['showcase', 'standard'].includes(value)) throw new UsageError('--quality は showcase か standard です');
      options[arg === '--repo-root' ? 'repoRoot' : arg.slice(2)] = value;
      i += 1;
    } else if (arg.startsWith('--')) throw new UsageError(`不明なオプションです: ${arg}`);
    else options.positional.push(arg);
  }
  if (options.positional.length !== 1) throw new UsageError('使用方法: archify hierarchy-build <root.json> [--scan dir] [--quality showcase|standard] [--repo-root dir] [--strict] [--no-preview-check] [--no-visual-check] [--json]');
  return options;
}

function deliver(diagram, options) {
  const args = [cli, 'deliver', diagram.type, diagram.specPath, diagram.htmlPath, '--quality', options.quality, '--json'];
  // deliver takes repository evidence for these types (architecture sources, SQL/DDL).
  if (options.repoRoot && ['architecture', 'sequence-er', 'workflow-er'].includes(diagram.type)) args.push('--repo-root', options.repoRoot);
  const run = spawnSync(process.execPath, args, { encoding: 'utf8' });
  let receipt = null;
  try {
    receipt = JSON.parse(run.stdout);
  } catch (_) {
    receipt = null;
  }
  const validation = receipt?.validation || {};
  return {
    spec: rel(diagram.specPath),
    html: rel(diagram.htmlPath),
    ok: run.status === 0 && receipt?.ok === true,
    checksPassed: validation.checksPassed ?? null,
    errors: validation.errors ?? null,
    warnings: validation.warnings ?? null,
    ...(run.status === 0 ? {} : { message: (receipt?.diagnostics?.[0]?.message || receipt?.error?.message || run.stderr || run.stdout || '').trim().split('\n')[0] }),
  };
}

// Parents before children: the tree depth from the root, then link order.
function deliveryOrder(result) {
  const parentOf = treeParents(result);
  const depth = (htmlPath, seen = new Set()) => {
    const parent = parentOf.get(htmlPath);
    if (!parent || seen.has(parent)) return 0;
    return 1 + depth(parent, new Set([...seen, htmlPath]));
  };
  return result.diagrams
    .map((diagram, index) => ({ diagram, index, depth: depth(diagram.htmlPath) }))
    .sort((a, b) => a.depth - b.depth || a.index - b.index)
    .map((entry) => entry.diagram);
}

export async function buildHierarchy(rootSpec, options) {
  const report = { schemaVersion: 1, command: 'hierarchy-build', root: rel(path.resolve(rootSpec)) };
  const { changed } = syncHierarchy(rootSpec);
  report.synced = changed.map(rel);

  const walked = checkHierarchy(rootSpec);
  if (!walked.diagrams.length) {
    report.ok = false;
    report.check = { summary: walked.summary, diagnostics: walked.diagnostics };
    return report;
  }
  report.delivered = deliveryOrder(walked).map((diagram) => deliver(diagram, options));

  // Cross-linked pages embed each other's thumbnails; a page delivered before
  // its peer existed (or changed) is stale until delivered again.
  report.redelivered = [];
  for (let round = 0; round < 2; round += 1) {
    const stale = new Set(checkHierarchy(rootSpec).diagnostics
      .filter((d) => d.code === 'hierarchy/stale-html').map((d) => d.subject.diagram));
    const again = deliveryOrder(walked).filter((diagram) => stale.has(path.relative(walked.rootDir, diagram.specPath).split(path.sep).join('/')));
    if (!again.length) break;
    report.redelivered.push(...again.map((diagram) => deliver(diagram, options)));
  }

  const root = walked.diagrams.find((diagram) => diagram.htmlPath === walked.root);
  const scanDir = options.scan || path.dirname(path.resolve(rootSpec));
  if (root.hierarchy?.map?.href) {
    const mapPath = path.resolve(path.dirname(root.htmlPath), root.hierarchy.map.href);
    const { written, delivery } = buildHierarchyMap(rootSpec, mapPath, { scanDir });
    report.map = { html: rel(mapPath), ok: written, ...(written ? {} : { message: JSON.stringify(delivery?.diagnostics?.[0]?.message || delivery?.error || null) }) };
  } else {
    report.map = null;
  }

  const result = checkHierarchy(rootSpec, { scanDir });
  report.check = { diagrams: result.diagrams.length, summary: result.summary, diagnostics: result.diagnostics };

  const deliveries = [...report.delivered, ...report.redelivered];
  // A page fixed by the second pass counts by its last delivery.
  const lastBySpec = new Map(deliveries.map((entry) => [entry.spec, entry]));
  // A failed delivery keeps the previous HTML; checking it would describe
  // an old page, so failed or missing pages are left out and named.
  const failed = new Set([...lastBySpec.values()].filter((entry) => !entry.ok).map((entry) => entry.html));
  const pages = result.diagrams.filter((diagram) => !failed.has(rel(diagram.htmlPath)) && fs.existsSync(diagram.htmlPath));
  const notChecked = result.diagrams.filter((diagram) => !pages.includes(diagram)).map((diagram) => rel(diagram.htmlPath));

  if (options.preview) {
    const previews = pages.length ? await checkLinkPreviews(pages.map((diagram) => diagram.htmlPath)) : [];
    report.preview = previews
      ? {
        status: 'checked',
        pages: previews.length,
        problems: previews.flatMap((page) => page.problems.map((problem) => ({ html: rel(page.file), theme: page.theme, ...problem }))),
        notChecked,
      }
      : { status: 'skipped', reason: 'Chrome/Chromium が見つかりません' };
  } else {
    report.preview = { status: 'skipped', reason: '--no-preview-check' };
  }

  // Every page (and the map) must fit the desktop viewports, as deliver's
  // own acceptance asks; exit 2 from visual-check means no Chrome.
  if (options.visual) {
    const targets = [...pages.map((diagram) => diagram.htmlPath), ...(report.map?.ok ? [path.resolve(report.map.html)] : [])];
    const results = targets.map((html) => {
      const run = spawnSync(process.execPath, [cli, 'visual-check', html, '--json'], { encoding: 'utf8' });
      let receipt = null;
      try { receipt = JSON.parse(run.stdout); } catch (_) { receipt = null; }
      return { html: rel(html), status: run.status, codes: [...new Set((receipt?.diagnostics || []).map((d) => d.code))] };
    });
    report.visual = results.some((entry) => entry.status === 2)
      ? { status: 'skipped', reason: 'Chrome/Chromium が見つかりません' }
      : { status: 'checked', pages: results.length, failed: results.filter((entry) => entry.status !== 0) };
  } else {
    report.visual = { status: 'skipped', reason: '--no-visual-check' };
  }

  report.ok = [...lastBySpec.values()].every((entry) => entry.ok)
    && (report.map === null || report.map.ok)
    && result.summary.errors === 0
    && (!options.strict || result.summary.warnings === 0)
    && (report.preview.status !== 'checked' || report.preview.problems.length === 0)
    && (report.visual.status !== 'checked' || report.visual.failed.length === 0);
  return report;
}

function printHuman(report) {
  console.log(`同期: 更新した仕様 ${report.synced.length} 件`);
  const line = (entry) => `  ${entry.ok ? 'OK' : 'NG'}  ${entry.html}${entry.ok ? `（チェック ${entry.checksPassed} / エラー ${entry.errors} / 警告 ${entry.warnings}）` : `  ${entry.message || ''}`}`;
  if (report.delivered) {
    console.log(`出力（親の図から順に）: ${report.delivered.length} 件`);
    report.delivered.forEach((entry) => console.log(line(entry)));
  }
  if (report.redelivered?.length) {
    console.log(`再出力（横断リンクの縮図をそろえる）: ${report.redelivered.length} 件`);
    report.redelivered.forEach((entry) => console.log(line(entry)));
  }
  if (report.map) console.log(`マップ: ${report.map.ok ? 'OK' : 'NG'}  ${report.map.html}${report.map.message ? `  ${report.map.message}` : ''}`);
  const { summary, diagnostics } = report.check;
  console.log(`整合性: 図 ${report.check.diagrams ?? 0} 件 / エラー ${summary.errors} 件 / 警告 ${summary.warnings} 件`);
  diagnostics.forEach((d) => console.log(`  ${d.severity === 'error' ? 'ERROR' : 'WARN '} [${d.code}] ${d.message}`));
  if (report.preview) {
    if (report.preview.status === 'checked') {
      console.log(`プレビュー: ${report.preview.pages} ページ / 問題 ${report.preview.problems.length} 件${report.preview.notChecked.length ? ` / 出力に失敗したため未検査 ${report.preview.notChecked.length} 図` : ''}`);
      report.preview.problems.forEach((p) => console.log(`  ${p.code}  ${p.html} (${p.theme}) ${p.node}${p.detail ? `  ${p.detail}` : ''}`));
    } else console.log(`プレビュー: スキップ（${report.preview.reason}）`);
  }
  if (report.visual) {
    if (report.visual.status === 'checked') {
      console.log(`画面サイズ（visual-check）: ${report.visual.pages} ページ / 不合格 ${report.visual.failed.length} 件`);
      report.visual.failed.forEach((entry) => console.log(`  NG  ${entry.html}  ${entry.codes.join(', ')}`));
    } else console.log(`画面サイズ（visual-check）: スキップ（${report.visual.reason}）`);
  }
  console.log(report.ok ? '結果: 合格' : '結果: 不合格');
}

export async function runHierarchyBuild(argv) {
  let options;
  try {
    options = parseArgs(argv);
  } catch (error) {
    console.error(error.message);
    return 2;
  }
  const report = await buildHierarchy(options.positional[0], options);
  if (options.json) console.log(JSON.stringify(report, null, 2));
  else printHuman(report);
  return report.ok ? 0 : 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await runHierarchyBuild(process.argv.slice(2));
}
