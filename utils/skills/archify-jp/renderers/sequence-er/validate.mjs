import fs from 'node:fs';import path from 'node:path';import {throwDiagnosticProblems} from '../shared/diagnostics.mjs';
function unique(items,what){const ids=new Set;for(const x of items){if(!x.id||ids.has(x.id))throw Error('Missing/duplicate '+what+' ID');ids.add(x.id)}return ids}
function validateBundle(input,repo){
 if(input.schema_version!==1||!Array.isArray(input.views)||!input.views.length)throw Error('Invalid input');unique(input.views.map(v=>({id:v.slug})),'view');
 const evidence=[];
 for(const v of input.views){if(!/^[a-z][a-z0-9-]*$/.test(v.slug))throw Error('Unsafe view filename');const messages=unique(v.sequence.messages,'message');unique(v.sequence.participants,'participant');
  if(!v.er){if(v.accesses?.length)throw Error('Accesses require ER');continue}
  if(!v.accesses?.length)throw Error('ER requires accesses');const entities=unique(v.er.entities,'entity'),relations=unique(v.er.relationships,'relation');unique(v.accesses,'access');
  const cols=new Set(v.er.entities.flatMap(e=>{unique(e.columns,'column');return e.columns.map(c=>e.id+'.'+c.id)}));
  for(const r of v.er.relationships)for(const side of ['from','to'])if(!cols.has(r[side].entity+'.'+r[side].column))throw Error('Unknown relationship column');
  for(const a of v.accesses){if(!messages.has(a.message)||!['SELECT','UPDATE','DELETE'].includes(a.operation))throw Error('Unknown message/operation');for(const role of ['read','filter','join','write']){if(!Array.isArray(a[role]))throw Error('Missing role array');for(const c of a[role])if(!cols.has(c))throw Error('Unknown column '+c)}for(const e of a.delete)if(!entities.has(e))throw Error('Unknown DELETE entity');for(const r of a.relations)if(!relations.has(r.id)||!['inner','left','subquery'].includes(r.kind))throw Error('Unknown relation');if(a.operation==='DELETE'&&a.write.length||a.operation!=='DELETE'&&a.delete.length||a.operation==='SELECT'&&a.write.length)throw Error('Inconsistent operation roles');evidence.push(a.source)}
  unique(v.accesses.map(a=>({id:a.message})),'access message');if(v.default&&!v.accesses.some(a=>a.id===v.default))throw Error('Unknown default access');
  for(const e of v.er.entities)if(!v.evidence?.some(x=>x.entity===e.id))throw Error('Missing DDL evidence '+e.id);evidence.push(...v.evidence);
 }
 if(evidence.length&&!repo)throw Error('SQL/DDL evidence requires --repo-root');
 for(const e of evidence){if(!e.path||path.isAbsolute(e.path)||e.path.split(/[\\/]/).some(x=>!x||x==='..'||x==='.'||x==='.git')||!Number.isInteger(e.line)||e.line<1||!e.quote)throw Error('Invalid source reference');const full=fs.realpathSync(path.resolve(repo,e.path)),realRepo=fs.realpathSync(repo);if(!full.startsWith(realRepo+path.sep))throw Error('Evidence outside repository');const actual=fs.readFileSync(full,'utf8').split('\n').slice(e.line-1).join('\n');if(!actual.startsWith(e.quote))throw Error('Source mismatch '+e.path+':'+e.line)}
 return evidence.length;
}

export function validateAccesses(diagram,repo){try{return validateBundle({schema_version:1,views:[{...diagram,slug:'diagram'}]},repo)}catch(e){throwDiagnosticProblems('Sequence ER validation failed',[e.message],{code:'sequence-er/reference',subject:{diagramType:'sequence-er'}})}}
