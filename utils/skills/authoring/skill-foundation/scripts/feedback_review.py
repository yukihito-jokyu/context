#!/usr/bin/env python3
"""修正前後の確認画面のサーバー。feedback.py review が起動する。skill-foundation の共通ランタイム（スキルごとに書き換えない）。

127.0.0.1 だけで待ち受け、指摘ごとに、修正前の版といちばん新しい修正版の実ファイルを並べる（テキストは差分と本文、
HTML はスクリプトを止めたプレビュー、画像は画像、PDF などは実ファイル）。ユーザーが「この修正版を承認する」を押すと、
feedback.json の指摘に承認を書く。承認はこの画面のボタンでだけ受け付ける。

承認の検査（どれかに当たれば拒否し、画面を開き直すよう伝える）:
  - 送信元（Origin・Host）がこのサーバーでない
  - トークンが、この指摘の画面を最後に開いたときに発行したものでない（古い画面。トークンは一回限り）
  - 承認する版が、画面に出した版でない、またはいちばん新しい修正版でない（別の版）
  - 画面を開いた後に、プロジェクトの実ファイルが表示した版から変わった

操作が --idle 分無いと止まる。使い方:
  python3 <skill>/scripts/feedback_review.py --root <プロジェクト> [--port 0] [--idle 30]
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import html
import json
import mimetypes
import os
import secrets
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402
import feedback as fb  # noqa: E402

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif"}
PAGES = {".html", ".htm"}
DIFF_LINES = 2000
PLATFORMS = {"claude": "Claude Code", "codex": "Codex"}

T = {
    "ja": {
        "lang": "ja", "title": "修正前後の確認", "theme": ("表示の色", "自動", "明るい", "暗い"),
        "lead": "指摘を受けて直した成果物を、直す前と比べて確かめる画面です。納得できたら、いちばん下の「この修正版を承認する」を押してください。"
                "承認はこの画面のボタンでだけ記録されます。会話で「OK」と伝えただけでは記録されません。",
        "nav": "指摘 {n} 件", "nav_none": "まだありません", "nav_label": "指摘の一覧",
        "pending": "承認待ち", "norev": "修正版待ち", "approved": "承認済み", "revs": "修正版 {n}",
        "issue": "指摘", "issue_lead": "あなたが成果物に対して言ったことの原文です。AI の要約で置き換えずに残しています。",
        "seen": "見ていた版", "summary": "AI の要点（参考）",
        "flow": "版の流れ", "flow_lead": "指摘を受けた版（修正前）と、いちばん新しい修正版を比べます。",
        "before": "修正前", "revision": "修正版", "after": "修正後", "comparing": "比べている版", "no_rev_yet": "修正版はまだありません",
        "trigger": {"finish": "完了したとき", "revision": "直したとき"},
        "files": "ファイル {n} 件（変わった {c}・同じ {s}）", "files_lead": "修正前と修正後の実際のファイルを並べます。",
        "files_norev": "修正版ができると、ここに直す前と後のファイルが並びます。今の修正前のファイル:",
        "chg": {"mod": "変わった", "add": "足した", "del": "消した", "same": "同じ"},
        "kind": {"text": "テキスト", "html": "HTML（スクリプトを止めて表示）", "image": "画像",
                 "other": "{ext}（画面では比べられないので実ファイルを開く）"},
        "tabs": ("差分", "修正後", "修正前"), "html_src": "HTML の差分を見る", "open": "{w}のファイルを開く ↗",
        "missing": "（このファイルは無い）", "same_files": "変わっていないファイル {n} 件", "cut": "… 長いので {n} 行で切った",
        "approve": "承認", "approve_lead": "承認すると、修正版 {d} を、この指摘（{c}）への対応として記録します。"
                                         "直っていなければ承認せず、会話で AI に伝えてください。",
        "comment": "コメント（任意。承認と一緒に残る）", "comment_ph": "例: これでよい", "button": "この修正版を承認する",
        "local": "この画面は、あなたのパソコンの中（127.0.0.1）だけで開いています。",
        "norev_lead": "まだ修正版がありません。AI が直すと、ここで承認できるようになります。",
        "done_head": "承認済み（{at}）", "done_body": "修正版 {d} を、この指摘への対応として記録しました。",
        "done_comment": "コメント: {c}", "done_note": "この指摘は承認で閉じました。新しい指摘は、会話で AI に伝えると別の指摘として記録されます。",
        "reject_head": "承認できませんでした", "reload": "画面を開き直す",
        "empty_head": "確かめる指摘はまだありません", "empty_body": "スキルの成果物に指摘をして、AI が直すと、ここに直す前と後が並びます。",
        "err_origin": "この画面以外から送られた承認なので、記録しませんでした。",
        "err_token": "古い画面からの承認です（この後に同じ指摘の画面が開かれたか、サーバーが起動し直した）。",
        "err_version": "画面に出した版と、承認しようとした版が違います。",
        "err_newer": "この画面を開いた後に、新しい修正版 {d} ができました。",
        "err_changed": "この画面を開いた後に、{files} が変わりました。",
        "err_done": "この指摘は既に承認済みです。", "err_norev": "修正版がまだありません。", "err_case": "指摘 {c} がありません。",
        "err_tail": "画面を開き直して、今の内容を確かめてから承認してください。",
        "ok": "承認を記録しました。",
    },
    "en": {
        "lang": "en", "title": "Review the fix", "theme": ("Color", "Auto", "Light", "Dark"),
        "lead": "Compare the outputs fixed after your feedback with the version before the fix. If you are satisfied, press "
                "\"Approve this fix\" at the bottom. Only the button on this page records an approval; saying \"OK\" in the conversation does not.",
        "nav": "{n} feedback item(s)", "nav_none": "None yet", "nav_label": "Feedback",
        "pending": "Awaiting approval", "norev": "Awaiting a fix", "approved": "Approved", "revs": "{n} fix(es)",
        "issue": "Feedback", "issue_lead": "What you said about the outputs, word for word. It is kept as is, not replaced by an AI summary.",
        "seen": "Version you saw", "summary": "AI gist (reference)",
        "flow": "Versions", "flow_lead": "The version that received the feedback (before) is compared with the newest fix.",
        "before": "Before", "revision": "Fix", "after": "After", "comparing": "compared", "no_rev_yet": "No fix yet",
        "trigger": {"finish": "on finish", "revision": "after a fix"},
        "files": "{n} file(s) ({c} changed, {s} unchanged)", "files_lead": "The actual files before and after the fix, side by side.",
        "files_norev": "Once there is a fix, the files before and after appear here. Files before the fix:",
        "chg": {"mod": "changed", "add": "added", "del": "deleted", "same": "unchanged"},
        "kind": {"text": "Text", "html": "HTML (scripts disabled)", "image": "Image",
                 "other": "{ext} (open the actual file; it cannot be compared here)"},
        "tabs": ("Diff", "After", "Before"), "html_src": "Show the HTML diff", "open": "Open the file {w} ↗",
        "missing": "(no such file)", "same_files": "{n} unchanged file(s)", "cut": "… cut at {n} lines",
        "approve": "Approve", "approve_lead": "Approving records fix {d} as the answer to this feedback ({c}). "
                                            "If it is not fixed, do not approve; tell the AI in the conversation instead.",
        "comment": "Comment (optional; kept with the approval)", "comment_ph": "e.g. Looks good", "button": "Approve this fix",
        "local": "This page is served only on your computer (127.0.0.1).",
        "norev_lead": "There is no fix yet. Once the AI fixes the outputs, you can approve it here.",
        "done_head": "Approved ({at})", "done_body": "Fix {d} was recorded as the answer to this feedback.",
        "done_comment": "Comment: {c}", "done_note": "This feedback is closed. New feedback in the conversation is recorded as a separate item.",
        "reject_head": "The approval was not recorded", "reload": "Reload the page",
        "empty_head": "Nothing to review yet", "empty_body": "When you give feedback on the skill's outputs and the AI fixes them, the versions appear here.",
        "err_origin": "The approval did not come from this page, so it was not recorded.",
        "err_token": "The approval came from an old page (the same feedback was opened again later, or the server restarted).",
        "err_version": "The version you tried to approve is not the version shown on the page.",
        "err_newer": "A newer fix {d} was made after this page was opened.",
        "err_changed": "{files} changed after this page was opened.",
        "err_done": "This feedback is already approved.", "err_norev": "There is no fix yet.", "err_case": "There is no feedback {c}.",
        "err_tail": "Reload the page, check the current content, and approve again.",
        "ok": "The approval was recorded. ",
    },
}

DARK = ("--bg:#191814;--panel:#201f1c;--sunken:#2a2925;--ink:#ede9df;--ink-2:#bdb7a9;--muted:#948e80;"
        "--line:#34322d;--line-2:#4a473f;--grid-dot:rgba(237,233,223,.06);"
        "--accent:#d97757;--accent-ink:#eb9877;--accent-soft:rgba(217,119,87,.15);--on-accent:#1b1a17;"
        "--good:#22b322;--good-ink:#62d062;--good-soft:rgba(34,179,34,.13);--warn:#fab219;--warn-ink:#f6c453;--warn-soft:rgba(250,178,25,.12);"
        "--crit:#e05252;--crit-ink:#f28a8a;--crit-soft:rgba(224,82,82,.15);")
LIGHT = ("--bg:#f6f5f1;--panel:#ffffff;--sunken:#efede7;--ink:#1f1e1b;--ink-2:#504d45;--muted:#706c62;"
         "--line:#e4e1d8;--line-2:#cdc9bd;--grid-dot:rgba(31,30,27,.08);"
         "--accent:#c6613f;--accent-ink:#a84f30;--accent-soft:#f8e7e0;--on-accent:#ffffff;"
         "--good:#0ca30c;--good-ink:#087a08;--good-soft:#e3f4e3;--warn:#fab219;--warn-ink:#875800;--warn-soft:#fdf1d6;"
         "--crit:#d03b3b;--crit-ink:#b02b2b;--crit-soft:#fbe6e6;")
FONTS = "https://fonts.googleapis.com/css2?family=DotGothic16&family=JetBrains+Mono:wght@400;700&display=swap"
# 見た目は catalog.py のカタログに揃える（2026-11-04 にユーザーが承認した案。issue #7 の作業2）
CSS = """
:root{""" + DARK + """color-scheme:dark;
--mono:"JetBrains Mono","SF Mono",Menlo,Consolas,"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic UI",Meiryo,monospace;
--display:"DotGothic16","JetBrains Mono","SF Mono",Menlo,"Hiragino Sans","Noto Sans JP",monospace}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){""" + LIGHT + """color-scheme:light}}
:root[data-theme="light"]{""" + LIGHT + """color-scheme:light}
:root[data-theme="dark"]{""" + DARK + """color-scheme:dark}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background-color:var(--bg);background-image:radial-gradient(var(--grid-dot) 1px,transparent 1.5px);background-size:20px 20px;
color:var(--ink);font:15px/1.8 var(--mono);-webkit-font-smoothing:antialiased}
a{color:var(--accent-ink)}code{font-family:var(--mono);font-size:.93em;background:var(--sunken);padding:1px 6px;border-radius:4px}
:focus-visible{outline:2px dashed var(--accent);outline-offset:2px}
.page{max-width:1240px;margin:0 auto;padding:28px 16px 64px;display:grid;gap:22px}
.top{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 22px;align-items:start;padding:20px 22px;border:1px solid var(--accent);border-radius:10px;background:var(--panel)}
.eyebrow{margin:0;font-size:13px;letter-spacing:.06em;color:var(--accent-ink);font-weight:700}.eyebrow::before{content:"✻ "}
.top h1{margin:2px 0 0;font:400 26px/1.3 var(--display);letter-spacing:.04em;overflow-wrap:anywhere}
.top .lead{margin:8px 0 0;color:var(--ink-2);max-width:78ch;font-size:14px}
.theme{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line-2);border-radius:6px;background:var(--bg)}
.theme button{font:inherit;font-size:13px;padding:4px 12px;border:0;border-radius:4px;background:none;color:var(--ink-2);cursor:pointer}
.theme button[aria-pressed="true"]{background:var(--accent);color:var(--on-accent);font-weight:700}
.layout{display:grid;grid-template-columns:280px minmax(0,1fr);gap:22px;align-items:start}
.cases{position:sticky;top:16px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 12px}
.cases h2{margin:0 6px 10px;font-size:14px}
.cases ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.cases a{display:grid;gap:2px;padding:10px 12px;border-radius:6px;color:var(--ink);text-decoration:none}
.cases a:hover{background:var(--sunken)}.cases a[aria-current="page"]{background:var(--sunken);box-shadow:inset 3px 0 0 var(--accent)}
.cases .q{font-size:13.5px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.cases small{font-size:12.5px;color:var(--muted)}
.main{display:grid;gap:18px;min-width:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px 22px;min-width:0}
.card h3{margin:0 0 10px;font-size:16px;line-height:1.5;display:flex;align-items:center;gap:10px}
.card h3::before{content:"";width:8px;height:8px;flex:none;background:var(--accent)}
.card .lead{margin:0 0 12px;color:var(--ink-2);font-size:14px}
.st{display:inline-flex;gap:6px;align-items:center;font-size:13px;font-weight:700;white-space:nowrap;color:var(--ink-2)}
.st i{width:8px;height:8px;border-radius:50%;flex:none;background:var(--muted)}
.st.warn{color:var(--warn-ink)}.st.warn i{background:var(--warn)}.st.good{color:var(--good-ink)}.st.good i{background:var(--good)}
.st.mute i{background:var(--line-2)}
blockquote{margin:0 0 10px;padding:10px 16px;border-left:3px solid var(--accent);background:var(--sunken);border-radius:0 6px 6px 0;white-space:pre-wrap;overflow-wrap:anywhere}
blockquote footer{margin-top:4px;font-size:12.5px;color:var(--muted);white-space:normal}
.sum{margin:0;font-size:13.5px;color:var(--ink-2)}.sum b{color:var(--muted);font-weight:700;margin-right:8px}
.flow{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px 6px;align-items:center}
.flow li{display:grid;padding:6px 12px;border:1px solid var(--line-2);border-radius:6px;font-size:13.5px;line-height:1.5}
.flow li small{font-size:12px;color:var(--muted)}
.flow li.cmp{border-color:var(--accent);background:var(--accent-soft)}
.flow .arrow{border:0;padding:0;color:var(--muted)}
.file{border-top:1px dashed var(--line);padding:14px 0 6px}.file:first-of-type{border-top:0;padding-top:4px}
.fhead{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;margin-bottom:8px}
.fhead code{font-weight:700;overflow-wrap:anywhere}
.kind{font-size:12.5px;color:var(--muted)}
.chg{font-size:12.5px;font-weight:700;padding:0 8px;border-radius:4px}
.chg.mod{color:var(--warn-ink);background:var(--warn-soft)}.chg.add{color:var(--good-ink);background:var(--good-soft)}
.chg.del{color:var(--crit-ink);background:var(--crit-soft)}.chg.same{color:var(--muted);background:var(--sunken)}
.tabs{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line-2);border-radius:6px;background:var(--bg);margin-bottom:8px}
.tabs button{font:inherit;font-size:13px;padding:2px 12px;border:0;border-radius:4px;background:none;color:var(--ink-2);cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--accent);color:var(--on-accent);font-weight:700}
pre{margin:0;padding:10px 12px;background:var(--bg);border:1px solid var(--line);border-radius:6px;font-size:13px;line-height:1.55;overflow:auto;max-height:420px}
.diff span{display:block;white-space:pre}.diff .add{color:var(--good-ink);background:var(--good-soft)}
.diff .del{color:var(--crit-ink);background:var(--crit-soft)}.diff .hunk{color:var(--muted)}
.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.pair figure{margin:0;display:grid;gap:6px;min-width:0;align-content:start}
.pair figcaption{font-size:12.5px;color:var(--muted);font-weight:700}
.pair iframe{width:100%;height:260px;border:1px solid var(--line);border-radius:6px;background:#fff}
.pair img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:var(--bg)}
.open{display:inline-flex;gap:8px;align-items:center;padding:8px 12px;border:1px solid var(--line-2);border-radius:6px;font-size:13.5px;text-decoration:none;color:var(--ink)}
.open:hover{border-color:var(--accent)}
details.src{margin-top:8px}details.src summary{cursor:pointer;font-size:13px;color:var(--ink-2)}
details.same summary{cursor:pointer;font-size:13.5px;color:var(--ink-2);padding-top:10px}
.plain{margin:0;padding-left:1.2em}
.approve{border-color:var(--accent)}
.approve label{display:grid;gap:6px;font-size:13.5px;font-weight:700;margin:4px 0 12px}
.approve textarea{font:inherit;font-size:14px;min-height:76px;padding:8px 10px;border:1px solid var(--line-2);border-radius:6px;background:var(--bg);color:var(--ink);resize:vertical}
.approve textarea:focus{outline:none;border-color:var(--accent)}
.actions{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}
.primary{display:inline-block;font:inherit;font-weight:700;font-size:14.5px;padding:9px 18px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:var(--on-accent);cursor:pointer;text-decoration:none}
.primary:hover{filter:brightness(1.06)}.primary:disabled{opacity:.45;cursor:not-allowed;filter:none}
.note{font-size:13px;color:var(--muted)}
.box{padding:12px 16px;border-radius:6px;margin:0 0 12px;font-size:14px;overflow-wrap:anywhere}
.box.good{background:var(--good-soft);border:1px solid var(--good);color:var(--ink)}
.box.crit{background:var(--crit-soft);border:1px solid var(--crit);color:var(--ink)}
.box b{display:block;margin-bottom:2px}
.empty{text-align:center;padding:48px 22px;color:var(--ink-2)}.empty h3{justify-content:center}
@media (max-width:860px){.top,.layout{grid-template-columns:minmax(0,1fr)}.theme{justify-self:start}.cases{position:static}.pair{grid-template-columns:minmax(0,1fr)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""
JS = """
const root=document.documentElement;
const pick=t=>{document.querySelectorAll('.theme button').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.theme===t)));
 if(t==='auto')root.removeAttribute('data-theme');else root.dataset.theme=t;try{localStorage.setItem('fb-theme',t)}catch(e){}};
try{const t=localStorage.getItem('fb-theme');if(t)pick(t)}catch(e){}
document.querySelectorAll('.theme button').forEach(b=>b.addEventListener('click',()=>pick(b.dataset.theme)));
document.querySelectorAll('.tabs').forEach(t=>t.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;const f=t.closest('.file');
 t.querySelectorAll('button').forEach(x=>x.setAttribute('aria-selected',String(x===b)));
 f.querySelectorAll('[data-view]').forEach(v=>v.hidden=v.dataset.view!==b.dataset.view);}));
"""

esc = html.escape


def when(at: str | None) -> str:
    try:
        return datetime.datetime.fromisoformat(at).strftime("%m/%d %H:%M")
    except (TypeError, ValueError):
        return at or ""


def size_text(n: int) -> str:
    return f"{n} B" if n < 1024 else f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def kind_of(entry: dict | None) -> str:
    ext = Path((entry or {}).get("path", "")).suffix.lower()
    if ext in IMAGES:
        return "image"
    if ext in PAGES and not (entry or {}).get("binary"):
        return "html"
    return "other" if (entry or {}).get("binary") else "text"


class Review:
    """画面の組み立てと承認の検査。トークンはサーバーのメモリにだけ置く（起動し直すと古い画面は承認できない）。"""

    def __init__(self, root: Path, contract: dict, port: int):
        self.root, self.contract, self.port = root, contract, port
        self.name = contract.get("skill") or rt.SKILL_DIR.name
        self.t = T.get(contract.get("language"), T["ja"])
        self.server_id = secrets.token_hex(8)
        self.tokens: dict[str, dict] = {}
        self.guard = threading.Lock()
        self.last = time.time()

    @property
    def origins(self) -> set[str]:
        return {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"}

    def text(self, store: dict, sha: str | None) -> str:
        if not sha:
            return ""
        path = fb.object_path(self.root, self.name, sha)
        return path.read_bytes().decode("utf-8", errors="replace") if path.is_file() else ""

    def label(self, case: dict, delivery_id: str) -> str:
        return f"{self.t['before'] if delivery_id == case['before'] else self.t['revision']} {delivery_id}"

    # ------------------------------------------------------------ 画面

    def page(self, case_id: str | None = None, error: str | None = None, comment: str = "", notice: str | None = None) -> str:
        with fb.locked(self.root, self.name):
            store = fb.load(self.root, self.name)
            if fb.revise(store, self.root, rt.load_state(self.root, self.name), self.contract, "review", None):
                fb.save(self.root, store)  # 画面を開いた時点の実ファイルを、修正版として先に記録する
        # 対応中を上に、それぞれ新しい順
        cases = [c for c in store["cases"] if c["status"] == "open"][::-1] + [c for c in store["cases"] if c["status"] != "open"][::-1]
        case = fb.find(store["cases"], case_id) if case_id else (cases[0] if cases else None)
        t = self.t
        head = (f'<header class="top"><div><p class="eyebrow">{esc(t["title"])}</p><h1>{esc(self.name)}</h1>'
                f'<p class="lead">{esc(t["lead"])}</p></div><div class="theme" role="group" aria-label="{esc(t["theme"][0])}">'
                + "".join(f'<button type="button" data-theme="{k}" aria-pressed="{str(k == "auto").lower()}">{esc(v)}</button>'
                          for k, v in zip(("auto", "light", "dark"), t["theme"][1:])) + "</div></header>")
        nav = self.nav(store, cases, case)
        if case is None:
            main = (f'<div class="main"><section class="card empty"><h3>{esc(t["empty_head"])}</h3>'
                    f'<p>{esc(t["empty_body"])}</p></section></div>')
        else:
            main = ('<div class="main">' + self.issue(store, case) + self.flow(store, case) + self.files(store, case)
                    + self.approve(store, case, error, comment, notice) + "</div>")
        return self.wrap(head + f'<div class="layout">{nav}{main}</div>')

    def nav(self, store: dict, cases: list[dict], current: dict | None) -> str:
        t = self.t
        if not cases:
            return (f'<nav class="cases" aria-label="{esc(t["nav_label"])}"><h2>{esc(t["nav"].replace("{n}", "0"))}</h2>'
                    f'<p class="note" style="margin:0 6px">{esc(t["nav_none"])}</p></nav>')
        items = []
        for c in cases:
            cls, lab = (("good", t["approved"]) if c["status"] == "approved" else ("warn", t["pending"]) if c["revisions"]
                        else ("mute", t["norev"]))
            quote = (c["issue"]["quotes"] or [""])[0].strip().splitlines()
            current_attr = ' aria-current="page"' if current and c["id"] == current["id"] else ""
            items.append(f'<li><a href="/?case={esc(c["id"])}"{current_attr}><span class="st {cls}"><i></i>{esc(lab)}</span>'
                         f'<span class="q">「{esc(quote[0] if quote else "")}」</span>'
                         f'<small>{esc(c["id"])} · {esc(when(c["opened_at"]))} · {esc(t["revs"].replace("{n}", str(len(c["revisions"]))))}</small></a></li>')
        return (f'<nav class="cases" aria-label="{esc(t["nav_label"])}"><h2>{esc(t["nav"].replace("{n}", str(len(cases))))}</h2>'
                f'<ul>{"".join(items)}</ul></nav>')

    def issue(self, store: dict, case: dict) -> str:
        t = self.t
        quotes = []
        for mid in case["issue"]["messages"]:
            m = fb.find(store["messages"], mid) or {}
            foot = " · ".join(x for x in (when(m.get("at")), PLATFORMS.get(m.get("platform"), m.get("platform") or ""),
                                          f'{t["seen"]}: {self.label(case, m.get("delivered", ""))}') if x)
            quotes.append(f'<blockquote>{esc(m.get("text", ""))}<footer>{esc(foot)}</footer></blockquote>')
        summary = case["issue"].get("summary")
        tail = f'<p class="sum"><b>{esc(t["summary"])}</b>{esc(summary)}</p>' if summary else ""
        return f'<section class="card"><h3>{esc(t["issue"])}</h3><p class="lead">{esc(t["issue_lead"])}</p>{"".join(quotes)}{tail}</section>'

    def flow(self, store: dict, case: dict) -> str:
        t = self.t
        ids = [case["before"], *case["revisions"]]
        items = []
        for i, did in enumerate(ids):
            d = fb.find(store["deliveries"], did) or {}
            sub = " · ".join(x for x in (when(d.get("at")), t["trigger"].get(d.get("trigger"), "")) if x)
            cmp = i == len(ids) - 1 and len(ids) > 1
            if cmp:
                sub += f" · {t['comparing']}"
            if i:
                items.append('<li class="arrow" aria-hidden="true">→</li>')
            items.append(f'<li{" class=cmp" if cmp else ""}>{esc(self.label(case, did))}<small>{esc(sub)}</small></li>')
        if len(ids) == 1:
            items.append(f'<li class="arrow" aria-hidden="true">→</li><li>{esc(t["no_rev_yet"])}</li>')
        return (f'<section class="card"><h3>{esc(t["flow"])}</h3><p class="lead">{esc(t["flow_lead"])}</p>'
                f'<ol class="flow">{"".join(items)}</ol></section>')

    def files(self, store: dict, case: dict) -> str:
        t = self.t
        before = fb.find(store["deliveries"], case["before"])
        if not case["revisions"]:
            names = "".join(f"<li><code>{esc(f['path'])}</code></li>" for f in before["files"])
            return (f'<section class="card"><h3>{esc(t["files"].replace("{n}", str(len(before["files"]))).replace("{c}", "0").replace("{s}", "0"))}</h3>'
                    f'<p class="lead">{esc(t["files_norev"])}</p><ul class="plain">{names}</ul></section>')
        after = fb.latest(store, case)
        a = {f["path"]: f for f in before["files"] if f.get("sha256")}
        b = {f["path"]: f for f in after["files"] if f.get("sha256")}
        blocks, same = [], []
        for path in sorted(set(a) | set(b)):
            fa, fb_ = a.get(path), b.get(path)
            if fa and fb_ and fa["sha256"] == fb_["sha256"]:
                same.append(path)
                continue
            change = "add" if not fa else "del" if not fb_ else "mod"
            blocks.append(self.file_block(store, path, fa, fb_, change))
        title = t["files"].replace("{n}", str(len(blocks) + len(same))).replace("{c}", str(len(blocks))).replace("{s}", str(len(same)))
        tail = (f'<details class="same"><summary>{esc(t["same_files"].replace("{n}", str(len(same))))}</summary>'
                + "".join(f'<p class="note" style="margin:4px 0"><code>{esc(p)}</code></p>' for p in same) + "</details>") if same else ""
        return f'<section class="card"><h3>{esc(title)}</h3><p class="lead">{esc(t["files_lead"])}</p>{"".join(blocks)}{tail}</section>'

    def diff(self, a: str, b: str, path: str) -> str:
        t = self.t
        lines = list(difflib.unified_diff(a.splitlines(), b.splitlines(), f"{t['before']} {path}", f"{t['after']} {path}",
                                          lineterm="", n=2))
        out = []
        for line in lines[:DIFF_LINES]:
            cls = "hunk" if line.startswith(("@@", "---", "+++")) else "add" if line.startswith("+") else "del" if line.startswith("-") else "ctx"
            out.append(f'<span class="{cls}">{esc(line) or " "}</span>')
        if len(lines) > DIFF_LINES:
            out.append(f'<span class="hunk">{esc(t["cut"].replace("{n}", str(DIFF_LINES)))}</span>')
        return '<pre class="diff">' + "".join(out) + "</pre>"

    def file_block(self, store: dict, path: str, fa: dict | None, fb_: dict | None, change: str) -> str:
        t = self.t
        kind = kind_of(fb_ or fa)
        ext = Path(path).suffix.lstrip(".").upper() or "FILE"
        head = (f'<div class="fhead"><code>{esc(path)}</code><span class="chg {change}">{esc(t["chg"][change])}</span>'
                f'<span class="kind">{esc(t["kind"][kind].replace("{ext}", ext))}</span></div>')
        if kind == "text":
            a, b = self.text(store, (fa or {}).get("sha256")), self.text(store, (fb_ or {}).get("sha256"))
            tabs = "".join(f'<button type="button" role="tab" aria-selected="{str(v == "diff").lower()}" data-view="{v}">{esc(lab)}</button>'
                           for v, lab in zip(("diff", "after", "before"), t["tabs"]))
            return (f'<article class="file">{head}<div class="tabs" role="tablist">{tabs}</div>'
                    f'<div data-view="diff">{self.diff(a, b, path)}</div>'
                    f'<pre data-view="after" hidden>{esc(b) if fb_ else esc(t["missing"])}</pre>'
                    f'<pre data-view="before" hidden>{esc(a) if fa else esc(t["missing"])}</pre></article>')

        def side(entry: dict | None, which: str) -> str:
            caption = which + (f"（{size_text(entry['size'])}）" if entry else "")
            if not entry:
                return f'<figure><figcaption>{esc(which)}</figcaption><p class="note">{esc(t["missing"])}</p></figure>'
            url = f'/object/{entry["sha256"]}?name={urllib.parse.quote(Path(path).name)}'
            if kind == "html":
                body = self.text(store, entry["sha256"])
                return (f'<figure><figcaption>{esc(caption)}</figcaption>'
                        f'<iframe sandbox title="{esc(which)} {esc(path)}" srcdoc="{esc(body)}"></iframe></figure>')
            if kind == "image":
                return f'<figure><figcaption>{esc(caption)}</figcaption><img alt="{esc(which)} {esc(path)}" src="{esc(url)}"></figure>'
            return (f'<figure><figcaption>{esc(caption)}</figcaption><a class="open" href="{esc(url)}" target="_blank" '
                    f'rel="noopener">{esc(t["open"].replace("{w}", which))}</a></figure>')

        body = f'<div class="pair">{side(fa, t["before"])}{side(fb_, t["after"])}</div>'
        if kind == "html":
            a, b = self.text(store, (fa or {}).get("sha256")), self.text(store, (fb_ or {}).get("sha256"))
            body += f'<details class="src"><summary>{esc(t["html_src"])}</summary>{self.diff(a, b, path)}</details>'
        return f'<article class="file">{head}{body}</article>'

    def approve(self, store: dict, case: dict, error: str | None, comment: str, notice: str | None) -> str:
        t = self.t
        if case["status"] == "approved":
            ap = case["approval"] or {}
            note = f'<br>{esc(t["done_comment"].replace("{c}", ap["comment"]))}' if ap.get("comment") else ""
            return (f'<section class="card approve"><h3>{esc(t["approve"])}</h3><div class="box good" role="status">'
                    f'<b>{esc(t["done_head"].replace("{at}", when(ap.get("at"))))}</b>{esc(t["done_body"].replace("{d}", case["after"]))}{note}</div>'
                    f'<p class="note">{esc(notice or t["done_note"])}</p></section>')
        if not case["revisions"]:
            return (f'<section class="card approve"><h3>{esc(t["approve"])}</h3><p class="lead">{esc(t["norev_lead"])}</p>'
                    f'<div class="actions"><button class="primary" type="button" disabled>{esc(t["button"])}</button></div></section>')
        last = fb.latest(store, case)
        lead = t["approve_lead"].replace("{d}", last["id"]).replace("{c}", case["id"])
        if error:
            box = f'<div class="box crit" role="alert"><b>{esc(t["reject_head"])}</b>{esc(error)}</div>'
            action = f'<a class="primary" href="/?case={esc(case["id"])}">{esc(t["reload"])}</a>'
            return (f'<section class="card approve"><h3>{esc(t["approve"])}</h3>{box}<p class="lead">{esc(lead)}</p>'
                    f'<label>{esc(t["comment"])}<textarea readonly>{esc(comment)}</textarea></label>'
                    f'<div class="actions">{action}<span class="note">{esc(t["local"])}</span></div></section>')
        token = secrets.token_urlsafe(24)
        with self.guard:
            self.tokens[case["id"]] = {"token": token, "delivery": last["id"], "hashes": fb.hashes(last)}
        return (f'<section class="card approve"><h3>{esc(t["approve"])}</h3><p class="lead">{esc(lead)}</p>'
                f'<form method="post" action="/approve"><input type="hidden" name="case" value="{esc(case["id"])}">'
                f'<input type="hidden" name="delivery" value="{esc(last["id"])}"><input type="hidden" name="token" value="{esc(token)}">'
                f'<label>{esc(t["comment"])}<textarea name="comment" placeholder="{esc(t["comment_ph"])}"></textarea></label>'
                f'<div class="actions"><button class="primary" type="submit">{esc(t["button"])}</button>'
                f'<span class="note">{esc(t["local"])}</span></div></form></section>')

    def wrap(self, inner: str) -> str:
        return (f'<!doctype html><html lang="{self.t["lang"]}"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(self.t["title"])} · {esc(self.name)}</title>'
                f'<link rel="stylesheet" href="{FONTS}"><style>{CSS}</style></head><body><div class="page">{inner}</div>'
                f'<script nonce="{{nonce}}">{JS}</script></body></html>')

    # ------------------------------------------------------------ 承認

    def approve_post(self, form: dict, origin: str | None, agent: str) -> tuple[int, str]:
        t = self.t
        case_id, delivery_id = form.get("case", ""), form.get("delivery", "")
        comment = form.get("comment", "")[:4000]
        if origin not in self.origins:
            return 403, self.page(case_id, error=t["err_origin"] + t["err_tail"], comment=comment)
        with self.guard:
            issued = self.tokens.get(case_id)
            if not issued or not secrets.compare_digest(issued["token"], form.get("token", "")):
                issued = None
            else:
                self.tokens.pop(case_id)  # 一回限り
        if issued is None:
            return 409, self.page(case_id, error=t["err_token"] + t["err_tail"], comment=comment)
        with fb.locked(self.root, self.name):
            store = fb.load(self.root, self.name)
            case = fb.find(store["cases"], case_id)
            error = None
            if case is None:
                error = t["err_case"].replace("{c}", case_id)
            elif case["status"] == "approved":
                error = t["err_done"]
            elif not case["revisions"]:
                error = t["err_norev"]
            elif delivery_id != issued["delivery"]:
                error = t["err_version"]
            elif fb.latest(store, case)["id"] != delivery_id:
                error = t["err_newer"].replace("{d}", fb.latest(store, case)["id"])
            else:
                now = {p: rt.sha256(self.root / p) if (self.root / p).is_file() else None for p in issued["hashes"]}
                moved = [p for p, sha in issued["hashes"].items() if now[p] != sha]
                if moved:
                    error = t["err_changed"].replace("{files}", "、".join(moved[:5]))
            if error is None:
                message = {"id": fb.next_id(store["messages"], "m"), "at": rt.now(), "kind": "approval", "platform": "review",
                           "session": None, "text": comment, "delivered": delivery_id, "class": "approval", "reason": None,
                           "case": case_id}
                store["messages"].append(message)
                case.update({"status": "approved", "after": delivery_id, "approval": {
                    "at": message["at"], "delivery": delivery_id, "comment": comment, "via": "review", "origin": origin,
                    "user_agent": agent[:300], "token": hashlib.sha256(form["token"].encode()).hexdigest()[:16],
                    "message": message["id"], "synthetic": bool(store.get("synthetic"))}})
                fb.save(self.root, store)
        if error:
            return 409, self.page(case_id, error=error + t["err_tail"], comment=comment)
        return 200, self.page(case_id, notice=t["ok"] + t["done_note"])

    # ------------------------------------------------------------ 実ファイル

    def object(self, sha: str, name: str) -> tuple[int, dict, bytes]:
        store = fb.load(self.root, self.name)
        known = {f["sha256"] for d in store["deliveries"] for f in d["files"] + d.get("input_files", []) if f.get("sha256")}
        path = fb.object_path(self.root, self.name, sha)
        if sha not in known or not path.is_file():
            return 404, {"Content-Type": "text/plain; charset=utf-8"}, b"not found"
        ext = Path(name).suffix.lower()
        kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
        headers = {"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"}
        if ext in PAGES or kind.startswith("text/"):
            kind = "text/plain; charset=utf-8"  # 成果物の HTML をこのサーバーの上で動かさない（承認を送らせない）
        elif kind == "application/pdf":
            headers.pop("Content-Security-Policy")  # ブラウザの PDF 表示は sandbox の下では開けない
        elif not kind.startswith("image/"):
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{urllib.parse.quote(name)}"
        headers["Content-Type"] = kind
        return 200, headers, path.read_bytes()


def handler(review: Review):
    class Handler(BaseHTTPRequestHandler):
        server_version = "skill-feedback-review"

        def log_message(self, fmt, *args):  # 端末を汚さない（ログはファイルに出す）
            sys.stderr.write("%s %s\n" % (rt.now(), fmt % args))

        def host_ok(self) -> bool:
            return self.headers.get("Host", "") in {o.split("//", 1)[1] for o in review.origins}

        def send(self, status: int, body: bytes, headers: dict) -> None:
            # Referrer-Policy は same-origin にする。no-referrer だとブラウザがフォームの Origin を null にし、本物の承認も拒否してしまう
            self.send_response(status)
            for key, value in {**headers, "Content-Length": str(len(body)), "Cache-Control": "no-store",
                               "Referrer-Policy": "same-origin", "X-Frame-Options": "DENY"}.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def send_page(self, status: int, page: str) -> None:
            nonce = secrets.token_urlsafe(16)
            csp = (f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
                   "font-src https://fonts.gstatic.com; img-src 'self' data:; frame-src 'self'; form-action 'self'; "
                   "base-uri 'none'; frame-ancestors 'none'")
            head, _, tail = page.rpartition("{nonce}")  # 最後の1つが script の印（本文に同じ文字列があっても置き換えない）
            self.send(status, (head + nonce + tail).encode("utf-8"),
                      {"Content-Type": "text/html; charset=utf-8", "Content-Security-Policy": csp})

        def do_GET(self):
            review.last = time.time()
            if not self.host_ok():
                return self.send(403, b"forbidden", {"Content-Type": "text/plain"})
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            if url.path == "/health":
                return self.send(200, json.dumps({"server": review.server_id}).encode(), {"Content-Type": "application/json"})
            if url.path.startswith("/object/"):
                status, headers, body = review.object(url.path.split("/")[2], (query.get("name") or ["file"])[0])
                return self.send(status, body, headers)
            if url.path == "/":
                return self.send_page(200, review.page((query.get("case") or [None])[0]))
            self.send(404, b"not found", {"Content-Type": "text/plain"})

        def do_POST(self):
            review.last = time.time()
            if not self.host_ok() or urllib.parse.urlsplit(self.path).path != "/approve":
                return self.send(403, b"forbidden", {"Content-Type": "text/plain"})
            length = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
            form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8", "replace")).items()}
            status, page = review.approve_post(form, self.headers.get("Origin"), self.headers.get("User-Agent", ""))
            self.send_page(status, page)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="プロジェクトのルート")
    parser.add_argument("--port", type=int, default=0, help="待ち受けるポート（0 なら空いているもの）")
    parser.add_argument("--idle", type=int, default=30, help="操作が無いまま止まるまでの分")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    contract = rt.load_contract()
    review = Review(root, contract, args.port)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(review))
    review.port = server.server_address[1]
    url = f"http://127.0.0.1:{review.port}/"
    rt.write_json(fb.store_dir(root, review.name) / "review.json",
                  {"url": url, "server": review.server_id, "pid": os.getpid(), "started_at": rt.now()})

    def idle_watch():
        while time.time() - review.last < args.idle * 60:
            time.sleep(5)
        server.shutdown()

    threading.Thread(target=idle_watch, daemon=True).start()
    rt.emit(f"確認画面: {url}")
    sys.stdout.flush()
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
