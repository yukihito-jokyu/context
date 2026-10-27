
const puppeteer = require(process.env.DOMAIN_MODEL_PUPPETEER || '/private/tmp/issue-86-tools/node_modules/puppeteer');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL, fileURLToPath} = require('node:url');
const crypto = require('node:crypto');
const root = path.resolve(process.argv[2] || __dirname);
const destination = path.resolve(process.argv[3] || __dirname);
const html = path.join(root, 'domain-models/sales/index.html');
const report = {schema_version:1, runner:'Puppeteer with installed Google Chrome', url:'domain-models/sales/index.html', started_at:new Date().toISOString(), viewports:[], external_requests:[], page_errors:[], console_errors:[], link_access:[], screenshots:[]};
const screenshots = {};
function ensure(value, message) { if(!value) throw new Error(message); }
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
let browser;
async function run() {
  browser = await puppeteer.launch({headless:true, executablePath:process.env.PUPPETEER_EXECUTABLE_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check']});
  report.browser_version = await browser.version();
  const page = await browser.newPage();
  page.on('pageerror', e => report.page_errors.push(String(e)));
  page.on('console', message => {if(message.type() === 'error') report.console_errors.push(message.text());});
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (/^https?:/i.test(request.url())) {report.external_requests.push(request.url()); request.abort();}
    else request.continue();
  });
  for(const viewport of [{name:'desktop', width:1440,height:1000,isMobile:false,hasTouch:false},{name:'mobile',width:390,height:844,isMobile:true,hasTouch:true}]) {
    await page.setViewport({width:viewport.width,height:viewport.height,isMobile:viewport.isMobile,hasTouch:viewport.hasTouch,deviceScaleFactor:1});
    await page.goto(pathToFileURL(html).href, {waitUntil:'networkidle0'});
    await page.waitForFunction(() => Array.from(document.querySelectorAll('.preview img')).every(el=>el.complete && el.naturalWidth>0));
    const entry = {viewport, all_diagrams:await page.$$eval('.card', cards=>cards.map(card=>({id:card.id,title:card.querySelector('h2').textContent,images_loaded:card.querySelector('img').naturalWidth>0}))), searches:[],diagrams:[], source_details:[], links:[],horizontal_overflow:[]};
    ensure(JSON.stringify(entry.all_diagrams.map(x=>x.id)) === JSON.stringify(['order','shipment']), 'all diagrams not present');
    async function overflow(stage) {
      const data = await page.evaluate(() => ({viewport:innerWidth,document_width:document.documentElement.scrollWidth,body_width:document.body.scrollWidth}));
      ensure(data.document_width<=data.viewport && data.body_width<=data.viewport,'document horizontal overflow: '+stage);
      entry.horizontal_overflow.push({stage,...data,passed:true});
    }
    await overflow('catalog');
    for (const query of ['顧客','配送','注文','顧客 注文','存在しない業務','']) {
      await page.$eval('#search', input=>{input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));});
      if(query) await page.type('#search',query);
      const result = await page.evaluate(() => ({count:document.querySelector('#count').textContent,visible:Array.from(document.querySelectorAll('.card')).filter(card=>!card.hidden).map(card=>card.id),empty_visible:!document.querySelector('#empty').hidden}));
      const expected = {'顧客':['order'],'配送':['shipment'],'注文':['order','shipment'],'顧客 注文':['order'],'存在しない業務':[],'':['order','shipment']}[query];
      ensure(JSON.stringify(result.visible) === JSON.stringify(expected),'search results incorrect for '+query);
      ensure(result.count === expected.length+'件のモデル','search count incorrect');
      ensure(result.empty_visible === (expected.length===0),'empty state incorrect');
      entry.searches.push({query,...result,passed:true});
    }
    for(const id of ['order','shipment']) {
      await page.click('#'+id+' summary');
      const source = await page.$eval('#'+id+' details', el=>({open:el.open,path:el.querySelector('code').textContent,quote:el.querySelector('blockquote').textContent}));
      ensure(source.open && source.path.startsWith('input.md:') && source.quote.length>0,'source details incorrect');
      entry.source_details.push({id,...source,passed:true});
      await overflow('source-'+id);
      await page.click('#'+id+' summary');
      for(const kind of ['mmd','png']) {
        const selector = '#'+id+' a[href$=".'+kind+'"]';
        const link = await page.$eval(selector, el=>({text:el.textContent,href:el.getAttribute('href'),url:el.href,download:el.hasAttribute('download')}));
        ensure(link.download,'download attribute missing');
        const file = fileURLToPath(link.url);
        ensure(fs.existsSync(file) && fs.statSync(file).size>0,'link file missing');
        const expected = kind==='mmd' ? 'diagrams/'+id+'.mmd':'images/'+id+'.png';
        ensure(link.href===expected, 'link target incorrect');
        entry.links.push({id,kind,href:link.href,download:link.download,bytes:fs.statSync(file).size,sha256:sha(fs.readFileSync(file)),passed:true});
      }
      const selector='#'+id+' .actions .open-diagram';
      await page.click(selector);
      await page.waitForFunction(() => document.querySelector('#viewer').open && document.querySelector('#zoom-image').complete && document.querySelector('#zoom-image').naturalWidth>0);
      const initial = await page.evaluate(() => ({open:document.querySelector('#viewer').open,title:document.querySelector('#viewer-title').textContent,alt:document.querySelector('#zoom-image').alt,src:document.querySelector('#zoom-image').getAttribute('src'),label:document.querySelector('#zoom-label').textContent,width:document.querySelector('#zoom-image').getBoundingClientRect().width,focus_in_dialog:document.querySelector('#viewer').contains(document.activeElement)}));
      ensure(initial.open && initial.src==='images/'+id+'.png' && initial.label==='100%' && initial.focus_in_dialog,'modal initial state incorrect');
      await overflow('modal-'+id);
      await page.click('#zoom-in');
      const enlarged = await page.$eval('#zoom-image',el=>({width:el.getBoundingClientRect().width,style:el.style.width}));
      ensure(enlarged.width>initial.width && enlarged.style==='125%', 'zoom in incorrect');
      await page.click('#zoom-out');
      ensure(await page.$eval('#zoom-label',el=>el.textContent)==='100%','zoom out incorrect');
      await page.click('#zoom-out');
      const reduced = await page.$eval('#zoom-image',el=>({width:el.getBoundingClientRect().width,style:el.style.width}));
      ensure(reduced.width<initial.width && reduced.style==='75%','zoom reduction incorrect');
      await page.click('#zoom-reset');
      ensure(await page.$eval('#zoom-label',el=>el.textContent)==='100%','zoom reset incorrect');
      await page.keyboard.press('Escape');
      await page.waitForFunction(()=>!document.querySelector('#viewer').open);
      const escaped=await page.$eval(selector,el=>document.activeElement===el);
      ensure(escaped,'focus did not return after Escape');
      const previewSelector='#'+id+' .preview .open-diagram';
      await page.click(previewSelector);
      await page.waitForFunction(()=>document.querySelector('#viewer').open);
      await page.click('#close');
      await page.waitForFunction(()=>!document.querySelector('#viewer').open);
      const closed=await page.$eval(previewSelector,el=>document.activeElement===el);
      ensure(closed,'focus did not return after close');
      entry.diagrams.push({id,initial,enlarged,reduced,zoom_reset:'100%',escape_closed:true,escape_restored_focus:escaped,close_button_closed:true,close_restored_focus:closed,passed:true});
    }
    await page.evaluate(()=>scrollTo(0,0));
    const imageName = viewport.name==='desktop'?'preview.png':'mobile.png';
    screenshots[imageName]=await page.screenshot({fullPage:true,type:'png'});
    report.screenshots.push({file:imageName,viewport:viewport.name,full_page:true});
    
    entry.link_access = [];
    for (const id of ['order','shipment']) {
      for (const kind of ['mmd','png']) {
        await page.goto(pathToFileURL(html).href,{waitUntil:'load'});
        const selector='#'+id+' a[href$=".'+kind+'"]';
        const relative=(kind==='mmd'?'diagrams/':'images/')+id+'.'+kind;
        const expected=path.join(root,'domain-models/sales',relative);
        const [response]=await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.click(selector)]);
        ensure(fileURLToPath(page.url())===expected,'link did not open the expected file');
        let observed;
        if (kind==='mmd') {
          observed=await page.evaluate(()=>document.body.textContent);
          ensure(observed===fs.readFileSync(expected,'utf8'),'opened Mermaid does not match the original');
        } else {
          await page.waitForFunction(()=>document.images.length===1 && document.images[0].complete && document.images[0].naturalWidth>0);
          observed=await page.evaluate(()=>({width:document.images[0].naturalWidth,height:document.images[0].naturalHeight}));
          const receipt=JSON.parse(fs.readFileSync(path.join(root,'domain-models/sales/validation.json'),'utf8')).images[id];
          ensure(observed.width===receipt.width && observed.height===receipt.height,'opened PNG dimensions differ');
        }
        entry.link_access.push({id,kind,href:relative,actual_browser_click:true,result:'file://で原本または画像を開いて取得できることを確認',content_matches:kind==='mmd'?true:undefined,dimensions:kind==='png'?observed:undefined,sha256:sha(fs.readFileSync(expected)),passed:true});
      }
    }
    report.viewports.push(entry);

  }
  ensure(report.external_requests.length===0,'external requests detected');
  ensure(report.page_errors.length===0 && report.console_errors.length===0,'JavaScript or console errors detected');
  fs.mkdirSync(destination,{recursive:true});
  for(const [file,data] of Object.entries(screenshots)) fs.writeFileSync(path.join(destination,file),data);
  report.finished_at=new Date().toISOString();
  report.status='passed';
  report.file_protocol_behavior='Chromeのfile://閲覧ではdownload属性付きリンクを押すと原本やPNGの表示に遷移した。各リンクを実際に押し、原本本文またはPNG寸法とハッシュの一致を確認した。保存ダイアログの強制は検証していない。';
  report.unverified=['この使い捨てプロジェクトに登録したhooksのセッションでの信頼と自動発火は確認していない。run.py checkとfinishを明示実行した。','既存カタログの更新と別ブラウザでの動作は、この新規2図の公開例では検証していない。'];
  fs.writeFileSync(path.join(destination,'ui-validation.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({phase:'saved',status:report.status,links_opened:report.viewports.reduce((total,viewport)=>total+viewport.link_access.length,0),files:[...Object.keys(screenshots),'ui-validation.json'],external_requests:report.external_requests.length,page_errors:report.page_errors.length,console_errors:report.console_errors.length}));
  await browser.close();
}
run().catch(async error=>{console.error(error.stack);if(browser)await browser.close();process.exitCode=1;});

