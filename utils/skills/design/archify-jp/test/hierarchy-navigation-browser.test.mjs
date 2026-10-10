import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ChromeVisualBrowser, findChrome } from '../bin/visual-check.mjs';
import { checkLinkPreviewPage } from '../scripts/check-link-preview.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(here, '..');
const chromePath = process.env.ARCHIFY_CHROME ? findChrome() : null;

async function evaluate(browser, sessionId, expression, awaitPromise = false) {
  const response = await browser.cdp.send('Runtime.evaluate', {
    expression, awaitPromise, returnByValue: true,
  }, sessionId);
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || 'Runtime.evaluate failed');
  return response.result?.value;
}

async function load(browser, artifact) {
  const sessionId = await browser.sessionPromise;
  await browser.cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  }, sessionId);
  const loaded = browser.cdp.waitFor('Page.loadEventFired', sessionId);
  await browser.cdp.send('Page.navigate', { url: pathToFileURL(artifact).href }, sessionId);
  await loaded;
  return sessionId;
}

function renderFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-nav-'));
  const diagram = JSON.parse(fs.readFileSync(path.join(skillRoot, 'examples/web-app.architecture.json'), 'utf8'));
  delete diagram.meta.output;
  diagram.components.find((c) => c.id === 'api').link = { href: 'detail/api.html', focus: 'handler', label: 'API の詳細' };
  diagram.components.find((c) => c.id === 'api').link.onward = 2;
  diagram.meta.hierarchy = {
    parent: { href: '../index.html', label: '全体図' },
    map: { href: 'map.html' },
    trail: [{ href: '../index.html', label: '全体図' }, { href: 'map.html', label: 'apps', focus: 'c-apps' }],
  };
  const input = path.join(dir, 'root.architecture.json');
  const output = path.join(dir, 'root.html');
  fs.writeFileSync(input, JSON.stringify(diagram));
  execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'render', 'architecture', input, output]);
  fs.mkdirSync(path.join(dir, 'detail'));
  fs.writeFileSync(path.join(dir, 'detail/api.html'), '<!doctype html><title>detail</title>');
  return output;
}

test('linked nodes offer drill-down from the passport, double-click and header links', {
  skip: chromePath ? false : 'Set ARCHIFY_CHROME to run the hierarchy navigation browser test.',
}, async () => {
  const artifact = renderFixture();
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    let sessionId = await load(browser, artifact);
    const before = await evaluate(browser, sessionId, `(function () {
      var api = document.querySelector('[data-node-id="api"]');
      var users = document.querySelector('[data-node-id="users"]');
      var nav = document.getElementById('archify-hierarchy');
      var crumbs = Array.prototype.map.call(nav.querySelectorAll('.archify-hierarchy-crumb'), function (a) {
        return [a.textContent, a.getAttribute('href')];
      });
      return {
        drilldown: api.getAttribute('data-drilldown'),
        badge: !!api.querySelector('[data-drilldown-overlay]'),
        onward: api.querySelector('.drilldown-count-text') ? api.querySelector('.drilldown-count-text').textContent : null,
        plainBadge: !!users.querySelector('[data-drilldown-overlay]'),
        navHidden: nav.hidden,
        level: nav.querySelector('.archify-hierarchy-level').textContent,
        crumbs: crumbs,
        here: nav.querySelector('.archify-hierarchy-here').textContent,
        map: nav.querySelector('.archify-hierarchy-map').getAttribute('href')
      };
    })()`);
    assert.equal(before.drilldown, 'true');
    assert.equal(before.badge, true);
    assert.equal(before.plainBadge, false);
    assert.equal(before.onward, '2');
    assert.equal(before.navHidden, false);
    assert.equal(before.level, 'L2');
    assert.deepEqual(before.crumbs, [['全体図', '../index.html'], ['apps', 'map.html#focus=c-apps']]);
    assert.equal(before.here, 'Webアプリのサンプル');
    assert.equal(before.map, 'map.html#here=root.html');

    const passport = await evaluate(browser, sessionId, `(function () {
      var node = document.querySelector('[data-node-id="api"]');
      node.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      return new Promise(function (resolve) {
        setTimeout(function () {
          var link = document.getElementById('focus-drilldown');
          var first = { hidden: link.hidden, href: link.getAttribute('href'), text: link.textContent };
          document.querySelector('[data-node-id="users"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
          setTimeout(function () {
            resolve({ api: first, usersHidden: document.getElementById('focus-drilldown').hidden });
          }, 300);
        }, 300);
      });
    })()`, true);
    assert.equal(passport.api.hidden, false, JSON.stringify(passport));
    assert.equal(passport.api.href, 'detail/api.html#focus=handler');
    assert.match(passport.api.text, /API の詳細/);
    assert.equal(passport.usersHidden, true, 'a node without a link must not offer drill-down');

    const exported = await evaluate(browser, sessionId, `(function () {
      return new Promise(function (resolve) {
        var original = URL.createObjectURL;
        URL.createObjectURL = function (blob) {
          URL.createObjectURL = original;
          blob.text().then(resolve);
          return 'blob:archify-test';
        };
        Archify.exportMenu.run('svg');
      });
    })()`, true);
    assert.doesNotMatch(exported, /data-drilldown-overlay/);
    assert.match(exported, /data-node-link-href="detail\/api\.html"/);

    // Hovering a linked node names where it goes and how it relates.
    const preview = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      var node = document.querySelector('[data-node-id="api"]');
      node.dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' }));
      setTimeout(function () {
        var card = document.getElementById('archify-link-preview');
        resolve({
          shown: !card.hidden,
          relation: card.querySelector('.archify-link-preview-rel').textContent,
          title: card.querySelector('.archify-link-preview-title').textContent
        });
        node.dispatchEvent(new PointerEvent('pointerout', { bubbles: true, pointerType: 'mouse' }));
      }, 350);
    })`, true);
    assert.deepEqual(preview, { shown: true, relation: '下の階層', title: 'API の詳細' });

    // Drilling down zooms into the node before the page changes.
    const navigated = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    const zoomed = await evaluate(browser, sessionId, `(function () {
      document.querySelector('[data-node-id="api"]').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
      return !!document.querySelector('.zoom-portal');
    })()`);
    assert.equal(zoomed, true);
    await navigated;
    const location = await evaluate(browser, sessionId, 'location.pathname + location.hash');
    assert.match(location, /\/detail\/api\.html#focus=handler$/);

    // A sideways link (outside this page's directory) changes page at once.
    sessionId = await load(browser, artifact);
    const sideways = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    const instant = await evaluate(browser, sessionId, `(function () {
      var node = document.querySelector('[data-node-id="api"]');
      var dir = location.pathname.split('/').slice(-2, -1)[0];
      node.setAttribute('data-node-link-href', '../' + dir + '/detail/api.html');
      node.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
      return !document.querySelector('.zoom-portal');
    })()`);
    assert.equal(instant, true);
    await sideways;

    sessionId = await load(browser, artifact);
    const keyboard = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    await evaluate(browser, sessionId, `(function () {
      var node = document.querySelector('[data-node-id="api"]');
      node.focus();
      node.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true }));
    })()`);
    await keyboard;
    assert.match(await evaluate(browser, sessionId, 'location.pathname'), /\/detail\/api\.html$/);
  } finally {
    await browser.close();
  }
});

function renderMapFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-stack-'));
  const cli = path.join(skillRoot, 'bin/archify.mjs');
  const arch = (title, components, hierarchy) => ({
    schema_version: 1,
    diagram_type: 'architecture',
    meta: { title, hierarchy },
    components: components.map((c, i) => ({ type: 'backend', pos: [40 + i * 240, 80], size: [160, 64], ...c })),
    connections: [],
  });
  const leaves = [['apps/web/web', 'Web'], ['apps/api/api', 'API'], ['data/db/db', 'DB']];
  const write = (file, value) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value)); };
  write(path.join(dir, 'root.architecture.json'), arch('全体', leaves.map(([href, label], i) => ({ id: `n${i}`, label, link: { href: `${href}.html` } })), { map: { href: 'map.html' } }));
  for (const [href, label] of leaves) {
    write(path.join(dir, `${href}.architecture.json`), arch(label, [{ id: 'x', label: 'X' }], { parent: { href: '../../root.html', label: '全体' }, map: { href: '../../map.html' } }));
  }
  execFileSync(process.execPath, [cli, 'hierarchy-sync', path.join(dir, 'root.architecture.json')]);
  for (const file of ['root', ...leaves.map(([href]) => href)]) {
    execFileSync(process.execPath, [cli, 'render', 'architecture', path.join(dir, `${file}.architecture.json`), path.join(dir, `${file}.html`)]);
  }
  execFileSync(process.execPath, [cli, 'map', path.join(dir, 'root.architecture.json'), path.join(dir, 'map.html')]);
  return dir;
}

test('a map diagram opens as stacked hierarchy layers and lights up where the reader came from', {
  skip: chromePath ? false : 'Set ARCHIFY_CHROME to run the hierarchy navigation browser test.',
}, async () => {
  const dir = renderMapFixture();
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    const sessionId = await browser.sessionPromise;
    await browser.cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
    const loaded = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    await browser.cdp.send('Page.navigate', { url: pathToFileURL(path.join(dir, 'map.html')).href + '#here=apps/api/api.html' }, sessionId);
    await loaded;
    const stack = await evaluate(browser, sessionId, `new Promise(function (resolve) { requestAnimationFrame(function () { requestAnimationFrame(function () {
      var container = document.querySelector('.diagram-container');
      var planes = Array.prototype.map.call(document.querySelectorAll('.hier-plane-label'), function (p) { return p.textContent; });
      var cards = Array.prototype.map.call(document.querySelectorAll('.hier-card'), function (c) { return c.querySelector('strong').textContent; });
      var here = document.querySelector('.hier-card[data-hier-here="true"] strong');
      var onPath = Array.prototype.map.call(document.querySelectorAll('.hier-card[data-hier-state]'), function (c) { return c.querySelector('strong').textContent; });
      resolve({
        view: container.getAttribute('data-hier-view'),
        svgHidden: getComputedStyle(container.querySelector('svg')).visibility,
        planes: planes,
        cards: cards,
        lines: document.querySelectorAll('.hier-lines path').length,
        litLines: document.querySelectorAll('.hier-lines path[data-on="true"]').length,
        here: here ? here.textContent : null,
        onPath: onPath.sort(),
        fits: document.documentElement.scrollHeight <= window.innerHeight
      });
    }); }); })`, true);
    assert.equal(stack.view, 'stack');
    assert.equal(stack.svgHidden, 'hidden');
    assert.deepEqual(stack.planes, ['L0 全体図', 'L1 関心ごと', 'L2 詳細図']);
    assert.deepEqual(stack.cards.sort(), ['API', 'DB', 'Web', 'apps', 'data', '全体'].sort());
    assert.equal(stack.lines, 5);
    assert.equal(stack.here, 'API');
    assert.deepEqual(stack.onPath, ['API', 'apps', '全体'].sort());
    assert.equal(stack.litLines, 2);
    assert.equal(stack.fits, true);

    // Hovering a card runs the flat hover trace and mirrors its emphasis.
    const hovered = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      var card = Array.prototype.find.call(document.querySelectorAll('.hier-card'), function (c) { return c.querySelector('strong').textContent === 'apps'; });
      var svg = document.querySelector('.diagram-container > svg');
      card.dispatchEvent(new MouseEvent('mouseenter'));
      setTimeout(function () {
        var dimmed = Array.prototype.filter.call(document.querySelectorAll('.hier-card'), function (c) { return Number(c.style.opacity) < 0.5; })
          .map(function (c) { return c.querySelector('strong').textContent; }).sort();
        var trace = svg.hasAttribute('data-intent-trace-active');
        var dirs = Array.prototype.map.call(document.querySelectorAll('.hier-lines .intent-trace-flow[data-direction]'), function (p) { return p.getAttribute('data-direction'); }).sort();
        card.dispatchEvent(new MouseEvent('mouseleave'));
        setTimeout(function () {
          resolve({ trace: trace, dimmed: dimmed, dirs: dirs, cleared: !svg.hasAttribute('data-intent-trace-active') && !card.style.opacity });
        }, 400);
      }, 400);
    })`, true);
    assert.deepEqual(hovered, { trace: true, dimmed: ['DB', 'data'], dirs: ['in', 'out', 'out'], cleared: true });

    // A card click behaves like a flat node click: it focuses the node and
    // opens the passport, and the stack follows passport focus changes.
    const clicked = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      var card = Array.prototype.find.call(document.querySelectorAll('.hier-card'), function (c) { return c.querySelector('strong').textContent === 'DB'; });
      card.click();
      setTimeout(function () {
        var drill = document.getElementById('focus-drilldown');
        var self = document.querySelector('.hier-card[data-hier-state="selected"] strong');
        resolve({ focus: document.getElementById('focus-id').textContent.trim() === card.getAttribute('data-hier-id'), drill: !drill.hidden, self: self ? self.textContent : null });
      }, 400);
    })`, true);
    assert.deepEqual(clicked, { focus: true, drill: true, self: 'DB' });

    const flat = await evaluate(browser, sessionId, `(function () {
      document.querySelector('.hier-tools button[aria-pressed="false"]').click();
      var container = document.querySelector('.diagram-container');
      return { view: container.getAttribute('data-hier-view'), svg: getComputedStyle(container.querySelector('svg')).visibility };
    })()`);
    assert.deepEqual(flat, { view: 'flat', svg: 'visible' });

    await evaluate(browser, sessionId, `document.querySelector('.hier-tools button').click()`);
    const navigated = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    await evaluate(browser, sessionId, `(function () {
      var card = Array.prototype.find.call(document.querySelectorAll('.hier-card'), function (c) { return c.querySelector('strong').textContent === 'DB'; });
      card.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
    })()`);
    await navigated;
    assert.match(await evaluate(browser, sessionId, 'location.pathname'), /\/data\/db\/db\.html$/);
    // The detail page emerges after the zoom and ends fully visible.
    const arrived = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      setTimeout(function () {
        var locator = document.getElementById('archify-locator');
        resolve({
          pending: document.documentElement.hasAttribute('data-zoom-arrival'),
          opacity: getComputedStyle(document.body).opacity,
          // Arriving by zoom briefly shows where this page sits in its parent.
          locator: !!locator && !locator.hidden,
          self: document.querySelectorAll('.archify-locator-node[data-state="self"]').length
        });
      }, 700);
    })`, true);
    assert.deepEqual(arrived, { pending: false, opacity: '1', locator: true, self: 1 });
  } finally {
    await browser.close();
  }
});

// root: hosts［h］ ─▶ events 枠、かつ h ─▶ e2（遷移先そのもの）。
function renderRouteFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-preview-route-'));
  const node = (id, label, pos, extra = {}) => ({ id, label, type: 'backend', pos, size: [160, 64], ...extra });
  const spec = (title, components, extra = {}) => ({ schema_version: 1, diagram_type: 'architecture', meta: { title, ...extra.meta }, components, connections: extra.connections || [], ...(extra.boundaries ? { boundaries: extra.boundaries } : {}) });
  const parent = { parent: { href: '../root.html', label: '全体図' } };
  const files = {
    'root.architecture.json': spec('全体図', [
      node('h', 'ホスト', [60, 160]),
      node('e1', 'イベント1', [420, 60]),
      node('e2', 'イベント2', [420, 260], { link: { href: 'b/b.html' } }),
    ], {
      boundaries: [
        { kind: 'region', id: 'hosts', label: 'hosts', wraps: ['h'], link: { href: 'a/a.html' } },
        { kind: 'region', id: 'events', label: 'events', wraps: ['e1', 'e2'] },
      ],
      connections: [{ from: 'h', to: 'events', label: '発火' }, { from: 'h', to: 'e2' }],
    }),
    'a/a.architecture.json': spec('A', [node('to-b', 'B へ', [60, 80], { link: { href: '../b/b.html', focus: 'y', title: 'B' } })], { meta: { hierarchy: parent } }),
    'b/b.architecture.json': spec('B', [node('x', 'X', [60, 80]), node('y', 'Y', [300, 80])], {
      meta: { hierarchy: { ...parent, incoming: [{ href: '../a/a.html', label: 'A', node: 'to-b', node_label: 'B へ', focus: 'y' }] } },
      connections: [{ from: 'x', to: 'y' }],
    }),
  };
  for (const name of Object.keys(files)) {
    const file = path.join(dir, name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(files[name]));
  }
  // a and b embed each other's thumbnails, so they render twice.
  for (const name of [...Object.keys(files), 'a/a.architecture.json', 'b/b.architecture.json']) {
    const file = path.join(dir, name);
    execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'render', 'architecture', file, file.replace(/\.architecture\.json$/, '.html')]);
  }
  return path.join(dir, 'a/a.html');
}

test('the link preview is opaque, hides the native tooltip and routes onto the destination itself', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, async () => {
  const artifact = renderRouteFixture();
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    for (const theme of ['light', 'dark']) {
      const sessionId = await browser.sessionPromise;
      await load(browser, `${artifact}`);
      await evaluate(browser, sessionId, `history.replaceState(null, '', '?theme=${theme}'); location.reload()`);
      await new Promise((resolve) => setTimeout(resolve, 800));
      const page = await checkLinkPreviewPage(browser, sessionId);
      assert.equal(page.nodes, 1);
      assert.deepEqual(page.problems, [], `${theme}: ${JSON.stringify(page.problems)}`);
    }
    // A direct line to the destination beats the line that only reaches its frame.
    const sessionId = await browser.sessionPromise;
    const route = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      var node = document.querySelector('[data-node-id="to-b"]');
      node.dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' }));
      setTimeout(function () {
        var card = document.getElementById('archify-link-preview');
        resolve({
          hops: card.querySelector('.archify-link-preview-route').getAttribute('data-hops'),
          litFrames: card.querySelectorAll('.archify-locator-group[data-route]:not([data-state])').length
        });
      }, 300);
    })`, true);
    assert.deepEqual(route, { hops: '1', litFrames: 0 });

    // The destination's own drawing shows the node the link lands on, and
    // that node in B shows where the link comes from.
    const landing = await evaluate(browser, sessionId, `(function () {
      var dest = document.querySelector('#archify-link-preview svg.archify-link-preview-dest');
      return dest ? Array.prototype.map.call(dest.querySelectorAll('[data-state="lands"]'), function (r) { return r.getAttribute('data-node'); }) : null;
    })()`);
    assert.deepEqual(landing, ['y']);
    const target = artifact.replace(/a\/a\.html$/, 'b/b.html');
    await load(browser, target);
    await new Promise((resolve) => setTimeout(resolve, 500));
    const arriving = await checkLinkPreviewPage(browser, sessionId);
    assert.equal(arriving.nodes, 1);
    assert.deepEqual(arriving.problems, []);
    const passport = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      document.querySelector('[data-node-id="y"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
      setTimeout(function () {
        resolve({
          badge: document.querySelector('[data-node-id="y"]').getAttribute('data-incoming'),
          links: Array.prototype.map.call(document.querySelectorAll('#focus-incoming a'), function (a) { return a.getAttribute('href'); })
        });
      }, 400);
    })`, true);
    assert.deepEqual(passport, { badge: '1', links: ['../a/a.html#focus=to-b'] });
  } finally {
    await browser.close();
  }
});

test('moving sideways to a sibling travels across the parent before the page changes', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, async () => {
  const artifact = renderRouteFixture();
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    const sessionId = await load(browser, artifact);
    await new Promise((resolve) => setTimeout(resolve, 400));
    const navigated = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    const trip = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      document.querySelector('[data-node-id="to-b"]').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
      setTimeout(function () {
        var stage = document.querySelector('.travel-stage');
        resolve({
          stage: !!stage,
          caption: stage ? stage.querySelector('.travel-caption').textContent : null,
          routes: stage ? stage.querySelectorAll('.travel-route').length : 0,
          self: stage ? stage.querySelectorAll('[data-state="self"]').length > 0 : false,
          target: stage ? stage.querySelectorAll('[data-state="target"]').length > 0 : false,
          still: location.pathname.split('/').pop()
        });
      }, 300);
    })`, true);
    assert.deepEqual(trip, { stage: true, caption: '全体図 の中を移動: A → B', routes: 1, self: true, target: true, still: 'a.html' });
    await navigated;
    assert.match(await evaluate(browser, sessionId, 'location.href'), /\/b\/b\.html#focus=y$/);

    // With motion stilled the same link changes page at once.
    await load(browser, artifact);
    await new Promise((resolve) => setTimeout(resolve, 400));
    const still = await evaluate(browser, sessionId, `(function () {
      document.documentElement.setAttribute('data-motion', 'still');
      document.querySelector('[data-node-id="to-b"]').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
      return !!document.querySelector('.travel-stage');
    })()`);
    assert.equal(still, false);
    let landed = null;
    for (let i = 0; i < 20 && !landed; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      landed = await evaluate(browser, sessionId, `/\\/b\\/b\\.html$/.test(location.pathname) ? location.pathname : null`).catch(() => null);
    }
    assert.ok(landed, 'navigated without travelling');
  } finally {
    await browser.close();
  }
});

test('hierarchy-build checks the link previews of the bundled example in a browser', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-hierarchy-build-preview-'));
  fs.cpSync(path.join(skillRoot, 'examples/hierarchy'), dir, { recursive: true, filter: (source) => !/\.html$|\.map\.architecture\.json$/.test(source) });
  const report = JSON.parse(execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'hierarchy-build', path.join(dir, 'shop.architecture.json'), '--strict', '--json'], { encoding: 'utf8' }));
  assert.equal(report.ok, true);
  assert.equal(report.preview.status, 'checked');
  assert.equal(report.preview.pages, 8);
  assert.deepEqual(report.preview.problems, []);
  // Every page and the map fit the desktop viewports.
  assert.equal(report.visual.status, 'checked');
  assert.deepEqual(report.visual.failed, []);
});

test('the preview check reports a viewer that never started instead of passing it', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, async () => {
  const artifact = renderRouteFixture();
  const broken = artifact.replace(/a\.html$/, 'broken.html');
  // A syntax error in the viewer script stops every runtime feature.
  fs.writeFileSync(broken, fs.readFileSync(artifact, 'utf8').replace('(function installHierarchyNavigation() {', '(function installHierarchyNavigation() { } else {'));
  const { checkLinkPreviews } = await import('../scripts/check-link-preview.mjs');
  const [page] = await checkLinkPreviews([broken], { themes: ['light'] });
  assert.deepEqual(page.problems.map((problem) => problem.code), ['viewer-error', 'viewer-missing']);
});

test('two siblings in one frame are reached along their line, not through the frame', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-sibling-route-'));
  const node = (id, label, pos, extra = {}) => ({ id, label, type: 'backend', pos, size: [160, 64], ...extra });
  const parent = { parent: { href: '../root.html', label: '全体図' } };
  const files = {
    'root.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: '全体図' },
      components: [node('p', 'P', [60, 120], { link: { href: 'p/p.html' } }), node('q', 'Q', [320, 120], { link: { href: 'q/q.html' } })],
      boundaries: [{ kind: 'region', id: 'g', label: 'g', wraps: ['p', 'q'] }],
      connections: [{ from: 'p', to: 'q', label: '保存' }] },
    'p/p.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: 'P', hierarchy: parent },
      components: [node('to-q', 'Q へ', [60, 80], { link: { href: '../q/q.html', focus: 'x', title: 'Q' } })], connections: [] },
    'q/q.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: 'Q', hierarchy: parent },
      components: [node('x', 'X', [60, 80])], connections: [] },
  };
  for (const name of Object.keys(files)) {
    const file = path.join(dir, name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(files[name]));
    execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'render', 'architecture', file, file.replace(/\.architecture\.json$/, '.html')]);
  }
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    const sessionId = await load(browser, path.join(dir, 'p/p.html'));
    await new Promise((resolve) => setTimeout(resolve, 400));
    const hops = await evaluate(browser, sessionId, `new Promise(function (resolve) {
      document.querySelector('[data-node-id="to-q"]').dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' }));
      setTimeout(function () {
        var card = document.getElementById('archify-link-preview');
        resolve({ hops: card.querySelector('.archify-link-preview-route').getAttribute('data-hops'), lit: card.querySelectorAll('.archify-locator-edge[data-route]').length });
      }, 300);
    })`, true);
    assert.deepEqual(hops, { hops: '1', lit: 1 });
  } finally {
    await browser.close();
  }
});

test('a route through a node without its own page lights that node and passes the preview check', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, () => {
  // A and B are joined only through M, which has no detail page.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-relay-route-'));
  const node = (id, label, pos, extra = {}) => ({ id, label, type: 'backend', pos, size: [160, 64], ...extra });
  const parent = { parent: { href: '../../root.html', label: '全体' } };
  const files = {
    'root.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: '全体' },
      components: [node('a', 'A', [40, 80], { link: { href: 'c/a/a.html' } }), node('m', 'M', [300, 80]), node('b', 'B', [560, 80], { link: { href: 'c/b/b.html' } })],
      connections: [{ from: 'a', to: 'm', label: '送信' }, { from: 'm', to: 'b', label: '転送' }] },
    'c/a/a.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: 'A', hierarchy: parent },
      components: [node('to-b', 'B へ', [60, 80], { link: { href: '../b/b.html', focus: 'x' } })], connections: [] },
    'c/b/b.architecture.json': { schema_version: 1, diagram_type: 'architecture', meta: { title: 'B', hierarchy: parent },
      components: [node('x', 'X', [60, 80])], connections: [] },
  };
  for (const name of Object.keys(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, name)), { recursive: true });
    fs.writeFileSync(path.join(dir, name), JSON.stringify(files[name]));
  }
  const report = JSON.parse(execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'hierarchy-build', path.join(dir, 'root.architecture.json'), '--quality', 'standard', '--no-visual-check', '--json'], { encoding: 'utf8' }));
  assert.equal(report.preview.status, 'checked');
  assert.deepEqual(report.preview.problems, []);
});

test('location tabs never cover a composite diagram whose headings start at the top', {
  skip: !chromePath && 'set ARCHIFY_CHROME to run browser checks',
}, () => {
  // workflow-er draws its section headings right at the top of the drawing.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-composite-tabs-'));
  fs.cpSync(path.join(skillRoot, 'test/fixtures/hierarchy-workflow-er'), dir, { recursive: true });
  const report = JSON.parse(execFileSync(process.execPath, [path.join(skillRoot, 'bin/archify.mjs'), 'hierarchy-build', path.join(dir, 'root.architecture.json'), '--quality', 'standard', '--repo-root', dir, '--no-visual-check', '--json'], { encoding: 'utf8' }));
  assert.equal(report.preview.status, 'checked');
  assert.deepEqual(report.preview.problems, []);
});
