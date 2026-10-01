import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { ChromeVisualBrowser, findChrome } from '../bin/visual-check.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const chrome = process.env.ARCHIFY_CHROME ? findChrome() : null;

test('access selection confines keyboard focus to its chip despite a long hidden note', {
  skip: chrome ? false : 'Set ARCHIFY_CHROME to run the browser focus regression.',
}, async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-access-focus-'));
  const browser = new ChromeVisualBrowser(chrome);
  try {
    const spec = JSON.parse(fs.readFileSync(path.join(root, 'examples/join-update-delete.sequence-er.json')));
    spec.sequence.messages.forEach(message => { message.note = '非表示の長い注釈。'.repeat(40); });
    const input = path.join(tmp, 'input.json'), output = path.join(tmp, 'output.html');
    fs.writeFileSync(input, JSON.stringify(spec));
    execFileSync(process.execPath, [path.join(root, 'bin/archify.mjs'), 'render', 'sequence-er', input, output, '--repo-root', root]);
    const session = await browser.sessionPromise;
    const loaded = browser.cdp.waitFor('Page.loadEventFired', session);
    await browser.cdp.send('Page.navigate', { url: pathToFileURL(output).href }, session);
    await loaded;
    await browser.cdp.send('Page.bringToFront', {}, session);
    const result = await browser.cdp.send('Runtime.evaluate', {
      returnByValue: true,
      expression: `Array.from(document.querySelectorAll('[data-access-id]')).map(group => {
        const arrow = group.querySelector('path'), chip = group.querySelector('.access-hit');
        const before = arrow.getBoundingClientRect().toJSON();
        group.focus();
        group.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        return { id: group.dataset.accessId, selected: group.ownerSVGElement.dataset.selectedAccess,
          outline: getComputedStyle(group).outlineStyle, chipStroke: getComputedStyle(chip).stroke,
          chipStrokeWidth: getComputedStyle(chip).strokeWidth, before,
          after: arrow.getBoundingClientRect().toJSON(),
          groupWidth: group.getBBox().width, arrowWidth: arrow.getBBox().width };
      })`,
    }, session);
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    assert.equal(result.result.value.length, 3);
    for (const row of result.result.value) {
      assert.ok(row.groupWidth > row.arrowWidth, 'the hidden note must extend beyond the arrow');
      assert.equal(row.outline, 'none', `${row.id}: a group outline would include the hidden note`);
      assert.equal(row.selected, row.id);
      assert.equal(row.chipStrokeWidth, '3px', `${row.id}: keyboard focus must remain visible`);
      assert.notEqual(row.chipStroke, 'none');
      assert.deepEqual(row.after, row.before, `${row.id}: selection must preserve arrow geometry`);
    }
  } finally {
    await browser.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
