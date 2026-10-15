const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const handler = require('serve-handler');
const {loadSiteConfig} = require('@docusaurus/core/lib/server/config');

async function start() {
  const args = process.argv.slice(2);
  const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
  const host = option('--host', '127.0.0.1');
  const port = Number(option('--port', '3000'));
  const build = path.resolve('build');
  if (!fs.existsSync(path.join(build, 'index.html'))) throw new Error('npm run buildを先に実行してください');
  const {siteConfig: {baseUrl}} = await loadSiteConfig({siteDir: process.cwd()});
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, `http://${host}:${port}`);
    if (!url.pathname.startsWith(baseUrl)) {
      response.writeHead(302, {Location: baseUrl});
      response.end();
      return;
    }
    request.url = '/' + url.pathname.slice(baseUrl.length) + url.search;
    // HTML artifacts are files. Keep their extensions and bytes intact.
    handler(request, response, {
      public: build,
      cleanUrls: !url.pathname.endsWith('.html'),
      trailingSlash: undefined,
      directoryListing: false,
    }).catch(error => {
      console.error(error.message);
      if (!response.headersSent) response.writeHead(500);
      response.end();
    });
  });
  server.listen(port, host, () => console.log(`Preview: http://${host}:${server.address().port}${baseUrl}`));
}
start().catch(error => {console.error(error.message); process.exitCode = 1;});
