#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {spawnSync} from 'node:child_process';import {esc} from '../renderers/shared/utils.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),flag=k=>{const i=args.indexOf(k);if(i<0||!args[i+1])throw Error('Missing '+k);return path.resolve(args[i+1])};
export function renderBundle(input,repo,out){
 if(fs.existsSync(out)||fs.existsSync(out+'.generating'))throw Error('Output already exists');
 if(input.schema_version!==1||!input.views?.length)throw Error('Invalid bundle');
 const ids=new Set();for(const v of input.views){if(!/^[a-z][a-z0-9-]*$/.test(v.slug)||ids.has(v.slug))throw Error('Unsafe/duplicate view slug');ids.add(v.slug)}
 const stage=out+'.generating';fs.mkdirSync(path.join(stage,'normalized'),{recursive:true});
 try{const manifest=[];
 for(const v of input.views){
  const diagram={schema_version:1,diagram_type:'sequence-er',meta:{title:v.title,locale:'ja',quality_profile:'showcase'},...Object.fromEntries(Object.entries(v).filter(([k])=>!['slug','title','kind','phase'].includes(k)))};
  diagram.navigation=input.views.map(p=>({href:p.slug+'.html',label:p.label||p.title,current:p.slug===v.slug}));
  const spec=path.join(stage,'normalized',v.slug+'.sequence-er.json'),output=path.join(stage,v.slug+'.html');fs.writeFileSync(spec,JSON.stringify(diagram,null,2)+'\n');
  const result=spawnSync(process.execPath,[path.join(root,'bin/archify.mjs'),'deliver','sequence-er',spec,output,'--repo-root',repo,'--quality','showcase','--json'],{encoding:'utf8',maxBuffer:16*1024*1024});
  if(result.status!==0)throw Error(result.stderr||result.stdout);
  const html=fs.readFileSync(output,'utf8'),svg=html.match(/<svg\b[\s\S]*?<\/svg>/)[0];fs.writeFileSync(path.join(stage,v.slug+'.svg'),svg+'\n');
  manifest.push({view:v.slug,mode:v.er?'sequence-er':'sequence',input:'normalized/'+v.slug+'.sequence-er.json',html:v.slug+'.html',svg:v.slug+'.svg'});
 }
 fs.writeFileSync(path.join(stage,'input.json'),JSON.stringify(input,null,2)+'\n');fs.writeFileSync(path.join(stage,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 fs.writeFileSync(path.join(stage,'index.html'),`<!doctype html><html lang="ja"><meta charset="utf-8"><title>${esc(input.title)}</title><h1>${esc(input.title)}</h1><ul>${input.views.map(v=>`<li><a href="${v.slug}.html">${esc(v.title)}</a></li>`).join('')}</ul></html>\n`);
 fs.renameSync(stage,out);return manifest;
 }catch(e){fs.rmSync(stage,{recursive:true,force:true});throw e}
}
if(process.argv[1]===fileURLToPath(import.meta.url)){try{const m=renderBundle(JSON.parse(fs.readFileSync(flag('--input'),'utf8')),flag('--repo-root'),flag('--out-dir'));console.log(JSON.stringify({status:'pass',views:m.length}))}catch(e){console.error(e.message);process.exitCode=1}}
