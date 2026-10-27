"""Mermaid 12をChrome CDP pipeで解析・描画する（STEP-03、OUT-02、OUT-04）。

出力: PNGと解析情報。外部接続・追加パッケージ・既存ブラウザプロファイルは使わない。
使用法: python3 render_diagram.py --source input.mmd --out diagram.png --mermaid /path/to/mermaid.min.js
終了コード: 0 成功、1 描画失敗、2 引数の誤り。POSIXとChromeを対象にする。
"""
import argparse
import base64
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time


class PipeChrome:
    """Dedicated Chrome process; NUL-delimited CDP messages over fd 3 and 4."""

    def __init__(self, browser, profile, log):
        if os.name != 'posix':
            raise ValueError('この描画経路はPOSIX専用です。Windowsは未対応です。')
        command_read, self.command_write = os.pipe()
        self.response_read, response_write = os.pipe()

        def connect():
            os.dup2(command_read, 3)
            os.dup2(response_write, 4)

        try:
            self.process = subprocess.Popen(
                [str(browser), '--headless=new', '--remote-debugging-pipe',
                 '--no-first-run', '--no-default-browser-check',
                 '--allow-file-access-from-files', '--disable-background-networking',
                 '--user-data-dir=' + str(profile), 'about:blank'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                pass_fds=tuple({3, 4, command_read, response_write}), preexec_fn=connect)
        except BaseException:
            for descriptor in (command_read, self.command_write, self.response_read, response_write):
                os.close(descriptor)
            raise
        os.close(command_read)
        os.close(response_write)
        self.buffer, self.sequence = b'', 0

    def call(self, method, params=None, session=None, timeout=30):
        self.sequence += 1
        message = {'id': self.sequence, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        wire = json.dumps(message, ensure_ascii=False).encode() + b'\0'
        offset = 0
        while offset < len(wire):
            offset += os.write(self.command_write, wire[offset:])
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while b'\0' in self.buffer:
                frame, self.buffer = self.buffer.split(b'\0', 1)
                if not frame:
                    continue
                result = json.loads(frame)
                if result.get('id') == self.sequence:
                    if 'error' in result:
                        raise ValueError('Chrome CDP: ' + str(result['error']))
                    return result.get('result', {})
            remaining = max(0, deadline - time.monotonic())
            if not select.select([self.response_read], [], [], remaining)[0]:
                break
            block = os.read(self.response_read, 1 << 20)
            if not block:
                raise ValueError('Chromeの起動または描画に失敗しました。ブラウザ実行権限を確認してください。exit=' + str(self.process.poll()))
            self.buffer += block
        raise ValueError('Chrome CDPが時間内に応答しませんでした: ' + method)

    def close(self):
        if self.process.poll() is None:
            try:
                self.call('Browser.close', timeout=2)
            except (OSError, ValueError):
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        os.close(self.command_write)
        os.close(self.response_read)


def resources(root, mermaid=None, browser=None):
    """Resolve an existing full Mermaid distribution and browser, without installing."""
    roots = [Path(root).resolve(), Path(__file__).resolve().parent]
    candidates = []
    if mermaid or os.environ.get('USECASE_MERMAID_JS'):
        candidates.append(Path(mermaid or os.environ['USECASE_MERMAID_JS']))
    for start in roots:
        for parent in [start, *start.parents]:
            candidates.append(parent / 'node_modules/mermaid/dist/mermaid.min.js')
    js = next((p.resolve() for p in candidates if p.is_file()), None)
    if not js:
        raise ValueError('既存のMermaid 12完全版が必要です。--mermaid または USECASE_MERMAID_JS でmermaid.min.jsを指定してください。')
    package = js.parent.parent / 'package.json'
    if not package.is_file():
        raise ValueError('Mermaidの版を確認できません。distとpackage.jsonを持つ配布物を指定してください。')
    version = json.loads(package.read_text(encoding='utf-8')).get('version', '')
    if version.split('.')[0] != '12':
        raise ValueError('検証対象はMermaid 12です。現在の版: ' + version)
    browsers = [browser, os.environ.get('USECASE_CHROME'),
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                shutil.which('google-chrome'), shutil.which('chromium'), shutil.which('chromium-browser')]
    chrome = next((Path(p).resolve() for p in browsers if p and Path(p).is_file()), None)
    if not chrome:
        raise ValueError('Chromeが必要です。--browser または USECASE_CHROME で実行ファイルを指定してください。')
    return {'mermaid': js, 'mermaid_version': version, 'browser': chrome}


PAGE = '''<!doctype html><meta charset="utf-8"><title>Use case renderer</title>
<style>html,body{margin:0;padding:0;background:white}#diagram{display:inline-block;margin:24px}svg{display:block;max-width:none!important}</style>
<div id="diagram"></div><script src="__MERMAID__"></script><script>
window.renderState={status:'loading'};
(async()=>{try{
const source=__SOURCE__;
mermaid.initialize({startOnLoad:false,theme:'default',look:'classic',layout:'elk',securityLevel:'strict',
 fontFamily:'Hiragino Sans, Noto Sans CJK JP, sans-serif',usecase:{useMaxWidth:false,nodeSpacing:70,rankSpacing:80}});
await mermaid.parse(source);
const d=await mermaid.mermaidAPI.getDiagramFromText(source);
if(d.type!=='usecase') throw Error('OUT-02 usecase-betaの原本が必要です');
const ast=d.db.getAST(), declarations={};
function walk(statements){for(const s of statements){
 for(const n of s.nodes||[]) if(n.defines) declarations[n.id]=(declarations[n.id]||0)+1;
 if(s.kind==='group') declarations[s.group]=(declarations[s.group]||0)+1;
 walk(s.children||[]);
}}
walk(ast.statements);
const metadata={actors:[...d.db.getActors().values()].map(x=>({id:x.id,label:x.label,parent:x.parentId||null})),
 usecases:[...d.db.getUseCases().values()].map(x=>({id:x.id,label:x.label,parent:x.parentId||null})),
 systems:[...d.db.getSystemBoundaries().values()].map(x=>({id:x.id,label:x.label,members:x.members})),
 relationships:d.db.getRelationships().map(x=>({source:x.source,target:x.target,type:x.type})),declarations};
if(!metadata.actors.length||!metadata.systems.length||!metadata.usecases.length) throw Error('OUT-02 アクター・境界・ユースケースを宣言してください');
if(metadata.actors.some(x=>x.parent)||metadata.usecases.some(x=>!x.parent)) throw Error('OUT-02 アクターは境界の外、ユースケースは境界の中に置いてください');
for(const x of [...metadata.actors,...metadata.usecases,...metadata.systems]){
 if((declarations[x.id]||0)>1) throw Error('OUT-04 宣言IDが重複しています: '+x.id);
 if(!declarations[x.id]) throw Error('OUT-02 全要素を明示宣言してください: '+x.id);
}
if(metadata.actors.length+metadata.usecases.length>40) throw Error('OUT-05 要素数の上限40を超えています');
const rendered=await mermaid.render('usecase',source);
document.getElementById('diagram').innerHTML=rendered.svg;
await document.fonts.ready;
const svg=document.querySelector('svg'),vb=svg.viewBox.baseVal;
svg.style.width=vb.width+'px';svg.style.height=vb.height+'px';
const r=document.getElementById('diagram').getBoundingClientRect();
window.renderState={status:'ready',width:Math.ceil(r.right+24),height:Math.ceil(r.bottom+24),metadata};
}catch(error){window.renderState={status:'error',error:String(error)}}})();
</script>'''


def render(source, png, environment, workspace):
    """Parse the original in the browser, then capture the complete SVG bounds."""
    png, workspace = Path(png), Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='chrome-', dir=workspace) as temporary:
        work = Path(temporary)
        page = PAGE.replace('__MERMAID__', environment['mermaid'].as_uri()).replace(
            '__SOURCE__', json.dumps(source, ensure_ascii=False).replace('<', '\\u003c'))
        (work / 'render.html').write_text(page, encoding='utf-8')
        with (work / 'chrome.log').open('wb') as log:
            chrome = PipeChrome(environment['browser'], work / 'profile', log)
            try:
                version = chrome.call('Browser.getVersion')['product']
                target = chrome.call('Target.createTarget', {'url': 'about:blank'})['targetId']
                session = chrome.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
                chrome.call('Page.enable', session=session)
                chrome.call('Network.enable', session=session)
                chrome.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*']}, session=session)
                chrome.call('Page.navigate', {'url': (work / 'render.html').as_uri()}, session=session)
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    result = chrome.call('Runtime.evaluate', {'expression': 'window.renderState||{status:"loading"}', 'returnByValue': True}, session=session)
                    state = result.get('result', {}).get('value', {'status': 'loading'})
                    if state['status'] == 'ready':
                        break
                    if state['status'] == 'error':
                        raise ValueError(state['error'])
                    time.sleep(.05)
                else:
                    raise ValueError('Mermaidの描画が完了しません。完全版mermaid.min.jsを確認してください。')
                width, height = state['width'], state['height']
                if not (0 < width <= 12000 and 0 < height <= 12000 and width * height <= 30000000):
                    raise ValueError('OUT-05 PNGの寸法または面積が上限を超えています。図を分割してください。')
                chrome.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': False}, session=session)
                shot = chrome.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True,
                    'clip': {'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1}}, session=session)
                png.write_bytes(base64.b64decode(shot['data'], validate=True))
                return {'width': width, 'height': height, 'model': state['metadata'],
                        'renderer': {'mermaid': environment['mermaid_version'], 'browser': version,
                                     'layout': 'elk', 'look': 'classic', 'theme': 'default', 'network': 'blocked'}}
            finally:
                chrome.close()


def preview(page_path, png, environment, workspace):
    """STEP-06: exercise the local HTML controls and capture its actual viewport."""
    with tempfile.TemporaryDirectory(prefix='preview-', dir=workspace) as temporary:
        work = Path(temporary)
        with (work / 'chrome.log').open('wb') as log:
            chrome = PipeChrome(environment['browser'], work / 'profile', log)
            try:
                target = chrome.call('Target.createTarget', {'url': 'about:blank'})['targetId']
                session = chrome.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
                chrome.call('Page.enable', session=session)
                chrome.call('Network.enable', session=session)
                chrome.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*']}, session=session)
                chrome.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False}, session=session)
                chrome.call('Page.navigate', {'url': Path(page_path).resolve().as_uri()}, session=session)
                for _ in range(100):
                    loaded = chrome.call('Runtime.evaluate', {'expression': 'document.readyState==="complete" && !!document.querySelector(".preview")', 'returnByValue': True}, session=session)
                    if loaded.get('result', {}).get('value'):
                        break
                    time.sleep(.05)
                else:
                    raise ValueError('STEP-06 HTMLを読み込めません。')
                expression = '''(async()=>{
                  await document.fonts.ready;
                  const images=[...document.querySelectorAll('.preview img')];
                  for(const img of images){img.loading='eager';await img.decode()}
                  const search=document.querySelector('#search');search.value='__no_matching_usecase__';
                  search.dispatchEvent(new Event('input'));
                  const searchEmpty=[...document.querySelectorAll('article')].every(x=>x.hidden)&&!document.querySelector('#empty').hidden;
                  search.value='';search.dispatchEvent(new Event('input'));
                  document.querySelector('.preview').click();
                  const dialogOpen=document.querySelector('#viewer').open;
                  document.querySelector('#close').click();
                  const dialogClosed=!document.querySelector('#viewer').open;
                  const details=document.querySelector('details');details.querySelector('summary').click();
                  const sourceShown=details.open&&details.querySelector('code').textContent.includes('usecase-beta');details.open=false;
                  const links=[...document.querySelectorAll('a[download]')].map(x=>x.getAttribute('href'));
                  return {cards:images.length,imagesValid:images.every(x=>x.naturalWidth>0),searchEmpty,dialogOpen,dialogClosed,sourceShown,
                   downloadLinks:links.length,localLinks:links.every(x=>!x.includes('://')&&!x.startsWith('/')),
                   noOverflow:document.documentElement.scrollWidth<=innerWidth};
                })()'''
                response = chrome.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True}, session=session)
                if response.get('exceptionDetails'):
                    raise ValueError('STEP-06 HTML操作テストが失敗しました: ' + str(response['exceptionDetails']))
                observed = response.get('result', {}).get('value', {})
                checks = ('imagesValid', 'searchEmpty', 'dialogOpen', 'dialogClosed', 'sourceShown', 'localLinks', 'noOverflow')
                if not observed.get('cards') or not all(observed.get(k) is True for k in checks):
                    raise ValueError('STEP-06 HTML操作の確認に失敗しました: ' + str(observed))
                shot = chrome.call('Page.captureScreenshot', {'format': 'png'}, session=session)
                Path(png).write_bytes(base64.b64decode(shot['data'], validate=True))
                return observed
            finally:
                chrome.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mermaid')
    parser.add_argument('--browser')
    args = parser.parse_args()
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='render-', dir=args.out.parent) as work:
            candidate = Path(work) / 'diagram.png'
            result = render(args.source.read_text(encoding='utf-8'), candidate, resources(Path.cwd(), args.mermaid, args.browser), work)
            os.replace(candidate, args.out)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('OUT-02 ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
