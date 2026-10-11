#!/usr/bin/env node
// 遷移先プレビュー（リンク付きノード・参照元のあるノードにホバーしたときのカード）の見た目の検査。
// 出力済み HTML をブラウザで開き、対象のノードすべてに順にホバーして確かめる。
//
//   node scripts/check-link-preview.mjs <html|dir>... [--json] [--theme light|dark|both]
//
// 検査項目:
//   viewer-error       ページの読み込み中にスクリプトの例外が出た（ビューアが動いていない）
//   viewer-missing     階層の図なのに遷移先プレビューの仕組みがない（ビューアが途中で止まった）
//   card-missing       リンクを持つノードなのにカードが出ない
//   card-translucent   カードの背景が透けて、背後の図の文字が読める
//   card-covers-node   カードがホバー中のノードに重なる
//   card-off-panel     カードが図のパネルからはみ出す
//   card-hides-tabs    カードが現在地タブ（パンくず・同じ階層の図）を隠す
//   tabs-under-toolbar 現在地タブが右上の固定ツールバーの下に入って隠れる（幅 1440・1024・800・600 で確認）
//   tabs-overlap       現在地タブ同士（パンくず・位置・同じ階層の図・マップ）が重なる
//   tabs-current-hidden 今の図のタブがタブ列やパネルの外に出て見えない
//   tabs-current-squeezed 今の図のタブが本来の幅より押し縮められ、題名が切れている
//   tabs-cover-diagram 現在地タブが図の中身（文字・ノード）に重なる
//   native-tooltip     カード表示中もブラウザ標準のツールチップ（<title>）が残っている
//   title-lost         カードを閉じた後に <title> が戻っていない
//   route-dangling     縮図の経路線の端が、この図・遷移先・経路上の囲みのどれにも着いていない
//   route-misses-target 経路線がこの図の側にしか着いておらず、遷移先に届いていない
//   route-count        「直接／N 本経由」の本数と強調した線の本数が合わない
//   dest-missing       遷移先の図の縮図が埋め込まれているのに、カードに出ない
//   dest-landing-missing 遷移先の縮図で、focus のノード（着くノード）が光っていない
//   incoming-badge-missing 参照元のあるノードに参照元バッジがない
//   incoming-missing   カードの参照元の行数が、このノードに着くリンクの数と合わない
//   incoming-source-missing 参照元の縮図で、リンク元のノードが光っていない
//
// 終了コード: 0 = 問題なし、1 = 問題あり、2 = 使い方の誤り／Chrome なし。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ChromeVisualBrowser, findChrome } from '../bin/visual-check.mjs';

// The location tabs against the toolbar and the drawing, at the current size.
const TABS_CHECK = `(function () {
  var problems = [];
  var nav = document.getElementById('archify-hierarchy');
  var svg = document.querySelector('.diagram-container svg');
  if (!nav || nav.hidden || !svg) return problems;
  var overlap = function (a, b) {
    return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  };
  var tabs = Array.prototype.filter.call(nav.querySelectorAll('a, button, span'), function (el) { var r = el.getBoundingClientRect(); return r.width && r.height; });
  var covered = {};
  Array.prototype.forEach.call(svg.querySelectorAll('text, [data-node-id]'), function (el) {
    var r = el.getBoundingClientRect();
    if (!r.width) return;
    if (tabs.some(function (t) { return overlap(r, t.getBoundingClientRect()); })) covered[(el.textContent || el.getAttribute('data-node-id') || '').trim().slice(0, 30)] = true;
  });
  Object.keys(covered).forEach(function (text) { problems.push({ node: '', code: 'tabs-cover-diagram', detail: text }); });
  // What the reader sees of each tab: a tab scrolled out of its row is clipped.
  var shown = function (el) {
    var r = el.getBoundingClientRect();
    var row = el.closest('.archify-hierarchy-tabs');
    if (!row || getComputedStyle(row).overflowX === 'visible') return r;
    var c = row.getBoundingClientRect();
    return { left: Math.max(r.left, c.left), right: Math.min(r.right, c.right), top: Math.max(r.top, c.top), bottom: Math.min(r.bottom, c.bottom) };
  };
  var items = Array.prototype.filter.call(nav.querySelectorAll('.archify-hierarchy-path, .archify-hierarchy-locate, .archify-hierarchy-sibling, .archify-hierarchy-map'), function (el) {
    var r = shown(el); return r.right - r.left > 1 && r.bottom - r.top > 1;
  });
  items.forEach(function (el, i) {
    items.slice(i + 1).forEach(function (other) {
      if (overlap(shown(el), shown(other))) problems.push({ node: '', code: 'tabs-overlap', detail: (el.textContent || '').trim().slice(0, 20) + ' / ' + (other.textContent || '').trim().slice(0, 20) });
    });
  });
  // This page's own tab must stay in view, inside its row and the panel,
  // with room for more than a sliver (a tab is at least 6.5rem wide).
  var current = nav.querySelector('.archify-hierarchy-sibling[aria-current]');
  var panelBox = (document.querySelector('.diagram-container') || svg).getBoundingClientRect();
  if (current) {
    var full = current.getBoundingClientRect();
    var seen = shown(current);
    var seenWidth = Math.min(seen.right, panelBox.right) - Math.max(seen.left, panelBox.left);
    if (seenWidth < Math.min(full.width, 96) - 1 || seen.bottom - seen.top < full.height - 1) {
      problems.push({ node: '', code: 'tabs-current-hidden', detail: (current.textContent || '').trim().slice(0, 30) });
    } else if (current.scrollWidth > current.clientWidth + 1 && full.width + 1 < parseFloat(getComputedStyle(current).maxWidth)) {
      problems.push({ node: '', code: 'tabs-current-squeezed', detail: (current.textContent || '').trim().slice(0, 30) });
    }
  }
  var toolbar = document.querySelector('.toolbar');
  var bar = toolbar ? toolbar.getBoundingClientRect() : null;
  if (bar && bar.width) {
    tabs.forEach(function (tab) {
      if (overlap(shown(tab), bar)) problems.push({ node: '', code: 'tabs-under-toolbar', detail: (tab.textContent || '').trim().slice(0, 30) });
    });
  }
  return problems;
})()`;

// Runs inside the page: hovers every node that the viewer would describe with
// a link preview and reports what looks wrong.
const PAGE_CHECK = `(async function () {
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var svg = document.querySelector('.diagram-container svg');
  var card = document.getElementById('archify-link-preview');
  var hierarchy = null;
  try { hierarchy = JSON.parse(document.getElementById('archify-hierarchy-data').textContent); } catch (_) { hierarchy = null; }
  if (!svg || !card) {
    // A hierarchy page always gets the preview; without it the viewer stopped.
    var expected = hierarchy && hierarchy.role !== 'map' && svg && svg.querySelector('[data-node-link-href]');
    return { nodes: 0, problems: expected ? [{ node: '', code: 'viewer-missing', detail: '#archify-link-preview がありません' }] : [] };
  }
  var container = card.parentElement;
  var problems = [];
  var report = function (node, code, detail) { problems.push({ node: node, code: code, detail: detail || '' }); };
  var frames = Array.prototype.filter.call(svg.querySelectorAll('rect[data-boundary-id][data-node-link-href]'), function () { return true; });
  var inside = function (outer, inner) {
    return inner.x >= outer.x && inner.y >= outer.y && inner.x + inner.width <= outer.x + outer.width && inner.y + inner.height <= outer.y + outer.height;
  };
  var data = {};
  try { data = JSON.parse(document.getElementById('archify-hierarchy-data').textContent) || {}; } catch (_) { data = {}; }
  var pathOf = function (href) { return new URL(href, location.href).pathname; };
  var peerPaths = Object.keys(data.peers || {}).map(pathOf);
  var arriving = function (id) { return (data.incoming || []).filter(function (entry) { return entry.focus === id; }); };
  var nav = document.getElementById('archify-hierarchy');
  var linked = Array.prototype.filter.call(svg.querySelectorAll('[data-node-id]'), function (node) {
    if (node.hasAttribute('data-node-link-href')) return true;
    if (arriving(node.getAttribute('data-node-id')).length) return true;
    var box = node.getBBox();
    return frames.some(function (frame) { return inside(frame.getBBox(), box); });
  });
  var alpha = function (color) {
    var m = color.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return color === 'transparent' ? 0 : 1;
    var parts = m[1].split(/[\\s,\\/]+/).filter(Boolean);
    return parts.length > 3 ? Number(parts[3]) : 1;
  };
  var overlap = function (a, b) {
    return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  };
  // The node's own title: on the node, or in the group that draws its box
  // (ER/class); a badge inside the node keeps its own.
  var hasTitle = function (node) {
    var box = node.querySelector('rect');
    return Array.prototype.some.call(node.querySelectorAll('title'), function (title) {
      return title.parentNode === node || (box && title.parentNode.contains(box));
    });
  };
  for (var i = 0; i < linked.length; i += 1) {
    var node = linked[i];
    var id = node.getAttribute('data-node-id');
    var titled = hasTitle(node);
    node.scrollIntoView({ block: 'center', inline: 'center' });
    node.dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' }));
    await wait(260);
    if (card.hidden) { report(id, 'card-missing'); continue; }
    var style = getComputedStyle(card);
    if (alpha(style.backgroundColor) < 1) report(id, 'card-translucent', style.backgroundColor);
    var cardBox = card.getBoundingClientRect();
    var nodeBox = node.getBoundingClientRect();
    var panelBox = container.getBoundingClientRect();
    if (overlap(cardBox, nodeBox)) report(id, 'card-covers-node');
    if (cardBox.left < panelBox.left - 1 || cardBox.right > panelBox.right + 1 || cardBox.top < panelBox.top - 1 || cardBox.bottom > panelBox.bottom + 1) {
      report(id, 'card-off-panel');
    }
    if (nav && !nav.hidden) {
      Array.prototype.forEach.call(nav.querySelectorAll('a, button'), function (tab) {
        var r = tab.getBoundingClientRect();
        if (r.width && overlap(cardBox, r)) report(id, 'card-hides-tabs', (tab.textContent || '').trim().slice(0, 30));
      });
    }
    if (hasTitle(node)) report(id, 'native-tooltip');

    var href = node.getAttribute('data-node-link-href');
    if (href && peerPaths.indexOf(pathOf(href)) >= 0) {
      var dest = card.querySelector('svg.archify-link-preview-dest');
      var focus = node.getAttribute('data-node-link-focus');
      if (!dest) report(id, 'dest-missing');
      else if (focus && !dest.querySelector('[data-state="lands"][data-node="' + CSS.escape(focus) + '"]')) report(id, 'dest-landing-missing', focus);
    }
    var expected = arriving(id);
    if (expected.length) {
      if (node.getAttribute('data-incoming') !== String(expected.length)) report(id, 'incoming-badge-missing');
      var rows = card.querySelectorAll('.archify-link-preview-from');
      if (rows.length !== expected.length) report(id, 'incoming-missing', 'rows ' + rows.length + ' / links ' + expected.length);
      expected.forEach(function (entry, k) {
        if (peerPaths.indexOf(pathOf(entry.href)) < 0 || !rows[k]) return;
        if (!rows[k].querySelector('[data-state="source"][data-node="' + CSS.escape(entry.node) + '"]')) report(id, 'incoming-source-missing', entry.href + '#' + entry.node);
      });
    }

    var caption = card.querySelector('.archify-link-preview-route');
    var thumb = card.querySelector('svg.archify-link-preview-locator');
    if (caption && thumb) {
      var lines = Array.prototype.slice.call(thumb.querySelectorAll('.archify-locator-edge[data-route]'));
      var hops = caption.hasAttribute('data-hops') ? Number(caption.getAttribute('data-hops')) : 0;
      if (lines.length !== hops) report(id, 'route-count', 'caption ' + hops + ' / lines ' + lines.length);
      var vb = thumb.viewBox.baseVal;
      var tol = Math.max(6, vb.width / 160);
      var boxes = Array.prototype.map.call(thumb.querySelectorAll('rect'), function (r) {
        return {
          x: r.x.baseVal.value, y: r.y.baseVal.value, w: r.width.baseVal.value, h: r.height.baseVal.value,
          state: r.getAttribute('data-state'), route: r.hasAttribute('data-route'), group: r.classList.contains('archify-locator-group')
        };
      });
      var near = function (p, b) { return p[0] >= b.x - tol && p[0] <= b.x + b.w + tol && p[1] >= b.y - tol && p[1] <= b.y + b.h + tol; };
      var within = function (outer, inner) { return inner.x >= outer.x && inner.y >= outer.y && inner.x + inner.w <= outer.x + outer.w && inner.y + inner.h <= outer.y + outer.h; };
      var targets = boxes.filter(function (b) { return b.state === 'target'; });
      // A lit frame counts as the target side when the target sits inside it.
      var targetSide = function (b) { return b.state === 'target' || (b.group && b.route && targets.some(function (t) { return t !== b && within(b, t); })); };
      var ends = [];
      lines.forEach(function (line) {
        var pts = Array.prototype.map.call(line.points, function (p) { return [p.x, p.y]; });
        if (pts.length) ends.push(pts[0], pts[pts.length - 1]);
      });
      // Joints where two route lines meet are not ends of the route.
      var terminals = ends.filter(function (p, k) {
        return !ends.some(function (q, j) { return j !== k && Math.abs(p[0] - q[0]) <= tol && Math.abs(p[1] - q[1]) <= tol; });
      });
      var touchesTarget = false;
      terminals.forEach(function (p) {
        // The smallest box under the end is what the reader sees it touch.
        var under = boxes.filter(function (b) { return near(p, b); }).sort(function (a, b) { return a.w * a.h - b.w * b.h; });
        var lit = under.filter(function (b) { return b.state || b.route; });
        if (!lit.length) { report(id, 'route-dangling', 'end ' + p.map(Math.round).join(',')); return; }
        if (under[0] && !under[0].state && !under[0].route && !under[0].group) {
          report(id, 'route-dangling', 'end ' + p.map(Math.round).join(',') + ' on an unlit node');
          return;
        }
        if (lit.some(targetSide)) touchesTarget = true;
      });
      if (lines.length && !touchesTarget) report(id, 'route-misses-target');
    }
    node.dispatchEvent(new PointerEvent('pointerout', { bubbles: true, pointerType: 'mouse' }));
    await wait(30);
    if (titled && !hasTitle(node)) report(id, 'title-lost');
  }
  // Checked last, after the viewer has settled its layout.
  problems = problems.concat(${TABS_CHECK});
  return { nodes: linked.length, problems: problems };
})()`;

// Narrower desktops, where the toolbar takes most of the top row, and the
// mobile layout (720px and below).
const NARROW_WIDTHS = [1024, 800, 600];

export async function checkLinkPreviewPage(browser, sessionId) {
  const response = await browser.cdp.send('Runtime.evaluate', {
    expression: PAGE_CHECK, awaitPromise: true, returnByValue: true,
  }, sessionId);
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  }
  return response.result.value;
}

// HTML files under the inputs, skipping visual-check sheets and deliver's
// staging folders (`.archify-*`). Walked by hand for Node 18.0–18.16.
function collect(inputs) {
  const files = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name.startsWith('.archify-') || entry.name === 'node_modules') continue;
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (entry.name.endsWith('.html') && !entry.name.endsWith('.visual-check.html')) files.push(path.resolve(file));
    }
  };
  for (const input of inputs) {
    if (!fs.existsSync(input)) throw new Error(`見つかりません: ${input}`);
    if (fs.statSync(input).isFile()) files.push(path.resolve(input));
    else walk(input);
  }
  return [...new Set(files)].sort();
}

export async function checkLinkPreviews(files, { themes = ['light', 'dark'] } = {}) {
  const chrome = findChrome();
  if (!chrome) return null;
  const browser = new ChromeVisualBrowser(chrome);
  const results = [];
  try {
    const sessionId = await browser.sessionPromise;
    await browser.cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
    await browser.cdp.send('Runtime.enable', {}, sessionId);
    for (const file of files) {
      for (const theme of themes) {
        const url = pathToFileURL(file);
        url.searchParams.set('theme', theme);
        // An exception while loading means the viewer is not running at all.
        const thrown = browser.cdp.waitFor('Runtime.exceptionThrown', sessionId, 1000).catch(() => null);
        const loaded = browser.cdp.waitFor('Page.loadEventFired', sessionId);
        await browser.cdp.send('Page.navigate', { url: url.href }, sessionId);
        await loaded;
        const exception = await thrown;
        const page = await checkLinkPreviewPage(browser, sessionId);
        const problems = exception
          ? [{ node: '', code: 'viewer-error', detail: String(exception.exceptionDetails?.exception?.description || exception.exceptionDetails?.text || '').split('\n')[0] }, ...page.problems]
          : page.problems;
        // Narrower desktops leave less room beside the toolbar; layout does
        // not depend on the theme, so once per page is enough.
        if (theme === themes[0]) {
          for (const width of NARROW_WIDTHS) {
            await browser.cdp.send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
            const narrow = await browser.cdp.send('Runtime.evaluate', {
              expression: `new Promise(function (done) { window.dispatchEvent(new Event('resize')); setTimeout(function () { done(${TABS_CHECK}); }, 400); })`,
              awaitPromise: true, returnByValue: true,
            }, sessionId);
            for (const p of narrow.result?.value || []) problems.push({ ...p, detail: `${p.detail} @${width}px` });
          }
          // A layout pass while scrolled down must not lose the toolbar clearance.
          await browser.cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 600, deviceScaleFactor: 1, mobile: false }, sessionId);
          const scrolled = await browser.cdp.send('Runtime.evaluate', {
            expression: `new Promise(function (done) {
              window.scrollTo(0, document.documentElement.scrollHeight);
              window.dispatchEvent(new Event('resize'));
              setTimeout(function () { window.scrollTo(0, 0); setTimeout(function () { done(${TABS_CHECK}); }, 200); }, 400);
            })`,
            awaitPromise: true, returnByValue: true,
          }, sessionId);
          for (const p of scrolled.result?.value || []) problems.push({ ...p, detail: `${p.detail} @1280x600 scrolled` });
          await browser.cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
        }
        results.push({ file, theme, nodes: page.nodes, problems });
      }
    }
  } finally {
    await browser.close();
  }
  return results;
}

async function main(argv) {
  const json = argv.includes('--json');
  const themeAt = argv.indexOf('--theme');
  const theme = themeAt >= 0 ? argv[themeAt + 1] : 'both';
  const inputs = argv.filter((arg, i) => !arg.startsWith('--') && (themeAt < 0 || i !== themeAt + 1));
  if (!inputs.length || !['light', 'dark', 'both'].includes(theme)) {
    process.stderr.write('使い方: node scripts/check-link-preview.mjs <html|dir>... [--json] [--theme light|dark|both]\n');
    return 2;
  }
  let files;
  try {
    files = collect(inputs);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    return 2;
  }
  const results = await checkLinkPreviews(files, { themes: theme === 'both' ? ['light', 'dark'] : [theme] });
  if (!results) {
    process.stderr.write('Chrome/Chromium が見つからないため検査できません\n');
    return 2;
  }
  const problems = results.flatMap((r) => r.problems.map((p) => ({ file: r.file, theme: r.theme, ...p })));
  if (json) process.stdout.write(`${JSON.stringify({ ok: !problems.length, pages: results.length, problems }, null, 2)}\n`);
  else {
    for (const r of results) {
      process.stdout.write(`${r.problems.length ? 'NG' : 'OK'}  ${path.relative(process.cwd(), r.file)} (${r.theme}) リンク ${r.nodes}\n`);
      for (const p of r.problems) process.stdout.write(`    ${p.code}  ${p.node}${p.detail ? `  ${p.detail}` : ''}\n`);
    }
    process.stdout.write(`\n${results.length} ページ / 問題 ${problems.length} 件\n`);
  }
  return problems.length ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main(process.argv.slice(2));
}
