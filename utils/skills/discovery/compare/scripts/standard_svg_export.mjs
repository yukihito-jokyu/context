// Run Archify's unmodified serializeSvg function with a bounded DOM adapter.
// This is SVG serialization, not a browser screenshot or Canvas PNG export.
import fs from 'node:fs';import vm from 'node:vm';import {fileURLToPath} from 'node:url';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const template=fs.readFileSync(fileURLToPath(new URL('../vendor/archify-jp/assets/template.html',import.meta.url)),'utf8');
const start=template.indexOf('      function serializeSvg(scale, opts) {');const end=template.indexOf('      function download(blob, filename)',start);if(start<0||end<start)throw Error('Unsupported Archify exporter; use the browser export and review compatibility after sync.');const source=template.slice(start,end);
function escape(s,attr=false){return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"',attr?'&quot;':'"')}
class Element{
 constructor(tag,attrs={},children=[]){this.tagName=tag;this.attrs={...attrs};this.children=children.map(x=>typeof x==='string'?x:new Element(x.tag,x.attrs,x.children));this.children.forEach(x=>{if(typeof x!=='string')x.parent=this});const e=this;this.style={removeProperty(k){const parts=(e.attrs.style||'').split(';').filter(x=>x.trim()&&!x.trim().startsWith(k+':'));if(parts.length)e.attrs.style=parts.join(';');else delete e.attrs.style},getPropertyValue(k){return (e.attrs.style||'').split(';').find(x=>x.trim().startsWith(k+':'))?.split(':').slice(1).join(':')||''},set cssText(v){e.attrs.style=v}}}
 getAttribute(k){return this.attrs[k]??null}setAttribute(k,v){this.attrs[k]=String(v)}removeAttribute(k){delete this.attrs[k]}hasAttribute(k){return Object.hasOwn(this.attrs,k)}
 get firstChild(){return this.children[0]||null}get nextSibling(){const a=this.parent?.children||[];return a[a.indexOf(this)+1]||null}
 set textContent(v){this.children=[String(v)]}get textContent(){return this.children.map(x=>typeof x==='string'?x:x.textContent).join('')}
 matches(selector){const attrs=[...selector.matchAll(/\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/g)];return attrs.every(x=>this.hasAttribute(x[1])&&(x[2]===undefined||this.getAttribute(x[1])===x[2]))}
 querySelectorAll(selector){let result=[];for(const child of this.children){if(typeof child==='string')continue;if(selector.split(',').some(x=>child.matches(x.trim())))result.push(child);result.push(...child.querySelectorAll(selector))}return result}
 cloneNode(){return new Element(this.tagName,this.attrs,this.children.map(x=>typeof x==='string'?x:{tag:x.tagName,attrs:x.attrs,children:x.toObject().children}))}
 toObject(){return {tag:this.tagName,attrs:this.attrs,children:this.children.map(x=>typeof x==='string'?x:x.toObject())}}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this)}
 insertBefore(x,ref){let i=ref===null?this.children.length:this.children.indexOf(ref);if(i<0)throw Error('Missing child');x.parent=this;this.children.splice(i,0,x)}
 appendChild(x){x.parent=this;this.children.push(x)}removeChild(x){this.children=this.children.filter(v=>v!==x)}
 get viewBox(){let [x,y,width,height]=this.getAttribute('viewBox').split(/\s+/).map(Number);return {baseVal:{x,y,width,height}}}
}
function serialize(e){if(typeof e==='string')return escape(e);return '<'+e.tagName+Object.entries(e.attrs).map(([k,v])=>' '+k+'="'+escape(v,true)+'"').join('')+'>'+e.children.map(serialize).join('')+'</'+e.tagName+'>'}
const svg=new Element(input.svg.tag,input.svg.attrs,input.svg.children);svg.setAttribute('data-preset','editorial');
const root=new Element('html',{'data-preset':'editorial','data-theme':'light'}),body=new Element('body');root.appendChild(body);
const document={documentElement:root,body,styleSheets:[{cssRules:input.rules}],querySelector(s){if(s==='.diagram-container svg')return svg;if(s.startsWith('[data-theme='))return root;return null},createElement:tag=>new Element(tag),createElementNS:(ns,tag)=>new Element(tag)};
function computed(e){const theme=e.getAttribute('data-theme')||'light';const values=input.variables[theme];return {getPropertyValue:n=>values[n]||'',backgroundColor:values['--bg']}}
const context={document,getComputedStyle:computed,XMLSerializer:class{serializeToString(e){return serialize(e)}}};vm.createContext(context);vm.runInContext(source+'\nthis.exported=serializeSvg(1,{autoTheme:false});',context);
if(!context.exported.canonicalStateClean)throw Error('Unclean canonical export');process.stdout.write(JSON.stringify(context.exported));
