import {esc} from '../shared/utils.mjs';
import {css} from './ui.mjs';
// Minimal XML tree reader for SVG produced by the bundled renderers, never arbitrary HTML.
function parse(xml){const dummy={tag:'',attrs:{},children:[]},stack=[dummy];for(const token of xml.match(/<[^>]*>|[^<]+/g)||[]){if(token.startsWith('<!--'))continue;if(token.startsWith('</')){stack.pop();continue}if(token.startsWith('<')){const m=token.match(/^<([\w:-]+)/);if(!m)continue;const n={tag:m[1],attrs:{},children:[]};for(const a of token.matchAll(/([\w:-]+)(?:="([^"]*)")?/g)){if(a.index<=m[0].length-1)continue;n.attrs[a[1]]=a[2]??''}stack.at(-1).children.push(n);if(!token.endsWith('/>'))stack.push(n)}else stack.at(-1).children.push(token)}return dummy.children.find(x=>x.tag==='svg')}
const node=(tag,attrs={},children=[])=>({tag,attrs:Object.fromEntries(Object.entries(attrs).map(([k,v])=>[k,esc(String(v))])),children});
const text=(x,y,value,cls='access-caption')=>node('text',{x,y,class:cls},[esc(value)]);
function serialize(n){return typeof n==='string'?n:`<${n.tag}${Object.entries(n.attrs).map(([k,v])=>` ${k}="${v}"`).join('')}>${n.children.map(serialize).join('')}</${n.tag}>`}
function elements(n){return [n,...n.children.filter(x=>typeof x!=='string').flatMap(elements)]}
function namespace(n,prefix){for(const e of elements(n)){if(e.attrs.id)e.attrs.id=prefix+e.attrs.id;for(const key of ['data-edge-id','data-composition-edge-id'])if(e.attrs[key])e.attrs[key]=prefix+e.attrs[key];for(const key of ['data-node-id','data-edge-from','data-edge-to','data-composition-edge-from','data-composition-edge-to'])if(e.attrs[key])e.attrs[key]=prefix+e.attrs[key];if(e.attrs['data-edge-key'])e.attrs['data-edge-key']=prefix+e.attrs['data-edge-key'];for(const [k,v] of Object.entries(e.attrs))if(v.includes('url(#'))e.attrs[k]=v.replaceAll('url(#','url(#'+prefix)}return n}

export const cards=()=>`<div class="cards"><div class="card"><h3 id="access-title"></h3><ul><li id="access-operation"></li><li id="access-values"></li></ul></div><div class="card"><h3>対象の条件</h3><ul><li id="access-filter"></li><li id="access-help"></li></ul></div><div class="card"><h3>SQLでの参照方法</h3><ul><li id="access-relation"></li><li id="access-source"></li></ul></div></div>`;
function controls(x,y){return node('g',{},[['all','すべて','text-muted'],['read','取得','backend-stroke'],['filter','条件','cloud-stroke'],['join','結合・参照','frontend-stroke'],['write','更新','security-stroke'],['delete','DELETE','security-stroke']].map(([r,label,color],i)=>node('g',{'data-role-toggle':r,role:'button',tabindex:0,'aria-pressed':true,'aria-label':label+'の表示切替',transform:`translate(${x+i*124} ${y})`},[node('rect',{class:'role-toggle-hit',width:116,height:28,rx:5}),node('circle',{cx:12,cy:14,r:4,fill:`var(--${color})`}),text(24,18,label,'access-key')])))}
export function compose(v,seq,er){
 const workflow=!!v.workflow,prefix=workflow?'flow-':'seq-',section=workflow?'workflow':'sequence';
 const l={sequenceWidth:workflow?Number(seq.attrs.viewBox.split(/\s+/)[2])+40:v.sequence.meta.viewBox?.[0]||1100,erWidth:v.er.meta.viewBox?.[0]||780,height:920,footerY:795,controlsY:850,...v.layout};if(workflow&&v.layout?.workflowWidth)l.sequenceWidth=v.layout.workflowWidth;const w=l.sequenceWidth+25+l.erWidth,x=l.sequenceWidth+20,rootSvg=node('svg',{viewBox:`0 0 ${w} ${l.height}`,role:'img',lang:'ja','aria-labelledby':'diagram-title diagram-description','data-preset':'classic','data-quality-profile':v.meta?.quality_profile||process.env.ARCHIFY_QUALITY_PROFILE||'showcase','data-diagram-type':v.diagram_type||'sequence-er'},[node('title',{id:'diagram-title'},[esc(v.title)]),node('desc',{id:'diagram-description'},[esc((v.context||'')+' '+(v.scope||''))]),node('rect',{width:w,height:l.height,fill:'var(--panel)'}),node('line',{x1:l.sequenceWidth,y1:25,x2:l.sequenceWidth,y2:l.height-30,stroke:'var(--panel-border)'}),text(35,30,(v.workflowHeading||v.sequenceHeading||v.label||v.title)+'：処理順','access-panel-title'),text(x+15,30,'参照・変更するデータモデル','access-panel-title'),text(35,58,v.caption||'A番号を選択して、実際のSQLの対象を確認'),text(x+15,58,'PK：主キー。FK：確認済みのDB制約。関係線はテーブル間の関連。')]);
 seq=namespace(seq,prefix);for(const e of elements(seq)){if(e.tag==='text'&&e.attrs['font-size'])e.attrs['font-size']=String(Math.max(12.3,Number(e.attrs['font-size'])*1.3));if('data-legend' in e.attrs)e.attrs.transform='translate(0 65)'}
 for(const a of v.accesses){
  const e=elements(seq).find(e=>workflow?e.attrs['data-node-id']===prefix+a.node:e.attrs['data-edge-id']===prefix+a.message);
  const shape=workflow?e.children.find(e=>e.tag==='rect'):null,t=workflow?null:elements(e).find(e=>e.tag==='text');
  const cx=workflow?Number(shape.attrs.x)+Number(shape.attrs.width)-20:Number(t.attrs.x),y=workflow?Number(shape.attrs.y)+Number(shape.attrs.height)-23:Number(t.attrs.y)+5;
  Object.assign(e.attrs,{'data-access-id':esc(a.id),role:'button',tabindex:'0','aria-pressed':'false'});
  e.children.push(node('rect',{x:cx-15,y,width:30,height:17,rx:3,class:'access-hit'}),node('text',{x:cx,y:y+12,'text-anchor':'middle',class:'access-key','font-size':11},[esc(a.id)]));
 }
 rootSvg.children.push(node('g',{transform:'translate(20 20)','data-section':section},seq.children.filter(e=>typeof e==='string'||!['title','desc'].includes(e.tag))));
 er=namespace(er,'er-');for(const e of elements(er)){if(e.tag==='marker'){e.attrs.markerWidth='12';e.attrs.markerHeight='12';e.attrs.markerUnits='userSpaceOnUse'}if(l.routes?.[e.attrs['data-edge-id']?.replace(/^er-/, '')]){e.attrs.d=esc(l.routes[e.attrs['data-edge-id'].replace(/^er-/, '')]);delete e.attrs['data-composition-points']}}
 for(const entity of v.er.entities){const outer=elements(er).find(e=>e.attrs['data-node-id']==='er-'+entity.id),inner=outer.children.find(e=>e.tag==='g'),width=Number(inner.children.find(e=>e.tag==='rect').attrs.width);outer.attrs['data-entity-id']=esc(entity.id);
  const rows=entity.columns.map((c,i)=>node('rect',{x:2,y:46+i*41,width:width-4,height:39,rx:3,class:'access-column','data-column-ref':entity.id+'.'+c.id}));inner.children.splice(3,0,...rows);
  entity.columns.forEach((c,i)=>['read','filter','join','write'].forEach((r,j)=>inner.children.push(node('rect',{x:width-14+j*3,y:47+i*41,width:2,height:37,class:'access-role-strip','data-column-strip':entity.id+'.'+c.id,'data-role':r}))));inner.children.push(text(width-12,13,'DELETE','delete-label'));
 }
 rootSvg.children.push(node('g',{transform:`translate(${x} 20)`,'data-section':'er'},er.children.filter(e=>typeof e==='string'||!['title','desc'].includes(e.tag))),text(35,l.footerY,v.context||''),text(35,l.footerY+27,v.scope||''),controls(x+15,l.controlsY),text(x+15,l.controlsY+53,'押すとその種類だけ表示。同じボタンで解除。「すべて」で戻す。'),node('defs',{},[node('style',{},[css])]))
 return serialize(rootSvg);
}
export function extract(html){const m=html.match(/<svg\b[\s\S]*?<\/svg>/);if(!m)throw Error('Missing SVG');return parse(m[0])}
// Static checker projection of the generated SVG: all shapes share root coordinates.
// This does not alter the delivered HTML or its nested interaction layers.
export function inspectionSvg(svg){
 const tree=parse(svg);
 function movePath(d,dx,dy){let command='',index=0;return d.replace(/[A-Za-z]|[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/g,t=>{if(/^[A-Za-z]$/.test(t)){command=t;index=0;return t}let n=Number(t);if(command!==command.toUpperCase())return t;if(command==='H')n+=dx;else if(command==='V')n+=dy;else if(['M','L','Q','C','S','T'].includes(command))n+=index++%2===0?dx:dy;return String(n)})}
 function walk(n,dx=0,dy=0,detail=false){
  if(typeof n==='string')return;
  if(n.attrs.transform?.includes('scale(')&&!elements(n).some(e=>'data-node-id' in e.attrs||'data-edge-id' in e.attrs||'data-node-label' in e.attrs))return;
  if(n.attrs.transform){const m=n.attrs.transform.match(/^translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)$/);if(!m)throw Error('Unsupported inspection transform: '+n.attrs.transform);dx+=Number(m[1]);dy+=Number(m[2]);delete n.attrs.transform}
  detail=detail||n.attrs['data-detail']==='context';if(n.tag==='text'&&detail)n.attrs['data-detail']='context';
  for(const k of ['x','x1','x2','cx'])if(k in n.attrs&&!n.attrs[k].includes('%'))n.attrs[k]=String(Number(n.attrs[k])+dx);
  for(const k of ['y','y1','y2','cy'])if(k in n.attrs&&!n.attrs[k].includes('%'))n.attrs[k]=String(Number(n.attrs[k])+dy);
  if(n.attrs.d)n.attrs.d=movePath(n.attrs.d,dx,dy);
  if(n.attrs['data-composition-points'])n.attrs['data-composition-points']=n.attrs['data-composition-points'].split(';').map(p=>{const [x,y]=p.split(',').map(Number);return `${x+dx},${y+dy}`}).join(';');
  if(n.tag==='text'&&n.attrs.class?.split(' ').includes('t-node'))n.attrs['data-node-label']='';
  n.children.forEach(x=>walk(x,dx,dy,detail));
 }
 walk(tree);return serialize(tree);
}
