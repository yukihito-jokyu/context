// node check-browser.mjs <example-directory> [playwright-module-URL]
// CHROME_PATH optionally selects an existing Chrome; otherwise use Playwright's browser.
import path from 'node:path';
const {chromium} = await import(process.argv[3] || 'playwright');
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
if (!process.argv[2]) throw new Error('Provide the directory containing technical/ and general/ examples');
const root=path.resolve(process.argv[2]);
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
const checks=[];
try {
 for (const topic of ['technical','general']) {
  const context=await browser.newContext();const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const url=pathToFileURL(`${root}/${topic}/output.html`).href;
  const measurements=[];
  for (const width of [1440,390]) {
   await page.setViewportSize({width,height:900});
   for (const id of ['overview','scenario','detail','conditions','sources']) {
    await page.goto(url+'#'+id);await page.waitForTimeout(400);
    assert.equal(await page.locator('[data-page]:visible').count(),1);
    assert.equal(await page.locator(`[data-page]:visible`).getAttribute('id'),id);
    const metric=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyFont:getComputedStyle(document.body).fontSize,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length}));
    assert.ok(metric.scrollWidth<=width, `${topic}/${id}/${width}: overflow ${metric.scrollWidth}`);assert.equal(metric.bodyFont,'19px');assert.equal(metric.brokenImages,0);measurements.push({id,...metric});
   }
  }
  await page.setViewportSize({width:1440,height:900});
  await page.goto(url);await page.screenshot({path:`${root}/${topic}/preview.png`,fullPage:true});
  await page.locator('[data-page]:visible [data-diagram-zoom]').click();
  assert.equal(await page.locator('[data-page]:visible [data-zoomed]').count(),1);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('[data-page]:visible [data-diagram-zoom]').click();
  const anchors=await page.locator('a[href^="#"]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href').slice(1)));
  const ids=await page.locator('[id]').evaluateAll(nodes=>nodes.map(n=>n.id));
  assert.equal(new Set(ids).size,ids.length);assert.ok(anchors.every(id=>ids.includes(id)));
  await page.locator('.topic-nav a[href="#detail"]').click();await page.waitForTimeout(450);
  assert.equal(await page.locator('[data-page]:visible').getAttribute('id'),'detail');
  await page.goBack();await page.waitForTimeout(450);assert.equal(await page.locator('[data-page]:visible').getAttribute('id'),'overview');
  await page.goForward();await page.waitForTimeout(450);assert.equal(await page.locator('[data-page]:visible').getAttribute('id'),'detail');
  const deep=topic==='technical'?'before-line-2':'record-undefined';
  await page.goto(url+'#'+deep);assert.equal(await page.locator('[data-page]:visible').getAttribute('id'),'detail');
  assert.equal(await page.locator(topic==='technical'?'#configuration':'#record-notes').getAttribute('open'),'');
  await page.goto(url+'#scenario');
  await page.waitForFunction(() => !document.getElementById('scenario').hidden);
  await page.waitForTimeout(600);
  await page.screenshot({path:`${root}/${topic}/scenario-preview.png`,fullPage:true});
  await page.locator('[data-flow-action="play"]').click();await page.locator('[data-flow-action="play"]').click();
  await page.waitForTimeout(150);assert.equal(await page.locator('[data-flow-select][aria-current]').getAttribute('data-flow-select'),'1');
  const running=await page.locator('.trace-signal').evaluateAll(nodes=>nodes.flatMap(n=>n.getAnimations().map(a=>a.playState)));
  assert.ok(running.includes('running'));
  await page.locator('[data-flow-action="pause"]').click();await page.waitForTimeout(300);
  assert.equal(await page.locator('[data-flow-select][aria-current]').getAttribute('data-flow-select'),'1');
  const paused=await page.locator('.trace-signal').evaluateAll(nodes=>nodes.flatMap(n=>n.getAnimations().map(a=>a.playState)));assert.ok(paused.includes('paused'));
  await page.locator('[data-flow-action="play"]').click();await page.waitForTimeout(2600);
  assert.equal(await page.locator('[data-flow-select][aria-current]').getAttribute('data-flow-select'),'2');
  await page.locator('[data-flow-select="3"]').click();assert.equal(await page.locator('[data-flow-select][aria-current]').getAttribute('data-flow-select'),'3');
  assert.equal(await page.locator('li[data-flow-stage="3"].flow-active').count(),1);
  await page.locator('[data-flow-action="play"]').click();await page.waitForTimeout(2600);
  assert.equal(await page.locator('[data-flow-select][aria-current]').count(),0);assert.match(await page.locator('.flow-status').textContent(),/終了/);
  await page.locator('[data-flow-action="play"]').click();await page.locator('[data-flow-action="reset"]').click();assert.equal(await page.locator('[data-flow-select][aria-current]').count(),0);
  await page.locator('[data-flow-action="play"]').click();await page.locator('.topic-nav a[href="#detail"]').click();await page.waitForTimeout(300);
  assert.ok(!(await page.locator('.trace-signal').evaluateAll(nodes=>nodes.flatMap(n=>n.getAnimations().map(a=>a.playState)))).includes('running'));
  await page.goto(url);await page.evaluate(()=>{document.querySelector('.topic-nav a[href="#scenario"]').click();document.querySelector('.topic-nav a[href="#conditions"]').click()});await page.waitForTimeout(450);assert.equal(await page.locator('[data-page]:visible').getAttribute('id'),'conditions');
  await page.emulateMedia({reducedMotion:'reduce',colorScheme:'dark'});await page.goto(url+'#scenario');await page.locator('[data-flow-action="play"]').click();assert.equal(await page.locator('.trace-signal').evaluateAll(nodes=>nodes.reduce((count,n)=>count+n.getAnimations().length,0)),0);assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(250, 249, 246)');
  await page.emulateMedia({media:'print'});assert.equal(await page.locator('[data-page]:visible').count(),5);
  await page.evaluate(()=>dispatchEvent(new Event('beforeprint')));assert.equal(await page.locator('details:not([open])').count(),0);await page.evaluate(()=>dispatchEvent(new Event('afterprint')));
  assert.deepEqual(errors,[]);
  await context.close();
  const plain=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:900}});const staticPage=await plain.newPage();await staticPage.goto(url);assert.equal(await staticPage.locator('[data-page]:visible').count(),5);assert.equal(await staticPage.locator('.flow-controls:visible').count(),0);await plain.close();
  checks.push({topic,status:'passed',measurements,operations:['direct links on all pages','history back and forward','ancestor details opening','unique IDs and local anchors','double play','pause and resume','stage select synchronizes diagram and prose','finite end','reset','navigation pauses trace','last rapid navigation wins','reduced motion','light even under dark OS','print all pages and details','JavaScript disabled','diagram zoom preserves page width'],pageErrors:errors,visualReview:'pending'});
 }
 fs.writeFileSync(root+'/browser-validation.json',JSON.stringify({browser:'Google Chrome via Playwright, headless',checks},null,2)+'\n');console.log('Both example HTMLs passed browser checks');
} finally {await browser.close()}
