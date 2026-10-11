(() => {
 const pages=[...document.querySelectorAll('[data-page]')],links=[...document.querySelectorAll('.topic-nav a')],groups=[...document.querySelectorAll('[data-topic-group]')],topLinks=[...document.querySelectorAll('.concern-nav a')];
 const previous=document.getElementById('page-previous'),next=document.getElementById('page-next'),status=document.getElementById('navigation-status');
 const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
 let current=pages[0],pending=0,pendingCommit=null,serial=0,source=null,arrival=null,lastHash=null,animations=[];
 function cancel(){serial++;if(pending)clearTimeout(pending);pending=0;pendingCommit=null;animations.forEach(a=>a.cancel());animations=[];if(source){source.classList.remove('navigation-source');source=null}if(arrival){arrival.classList.remove('navigation-arrival');arrival=null}}
 function animation(node,frames,options){if(!motion.matches&&node&&typeof node.animate==='function')animations.push(node.animate(frames,options))}
 function describe(target,page){if(!target||target===page)return page.dataset.label;if(target.id.endsWith('-detail-start'))return page.dataset.label+'の本文';const title=target.matches('h2,h3,h4,summary')?target:target.querySelector('summary,h2,h3,h4');if(title)return title.textContent.trim();if(/-line-\d+$/.test(target.id))return page.dataset.label+'：'+target.id.replace(/^.*-line-/,'')+'行目';return page.dataset.label+'：'+(target.getAttribute('aria-label')||'選んだ説明')}
 function render(moveFocus,originLabel){
  let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{id=''}
  const target=document.getElementById(id),page=(target&&target.closest('[data-page]'))||pages[0],old=current;current=page;lastHash=location.hash;
  pages.forEach(item=>{item.hidden=item!==page});groups.forEach(group=>{group.hidden=group.dataset.topicGroup!==page.dataset.group});
  links.forEach(link=>{if(link.getAttribute('href')==='#'+page.id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current')});
  topLinks.forEach(link=>{if(link.dataset.group===page.dataset.group)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current')});
  if(target&&target.tagName==='DETAILS')target.open=true;let parent=target&&target.parentElement;while(parent&&parent!==page){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement}
  const index=pages.indexOf(page);for(const [link,destination]of[[previous,pages[index-1]],[next,pages[index+1]]]){link.hidden=!destination;if(destination){link.setAttribute('href','#'+destination.id);link.textContent=(link===previous?'← ':'')+destination.dataset.label+(link===next?' →':'')}else link.removeAttribute('href')}
  if(!moveFocus)return;
  const focus=target&&page.contains(target)?target:page;if(!focus.hasAttribute('tabindex'))focus.setAttribute('tabindex','-1');focus.focus({preventScroll:true});
  const visual=focus.id.endsWith('-detail-start')?(focus.nextElementSibling||focus):focus;
  arrival=visual;visual.classList.add('navigation-arrival');
  if(status){status.hidden=false;status.textContent=(originLabel||old.dataset.label)+' → '+describe(focus,page);status.dataset.arrived='true'}
  const direction=pages.indexOf(page)>=pages.indexOf(old)?1:-1;
  if(old!==page)animation(page,[{opacity:.35,transform:'translateX('+direction*20+'px)'},{opacity:1,transform:'translateX(0)'}],{duration:360,easing:'ease-out'});
  animation(visual,[{backgroundColor:'#eeedfe',outlineColor:'#7c629a'},{backgroundColor:'transparent',outlineColor:'#d3d0c7'}],{duration:2200,easing:'ease-out'});
  const behavior=motion.matches?'auto':'smooth';if(focus===page)window.scrollTo({top:0,behavior});else visual.scrollIntoView({block:'center',behavior});
 }
 function navigate(hash,link,historyChange){
  document.dispatchEvent(new Event('explain:navigate'));
  const origin=current.dataset.label+(link?.closest('[data-concern-overview]')?'の全体図':'');cancel();const token=serial;
  if(link){source=link;link.classList.add('navigation-source');animation(link,[{backgroundColor:'#eeedfe'},{backgroundColor:'#e1f5ee'}],{duration:140,easing:'ease-out'})}
  if(status){status.hidden=false;status.textContent=origin+' → 移動しています';status.dataset.arrived='false'}
  const commit=()=>{if(token!==serial)return;pending=0;pendingCommit=null;if(historyChange&&location.hash!==hash)history.pushState(null,'',hash);if(source){source.classList.remove('navigation-source');source=null}render(true,origin)};
  pendingCommit=commit;if(motion.matches)commit();else pending=setTimeout(commit,140);
 }
 document.addEventListener('click',event=>{
  if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  const link=event.target.closest('a[href^="#"]');if(!link||link.hasAttribute('download')||link.getAttribute('target')==='_blank')return;
  const hash=link.getAttribute('href');let id;try{id=decodeURIComponent(hash.slice(1))}catch{return}if(!document.getElementById(id))return;
  event.preventDefault();navigate(hash,link,true);
 });
 function historyNavigation(){if(location.hash===lastHash)return;navigate(location.hash,null,false)}
 window.addEventListener('hashchange',historyNavigation);window.addEventListener('popstate',historyNavigation);
 function finishPending(){if(pendingCommit){if(pending)clearTimeout(pending);const commit=pendingCommit;pending=0;pendingCommit=null;commit()}}
 document.addEventListener('visibilitychange',()=>{if(document.hidden){finishPending();cancel();render(false)}});
 motion.addEventListener('change',()=>{if(motion.matches){finishPending();animations.forEach(a=>a.cancel());animations=[]}});
 render(Boolean(location.hash));
 const folded = new Set();
 window.addEventListener('beforeprint', () => document.querySelectorAll('details:not([open])').forEach(node => {folded.add(node);node.open=true}));
 window.addEventListener('afterprint', () => {folded.forEach(node => {node.open=false});folded.clear()});
 document.querySelectorAll('[data-diagram-zoom]').forEach(button => {
  const diagram = button.closest('figure').querySelector('.archify-overview-image');
  button.hidden = false;
  button.addEventListener('click', () => {
   const zoomed = diagram.toggleAttribute('data-zoomed');
   button.setAttribute('aria-pressed', String(zoomed));
   button.textContent = zoomed ? '図を全体表示に戻す' : '図の文字を拡大する';
  });
 });
})();
