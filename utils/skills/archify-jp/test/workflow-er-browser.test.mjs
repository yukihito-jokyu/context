import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {ChromeVisualBrowser,findChrome} from '../bin/visual-check.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const chrome=process.env.ARCHIFY_CHROME?findChrome():null;
test('workflow node click and keyboard selection map SQL roles without moving nodes',{skip:chrome?false:'Set ARCHIFY_CHROME for browser checks.'},async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'archify-workflow-er-browser-')),browser=new ChromeVisualBrowser(chrome);
 try{
  const out=path.join(tmp,'diagram.html');
  execFileSync(process.execPath,[path.join(root,'bin/archify.mjs'),'deliver','workflow-er',path.join(root,'examples/task-operations.workflow-er.json'),out,'--repo-root',root,'--quality','showcase']);
  const session=await browser.sessionPromise,cdp=browser.cdp;
  const loaded=cdp.waitFor('Page.loadEventFired',session);
  await cdp.send('Page.navigate',{url:pathToFileURL(out).href},session);await loaded;await cdp.send('Page.bringToFront',{},session);
  async function evaluate(expression){const r=await cdp.send('Runtime.evaluate',{expression,returnByValue:true},session);assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;}
  const before=await evaluate(`Array.from(document.querySelectorAll('[data-section=workflow] [data-node-id]')).map(e=>e.getBoundingClientRect().toJSON())`);
  const center=await evaluate(`(()=>{const r=document.querySelector('[data-access-id=A2]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  await cdp.send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...center},session);
  await cdp.send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...center},session);
  assert.equal(await evaluate(`document.querySelector('svg').dataset.selectedAccess`),'A2');
  assert.equal(await evaluate(`document.querySelector('[data-column-ref="tasks.state"]').dataset.accessRole`),'write');
  await evaluate(`document.querySelector('[data-access-id=A3]').focus()`);
  await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32},session);
  await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32},session);
  assert.equal(await evaluate(`document.querySelector('svg').dataset.selectedAccess`),'A3');
  assert.equal(await evaluate(`document.querySelector('[data-entity-id=tasks]').hasAttribute('data-delete-target')`),true);
  await evaluate(`document.querySelector('[data-role-toggle=filter]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
  assert.equal(await evaluate(`document.querySelector('[data-column-ref="tasks.state"]').dataset.accessRole`),'filter');
  assert.equal(await evaluate(`document.querySelector('[data-entity-id=tasks]').hasAttribute('data-delete-target')`),false);
  const after=await evaluate(`Array.from(document.querySelectorAll('[data-section=workflow] [data-node-id]')).map(e=>e.getBoundingClientRect().toJSON())`);
  assert.deepEqual(after,before);
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('[data-access-id=A3]')).outlineStyle`),'none');
 }finally{await browser.close();fs.rmSync(tmp,{recursive:true,force:true})}
});
