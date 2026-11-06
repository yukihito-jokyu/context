#!/usr/bin/env python3
"""Local before/after review. Approval is accepted only through this page's POST."""
from __future__ import annotations

import difflib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlencode, urlsplit

import feedback as fb
import _skillrt as rt

PAGE = r'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>成果物の修正前後を確認</title><style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#172630;background:#f3f6f5}*{box-sizing:border-box}body{margin:0}main{max-width:1320px;margin:0 auto;padding:36px 24px 80px}h1{font-size:30px;margin:0 0 12px}h2{font-size:21px}p{line-height:1.7}.lead{color:#51626b;max-width:850px}.top{display:flex;justify-content:space-between;gap:20px;align-items:center}.card{background:white;border:1px solid #d8e2de;border-radius:16px;padding:24px;margin-top:24px}.issue{white-space:pre-wrap;border-left:4px solid #477c68;padding:12px 18px;background:#f2f7f4}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}.version{min-width:0;border:1px solid #dce3e0;border-radius:10px;padding:16px}.version h3{margin:0 0 12px;font-size:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;font:13px/1.6 ui-monospace,monospace;background:#f5f7f7;padding:14px;border-radius:8px;max-height:520px;overflow:auto}.version img{max-width:100%;max-height:520px;object-fit:contain}.version iframe{width:100%;height:480px;border:1px solid #dce3e0;background:white}a{color:#20664f}button{border:0;border-radius:8px;padding:12px 18px;background:#246b50;color:white;font-size:15px;font-weight:600;cursor:pointer}button.secondary{background:#e4ece8;color:#245d48}button:disabled{opacity:.5;cursor:default}textarea{display:block;width:100%;max-width:760px;min-height:80px;padding:12px;border:1px solid #ccd9d3;border-radius:8px;font:inherit;margin:10px 0 16px}.badge{font-size:13px;background:#e7f2eb;color:#246b50;border-radius:20px;padding:6px 12px}.pending{background:#fff2d5;color:#8c641a}.meta{color:#65746d;font-size:13px;overflow-wrap:anywhere}.error{color:#a03030;white-space:pre-wrap}.notice{color:#246b50;font-weight:600}.diff{margin:14px 0}summary{cursor:pointer}footer{margin-top:32px;color:#65746d;font-size:13px}@media(max-width:760px){main{padding:24px 14px}.pair{grid-template-columns:1fr}.card{padding:16px}.top{align-items:flex-start}h1{font-size:25px}}
</style><main><div class="top"><div><h1>成果物の修正前後を確認</h1><p class="lead">指摘の原文と、修正前・修正後の実ファイルを確認できます。承認ボタンを押すと、表示した修正版を改善用の承認済み事例として保存します。</p></div><button class="secondary" id="reload">再読み込み</button></div><p id="notice" role="status"></p><div id="cases"></div><footer>会話の相づちや無回答を承認にはしません。修正版が変わった場合は、再読み込みして確認してください。</footer></main>
<script>
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
async function api(path,options){const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw Error(data.error||'読み込みに失敗しました');return data}
function artifact(parent,item){if(!item){parent.append(el('p','この版にはありません','meta'));return}parent.append(el('p',item.path,'meta'));const link=el('a','元のファイルを開く / ダウンロード');link.href=item.url+'&download=1';link.target='_blank';link.rel='noopener';parent.append(link);if(item.text!==null){parent.append(el('pre',item.text))}if(item.media_type.startsWith('image/')){const img=el('img');img.src=item.url;img.alt=item.path;parent.append(img)}else if(item.media_type==='text/html'||item.media_type==='application/pdf'){const frame=el('iframe');frame.src=item.url;frame.title=item.path;frame.setAttribute('sandbox','');parent.append(frame)}}
async function load(){try{const data=await api('/api/state');const root=document.getElementById('cases');root.replaceChildren();document.title=data.skill+' — 修正前後の確認';if(!data.cases.length)root.append(el('p','成果物への指摘はまだ記録されていません。'));for(const c of data.cases){const card=el('section',undefined,'card');const head=el('div',undefined,'top');head.append(el('h2',c.summary||'成果物への指摘'),el('span',c.status==='approved'?'承認済み':'確認待ち','badge '+(c.status==='approved'?'':'pending')));card.append(head,el('p',c.issue,'issue'),el('p','元の依頼: '+c.request),el('p','記録: '+c.id,'meta'));if(!c.after){card.append(el('p','修正版を作成・提示すると、ここに修正前後が表示されます。'));root.append(card);continue}for(const pair of c.files){const row=el('div',undefined,'pair');const before=el('div',undefined,'version');before.append(el('h3','修正前'));artifact(before,pair.before);const after=el('div',undefined,'version');after.append(el('h3','修正後'));artifact(after,pair.after);row.append(before,after);card.append(row);if(pair.diff){const detail=el('details',undefined,'diff');detail.append(el('summary','テキストの差分'),el('pre',pair.diff));card.append(detail)}}card.append(el('p','修正後の版: '+c.after+' / スキル版: '+c.skill_revision.slice(0,12),'meta'));if(c.status==='approved'){card.append(el('p','承認した記録: '+c.approval.text,'notice'))}else{const label=el('label','承認時のコメント（任意）');const notes=el('textarea');notes.setAttribute('aria-label','承認時のコメント');label.append(notes);const button=el('button','この修正版を承認する');const status=el('p',undefined,'error');button.onclick=async()=>{button.disabled=true;try{await api('/api/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:c.id,delivery:c.after,revision:c.revision,token:c.token,notes:notes.value})});document.getElementById('notice').textContent='承認を記録しました。';await load()}catch(error){status.textContent=error.message;button.disabled=false}};card.append(label,button,status)}root.append(card)}}catch(error){document.getElementById('notice').textContent=error.message;document.getElementById('notice').className='error'}}document.getElementById('reload').onclick=load;load();
</script></html>'''


def revision(case: dict) -> str:
    return fb.digest(json.dumps(case, sort_keys=True, ensure_ascii=False).encode())


def view(root: Path, contract: dict, tokens: dict) -> dict:
    with fb.locked(root, contract["skill"]) as (base, data):
        fb.validate(base, data)
        cards = []
        for case in data["cases"]:
            after_id = case["after"] or (case["revisions"][-1] if case["revisions"] else None)
            before = fb.delivery_by_id(data, case["before"])
            after = fb.delivery_by_id(data, after_id) if after_id else None
            def files(delivery):
                result = {}
                if delivery:
                    for n, item in enumerate(delivery["artifacts"]):
                        raw = fb.blob(base, item)
                        try:
                            text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            text = None
                        result[item["path"]] = {**item, "text": text,
                            "url": "/artifact?" + urlencode({"case": case["id"], "delivery": delivery["id"], "index": n})}
                return result
            old, new = files(before), files(after)
            pairs = []
            for path in sorted(set(old) | set(new)):
                left, right = old.get(path), new.get(path)
                diff = ""
                if left and right and left["text"] is not None and right["text"] is not None:
                    diff = "".join(difflib.unified_diff(left["text"].splitlines(True), right["text"].splitlines(True),
                                                       fromfile="修正前/" + path, tofile="修正後/" + path))
                pairs.append({"before": left, "after": right, "diff": diff})
            token = secrets.token_urlsafe(32)
            fingerprint = revision(case)
            tokens[case["id"]] = (token, fingerprint)
            cards.append({"id": case["id"], "summary": case["issue"]["summary"], "issue": case["issue"]["text"],
                          "request": case["request"], "status": case["status"], "before": before["id"], "after": after_id,
                          "files": pairs, "skill_revision": after["skill"]["revision"] if after else "",
                          "approval": case["approval"], "revision": fingerprint, "token": token})
        return {"skill": contract["skill"], "cases": cards}


def approve(root: Path, contract: dict, request: dict, tokens: dict) -> list[str]:
    case_id = request.get("case_id", "")
    expected = tokens.get(case_id)
    if not expected or not secrets.compare_digest(str(request.get("token", "")), expected[0]):
        raise fb.FeedbackError("確認画面を再読み込みしてから承認してください。")
    with fb.locked(root, contract["skill"]) as (base, data):
        fb.validate(base, data)
        case = next((c for c in data["cases"] if c["id"] == case_id), None)
        if (case is None or revision(case) != request.get("revision") or request.get("revision") != expected[1]
                or not case["revisions"] or case["revisions"][-1] != request.get("delivery")):
            raise fb.FeedbackError("確認中に修正版が変わりました。再読み込みして確認してください。")
        state = rt.load_state(root, contract["skill"])
        if state is None or not fb.same_session(fb.runtime(data, state), case["session_id"]):
            raise fb.FeedbackError("対応する実行の記録を確認できません。")
        notes = request.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 10000:
            raise fb.FeedbackError("承認コメントは10000文字以内にしてください。")
        message = {"id": fb.ident("response"), "event_id": fb.ident("review"), "at": rt.now(),
                   "platform": "review-ui", "source": "review-ui", "session_id": case["session_id"],
                   "text": notes.strip() or "この修正版を承認する", "delivery": request["delivery"],
                   "kind": "unclassified", "action": "approve", "case_id": case_id}
        # Append only after all checks succeed; rejected/stale requests are not approvals.
        result = fb.approve_record(root, state, contract, base, data, message)
        data["messages"].append(message)
        tokens.pop(case_id, None)
        return result


def make_server(root: Path, contract: dict, port: int = 0) -> ThreadingHTTPServer:
    tokens = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, content, content_type="application/json; charset=utf-8", download=False):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:") if self.path.startswith('/artifact') else None
            if download:
                self.send_header("Content-Disposition", "attachment")
            self.end_headers()
            self.wfile.write(content)

        def json(self, code, data):
            self.send(code, json.dumps(data, ensure_ascii=False).encode())

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                self.json(403, {"error": "Invalid host"})
                return
            try:
                route = urlsplit(self.path)
                if route.path == "/":
                    self.send(200, PAGE.encode(), "text/html; charset=utf-8")
                elif route.path == "/api/state":
                    self.json(200, view(root, contract, tokens))
                elif route.path == "/artifact":
                    query = parse_qs(route.query)
                    with fb.locked(root, contract["skill"]) as (base, data):
                        case = next(c for c in data["cases"] if c["id"] == query["case"][0])
                        delivery_id = query["delivery"][0]
                        if delivery_id not in [case["before"], *case["revisions"]]:
                            raise fb.FeedbackError("Invalid revision")
                        item = fb.delivery_by_id(data, delivery_id)["artifacts"][int(query["index"][0])]
                        content = fb.blob(base, item)
                        media = item["media_type"] if item["media_type"] in {"text/html", "application/pdf"} or item["media_type"].startswith("image/") else "text/plain; charset=utf-8"
                    self.send(200, content, media, "download" in query)
                else:
                    self.json(404, {"error": "Not found"})
            except (fb.FeedbackError, OSError, ValueError, KeyError, IndexError, StopIteration) as exc:
                self.json(400, {"error": str(exc)})

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self.valid_host() or self.headers.get("Origin") != origin or self.path != "/api/approve":
                self.json(403, {"error": "確認画面から送信してください。"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 20000:
                    raise fb.FeedbackError("Invalid request size")
                request = json.loads(self.rfile.read(length))
                self.json(200, {"approved": approve(root, contract, request, tokens)})
            except (fb.FeedbackError, OSError, KeyError, ValueError, TypeError) as exc:
                self.json(400, {"error": str(exc)})
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(root: Path, contract: dict, port: int = 0) -> None:
    with make_server(root, contract, port) as server:
        print(f"http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
