#!/bin/sh
# OUT-16: 既存のNode.jsとPuppeteerで、PNGの確認用一覧を生成する。追加取得はしない。
exec node - "$@" <<'CONTACT_SHEET_JS'
// 既存Mermaid CLIと同じPuppeteerを使い、PNGを4件ずつ一覧にする。
// 入力は同梱Pythonが作るJSON。外部ページへ移動せず、PNGのdata URLだけを描画する。
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');

async function main() {
  const cliRequire = createRequire(path.resolve(process.argv[2]));
  const imported = cliRequire('puppeteer');
  const puppeteer = imported.default || imported;
  const input = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const browser = await puppeteer.launch({...input.browser, headless:true});
  try {
    const page = await browser.newPage();
    await page.setViewport({width:3000,height:1,deviceScaleFactor:1});
    for (const sheet of input.sheets) {
      const body = sheet.items.map(item => `<article><h2>${escape(item.id)} · ${item.width} × ${item.height}</h2><img src="data:image/png;base64,${item.base64}" alt="${escape(item.id)}"></article>`).join('');
      await page.setContent(`<html><head><meta charset="utf-8"><style>body{margin:0;padding:24px;background:white;color:#152535;font:24px sans-serif}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:20px;border:2px solid #ccd3dc;min-width:0}h2{font-size:24px;margin:0 0 16px}img{display:block;max-width:100%;width:auto;height:auto;max-height:950px;margin:auto;object-fit:contain}</style></head><body><main>${body}</main></body></html>`);
      await page.evaluate(async () => {await Promise.all([...document.images].map(image => image.decode())); await document.fonts.ready;});
      await page.screenshot({path:sheet.output,fullPage:true});
    }
    await page.close();
  } finally {
    await browser.close();
  }
}
main().catch(error => {console.error(error.message);process.exitCode=1;});

CONTACT_SHEET_JS
