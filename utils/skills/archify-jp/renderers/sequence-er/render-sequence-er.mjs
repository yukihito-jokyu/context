import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {loadDiagram,writeDiagram} from '../shared/cli.mjs';
import {esc} from '../shared/utils.mjs';
import {compose,extract,cards} from './compose.mjs';
import {css,runtime,patchGeometry} from './ui.mjs';
const rendererDir=path.dirname(fileURLToPath(import.meta.url));
const {diagram,template:baseTemplate,outPath}=loadDiagram({rendererDir,diagramType:'sequence-er',defaultExample:'join-update-delete.sequence-er.json'});
const nav=diagram.navigation?.length?'<nav class="phase-nav" aria-label="図の切替">'+diagram.navigation.map(p=>`<a href="${esc(p.href)}"${p.current?' aria-current="page"':''}>${esc(p.label)}</a>`).join('')+'</nav>':'';
const template=baseTemplate.replace('</style>',css+'</style>').replace('    </div>\n\n    <!-- ARCHIFY:GUIDED_VIEWS_DATA -->',nav+'\n    </div>\n\n    <!-- ARCHIFY:GUIDED_VIEWS_DATA -->');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'archify-sequence-er-'));
try{
 const components={};
 for(const type of ['sequence',...(diagram.er?['er']:[])]){
  const input=path.join(tmp,type+'.json'),output=path.join(tmp,type+'.html');
  fs.writeFileSync(input,JSON.stringify(diagram[type]));
  const result=spawnSync(process.execPath,[path.resolve(rendererDir,'..',type,'render-'+type+'.mjs'),input,output],{encoding:'utf8',maxBuffer:16*1024*1024});
  if(result.status!==0)throw Error(result.stderr||result.stdout||'Component renderer failed');
  components[type]=fs.readFileSync(output,'utf8');
 }
 if(!diagram.er){
  // Delegate the complete output, preserving the standalone sequence behavior.
  const svg=components.sequence.match(/<svg\b[\s\S]*?<\/svg>/)[0];
  writeDiagram({outPath,template,diagramType:'sequence-er',meta:diagram.meta,svg,cards:diagram.sequence.cards});
 }else{
  const svg=compose({...diagram,title:diagram.meta.title},extract(components.sequence),extract(components.er));
  const data=JSON.stringify({accesses:diagram.accesses,default:diagram.default}).replaceAll('<','\\u003c');
  const enhanced=patchGeometry(template).replace('</body>',`<script id="sequence-er-data" type="application/json">${data}</script><script>${runtime}</script></body>`);
  writeDiagram({outPath,template:enhanced,diagramType:'sequence-er',meta:diagram.meta,svg,cardsHtml:cards()});
 }
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
