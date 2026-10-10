import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ChromeVisualBrowser, findChrome } from '../bin/visual-check.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(here, '..');
const tmp = os.tmpdir();
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

test('clicking a class or ER node frames that node itself in the shared Viewer', {
  skip: chromePath ? false : 'Set ARCHIFY_CHROME to run the browser focus regression.',
}, async () => {
  const browser = new ChromeVisualBrowser(chromePath);
  try {
    for (const entry of [
      { type: 'class', fixture: 'domain-model.class.json', id: 'customer', expectedX: 60 },
      { type: 'er', fixture: 'ecommerce.er.json', id: 'customers', expectedX: 55 },
    ]) {
      const output = path.join(tmp, `archify-focus-${process.pid}-${entry.type}.html`);
      execFileSync(process.execPath, [
        path.join(skillRoot, 'bin', 'archify.mjs'), 'render', entry.type,
        path.join(skillRoot, 'examples', entry.fixture), output,
      ]);
      const sessionId = await load(browser, output);
      const receipt = await evaluate(browser, sessionId, `(function () {
        var node = document.querySelector('[data-node-id="${entry.id}"]');
        var logicalBox = node.getBBox();
        node.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        return new Promise(function (resolve) {
          setTimeout(function () {
            var state = Archify.view.state();
            resolve({
              logicalX: logicalBox.x,
              scale: state.scale,
              mode: state.mode,
              pressed: node.getAttribute('aria-pressed'),
              active: Archify.focus.active()
            });
          }, 650);
        });
      })()`, true);
      assert.equal(receipt.logicalX, entry.expectedX, JSON.stringify(receipt));
      assert.equal(receipt.active, entry.id, JSON.stringify(receipt));
      assert.equal(receipt.pressed, 'true', JSON.stringify(receipt));
      assert.equal(receipt.mode, 'semantic', JSON.stringify(receipt));
      assert.ok(receipt.scale > 1.9, `node-only framing must exceed the neighbor cap: ${JSON.stringify(receipt)}`);
    }
  } finally {
    await browser.close();
  }
});
