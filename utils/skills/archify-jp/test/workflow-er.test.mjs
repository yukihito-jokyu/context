import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'archify-workflow-er-'));
const example=JSON.parse(fs.readFileSync(path.join(root,'examples/task-operations.workflow-er.json')));
function run(d,name){const input=path.join(tmp,name+'.json'),out=path.join(tmp,name+'.html');fs.writeFileSync(input,JSON.stringify(d));fs.writeFileSync(out,'last good');const result=spawnSync(process.execPath,[path.join(root,'bin/archify.mjs'),'deliver','workflow-er',input,out,'--repo-root',root,'--quality','showcase','--json'],{encoding:'utf8'});return {...result,html:fs.readFileSync(out,'utf8')};}
test('workflow and ER deliver as one SVG with separate identities and access bindings',()=>{
 const d=structuredClone(example);d.meta.views=[{id:'targets',label:'対象',focus:['flow-query-1','er-tasks']}];
 const r=run(d,'valid');assert.equal(r.status,0,r.stdout+r.stderr);assert.equal((r.html.match(/<svg\b/g)||[]).length,1);
 assert.match(r.html,/data-diagram-type="workflow-er"/);assert.match(r.html,/data-section="workflow"/);assert.match(r.html,/data-section="er"/);
 assert.match(r.html,/data-node-id="flow-query-1"[^>]*data-access-id="A1"/);assert.match(r.html,/data-node-id="er-tasks"/);assert.match(r.html,/data-role-toggle="delete"/);
 const left=r.html.match(/<g transform="translate\(([^)]+)\)" data-section="workflow"/)[1].split(' ').map(Number);
 const right=r.html.match(/<g transform="translate\(([^)]+)\)" data-section="er"/)[1].split(' ').map(Number);assert(right[0]>left[0]);
});
for(const [name,change] of [
 ['unknown-node',d=>d.accesses[0].node='missing'],
 ['duplicate-binding',d=>d.accesses[1].node=d.accesses[0].node],
 ['unknown-column',d=>d.accesses[0].read.push('tasks.missing')],
 ['source-mismatch',d=>d.accesses[0].source.quote='wrong SQL'],
 ['missing-er',d=>delete d.er],
 ['missing-ddl',d=>d.evidence=[]],
 ['wrong-focus',d=>d.meta.views=[{id:'bad',label:'bad',focus:['query-1']}]],
])test(name+' fails without replacing output',()=>{const d=structuredClone(example);change(d);const r=run(d,name);assert.notEqual(r.status,0);assert.equal(r.html,'last good')});
test.after(()=>fs.rmSync(tmp,{recursive:true,force:true}));
