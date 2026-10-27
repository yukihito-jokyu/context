const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const puppeteer=require('<user-home>/.npm/_npx/668c188756b835f3/node_modules/puppeteer/lib/puppeteer/puppeteer.js');
const root=__dirname, catalog=path.join(root,'project/.skill-runs/generate-domain-model-from-code/out/subscription-billing');
const out=path.join(root,'evidence');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const result={url:pathToFileURL(path.join(catalog,'index.html')).href,browser:'existing Google Chrome',viewports:[],png_opened:[],errors:[],http_requests:[],downloads:[]};
(async()=>{
 fs.rmSync(path.join(out,'downloads'),{recursive:true,force:true});fs.mkdirSync(path.join(out,'downloads'),{recursive:true});fs.mkdirSync(path.join(out,'screenshots'),{recursive:true});
 const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,userDataDir:path.join(root,'browser-profile'),args:['--no-first-run','--no-default-browser-check']});
 try{
  const page=await browser.newPage();
  page.on('pageerror',e=>result.errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error')result.errors.push(m.text())});
  page.on('request',r=>{if(/^https?:/.test(r.url()))result.http_requests.push(r.url())});
  const cdp=await page.createCDPSession();
  await cdp.send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:path.join(out,'downloads')});
  for(const viewport of [{name:'desktop',width:1440,height:1000,isMobile:false,hasTouch:false},{name:'mobile',width:390,height:844,isMobile:true,hasTouch:true}]){
   const {name,...size}=viewport;await page.setViewport(size);await page.goto(result.url,{waitUntil:'load'});await page.waitForFunction(()=>[...document.querySelectorAll('.preview img')].every(i=>i.complete&&i.naturalWidth>0));
   const info=await page.evaluate(()=>({title:document.title,lang:document.documentElement.lang,concepts:document.querySelectorAll('.concept').length,diagrams:document.querySelectorAll('.diagram').length,count:document.querySelector('#count').textContent,bodyWidth:document.body.scrollWidth,viewportWidth:innerWidth,header:document.querySelector('h1').textContent}));
   assert.equal(info.title,'定期契約と請求のドメインモデル');assert.equal(info.lang,'ja');assert.equal(info.concepts,4);assert.equal(info.diagrams,3);assert.equal(info.count,'4件の概念');assert.ok(info.bodyWidth<=info.viewportWidth);
   const record={viewport,initial:info,search:[],domains:[],zoom:[],code_evidence:false};
   for(const [query,expected] of [['Customer',1],['請求書',1],['Plan',1],['存在しない概念',0],['',4]]){
    await page.focus('#search');await page.keyboard.press('Home');await page.keyboard.down('Shift');await page.keyboard.press('End');await page.keyboard.up('Shift');await page.keyboard.press('Backspace');if(query)await page.type('#search',query);
    const found=await page.evaluate(()=>({visible:[...document.querySelectorAll('.concept')].filter(e=>!e.hidden).map(e=>e.querySelector('h3').textContent),count:document.querySelector('#count').textContent,empty:!document.querySelector('#empty').hidden}));
    assert.equal(found.visible.length,expected,JSON.stringify({query,input:await page.$eval('#search',e=>e.value),found}));assert.equal(found.empty,expected===0);record.search.push({query,expected,...found});
   }
   for(const [domain,expected] of [['billing',1],['subscriptions',3],['',4]]){
    await page.select('#domain',domain);const found=await page.evaluate(()=>({visibleConcepts:[...document.querySelectorAll('.concept')].filter(e=>!e.hidden).map(e=>e.querySelector('h3').textContent),visibleDiagrams:[...document.querySelectorAll('.diagram')].filter(e=>!e.hidden).map(e=>e.querySelector('h2').textContent)}));
    assert.equal(found.visibleConcepts.length,expected);assert.equal(found.visibleDiagrams.length,domain?2:3);record.domains.push({domain,expected,...found});
   }
   await page.select('#domain','billing');await page.type('#search','Customer');assert.equal(await page.$eval('#count',e=>e.textContent),'0件の概念');await page.select('#domain','');await page.focus('#search');await page.keyboard.press('Home');await page.keyboard.down('Shift');await page.keyboard.press('End');await page.keyboard.up('Shift');await page.keyboard.press('Backspace');
   const evidence=await page.$('.concept details summary');await evidence.click();assert.equal(await page.$eval('.concept details',e=>e.open),true);assert.ok((await page.$eval('.concept details pre',e=>e.textContent)).includes('invoiceId'));await evidence.click();record.code_evidence=true;
   const buttons=await page.$$('.preview');
   for(let i=0;i<buttons.length;i++){
    await buttons[i].click();await page.waitForFunction(()=>document.querySelector('dialog').open&&document.querySelector('dialog img').complete&&document.querySelector('dialog img').naturalWidth>0);
    const zoom=await page.evaluate(()=>({open:document.querySelector('dialog').open,title:document.querySelector('dialog h2').textContent,width:document.querySelector('dialog img').naturalWidth,height:document.querySelector('dialog img').naturalHeight,scrollWidth:document.querySelector('.zoom').scrollWidth,clientWidth:document.querySelector('.zoom').clientWidth}));
    if(i===0)await page.screenshot({path:path.join(out,'screenshots',name+'-zoom.png')});
    if(zoom.scrollWidth>zoom.clientWidth){zoom.scrollLeft=await page.$eval('.zoom',e=>{e.scrollLeft=e.scrollWidth;return e.scrollLeft});assert.ok(zoom.scrollLeft>0);if(i===0)await page.screenshot({path:path.join(out,'screenshots',name+'-zoom-scrolled.png')});}
    if(i===1)await page.keyboard.press('Escape');else await page.click('#close');assert.equal(await page.$eval('dialog',e=>e.open),false);zoom.closed=true;record.zoom.push(zoom);
   }
   await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,'screenshots',name+'.png'),fullPage:true});
   if(name==='desktop'){
    const links=await page.$$('a[download]');
    for(const link of links){
     const filename=await link.evaluate(e=>e.download);await link.click();
     for(let n=0;n<100&&!fs.existsSync(path.join(out,'downloads',filename));n++)await new Promise(r=>setTimeout(r,20));
     const actual=fs.readFileSync(path.join(out,'downloads',filename)),original=fs.readFileSync(path.join(catalog,'diagrams',filename));assert.deepEqual(actual,original);result.downloads.push({file:filename,sha256:sha(actual),bytes:actual.length,actual_browser_download:true});
    }
   }
   result.viewports.push(record);
  }
  for(const name of fs.readdirSync(path.join(catalog,'diagrams')).filter(n=>n.endsWith('.png'))){
   await page.goto(pathToFileURL(path.join(catalog,'diagrams',name)).href,{waitUntil:'load'});
   const dimensions=await page.$eval('img',i=>({width:i.naturalWidth,height:i.naturalHeight,complete:i.complete}));assert.ok(dimensions.width>0&&dimensions.height>0&&dimensions.complete);result.png_opened.push({file:'diagrams/'+name,...dimensions});
  }
  assert.equal(result.errors.length,0);assert.equal(result.http_requests.length,0);result.status='passed';
 } finally {await browser.close();fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(result,null,2)+'\n')}
 console.log(JSON.stringify({status:result.status,viewports:result.viewports.length,png_opened:result.png_opened.length,downloads:result.downloads.length,errors:result.errors.length,http_requests:result.http_requests.length}));
})().catch(e=>{console.error(e);process.exit(1)});
