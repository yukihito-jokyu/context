# 収束テスト ラウンド 2

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | active、done | 0.938 | 1.000 | 0.833 | 0.876 | 全員通過 | claude 0.875、codex 1.000 | 満たさない |
| T2-default | done | 1.000 | 1.000 | 1.000 | 0.848 | 全員通過 | claude 1.000、codex 1.000 | 満たす |
| T3-edge | done、unused | 0.333 | 1.000 | 0.333 | 0.891 | 全員通過 | claude 1.000、codex 1.000 | 満たさない |

## T1-typical

### 実行の状態（期待: done）

- claude-1: active
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: `orders`, `sales`
- claude-2: `orders`, `sales`
- codex-1: `URL`, `orders`, `sales`
- codex-2: `orders`, `sales`

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-domain-model/notes.md`: claude-2, codex-1, codex-2

### 中身の違い（抜粋）

#### `domain-models/sales/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/sales/catalog.json
+++ claude-2/domain-models/sales/catalog.json
@@ -1,11 +1,11 @@
 {
   "diagrams": [
     {
-      "description": "顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。",
+      "description": "顧客が0件以上の注文を申し込む関係を表す。注文は1人の顧客に属する。",
       "id": "order",
       "sources": [
         {
-          "path": "orders.md:2",
+          "path": "orders.md:1-2",
           "quote": "概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
         }
       ],
@@ -17,11 +17,11 @@
       "unresolved": []
     },
     {
-      "description": "注文が支払を持つ関係を表す。支払は1件の注文に属する。",
+      "description": "注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。",
       "id": "payment",
       "sources": [
         {
-          "path": "orders.md:4",
+          "path": "orders.md:3-4",
           "quote": "概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。"
         }
       ],
@@ -35,5 +35,5 @@
   ],
   "name": "sales",
   "schema_version": 1,
-  "title": "受注と支払のドメインモデル"
+  "title": "受注と支払の業務モデル"
 }
```

#### `domain-models/sales/index.html`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/sales/index.html
+++ claude-2/domain-models/sales/index.html
@@ -3,24 +3,24 @@
 <head>
 <meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
-<title>受注と支払のドメインモデル — ドメインモデル</title>
+<title>受注と支払の業務モデル — ドメインモデル</title>
 <style>
 :root{color-scheme:light;--ink:#172e36;--muted:#546a71;--line:#d5e0df;--paper:#f3f6f4;--accent:#146358}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ca7e30;outline-offset:4px}header{background:#163f3c;color:#f4faf6;padding:44px max(24px,calc((100vw - 1240px)/2)) 38px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#aed1bf;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{margin:12px 0 0;color:#c2d7d0;max-width:780px}main{max-width:1288px;margin:auto;padding:30px 24px 60px}.toolbar{display:flex;align-items:end;gap:20px;flex-wrap:wrap;margin-bottom:26px}.search{flex:1;min-width:240px}.search label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input{width:100%;padding:13px 16px;border:1px solid #aebfba;border-radius:8px;background:white;color:var(--ink)}#count{margin:0 0 12px;color:var(--muted);font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 18px #143d3010}.card[hidden]{display:none}.preview{background:#e8efeb;border-bottom:1px solid var(--line);padding:22px}.preview button{width:100%;height:264px;display:grid;place-items:center;border:0;background:white;border-radius:8px;padding:18px}.preview img{max-width:100%;max-height:228px;object-fit:contain}.card-body{padding:25px}.diagram-id{font:12px/1.5 ui-monospace,monospace;color:var(--accent);letter-spacing:.05em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px}.card p{color:var(--muted);margin:0 0 15px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:12px;padding:3px 10px;background:#edf4ef;border-radius:5px;color:#365d4c}.unknown{border-left:3px solid #bf8c42;background:#faf4e9;font-size:13px;padding:12px 16px;margin:18px 0}.unknown ul{padding-left:18px;margin:5px 0}.card .confirmed{font-size:13px;color:#427460}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}.sources{padding-left:18px;overflow-wrap:anywhere}.sources li{margin-top:14px}blockquote{margin:8px 0 12px;padding-left:12px;border-left:2px solid #bfccc8;color:var(--muted)}code{font-size:12px}.actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-top:24px;font-size:13px}.primary{border:0;border-radius:6px;background:var(--accent);color:white;padding:9px 15px}.empty{padding:60px 20px;text-align:center;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px;margin-top:36px;color:var(--muted);font-size:12px}dialog{width:min(1400px,96vw);max-width:96vw;max-height:94vh;border:1px solid #bbc9c2;border-radius:12px;padding:0;color:var(--ink)}dialog::backdrop{background:#0a2425b3}.dialog-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--paper)}.dialog-bar h2{font-size:18px;margin:0}.zoom-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.zoom-controls button{background:white;border:1px solid #aebfba;border-radius:5px;padding:5px 12px}#viewport{overflow:auto;max-height:73vh;padding:24px;background:white}#zoom-image{display:block;width:100%;max-width:none;height:auto}#zoom-label{min-width:44px;font-size:12px;text-align:center}@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:30px 24px}.dialog-bar{align-items:start;flex-direction:column}.preview button{height:230px}.preview img{max-height:196px}}
 </style>
 </head>
 <body>
-<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注と支払のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
+<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注と支払の業務モデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">2件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
+<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客が0件以上の注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="受注" aria-label="受注の図を拡大"><img src="images/order.png" alt="受注のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客が0件以上の注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:1-2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="受注">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="支払 注文が支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="支払 注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="支払" aria-label="支払の図を拡大"><img src="images/payment.png" alt="支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文が支払を持つ関係を表す。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:3-4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="payment" data-title="支払">図を拡大</button><a href="diagrams/payment.mmd" download>Mermaid原本</a><a href="images/payment.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/sales/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/sales/validation.json
+++ claude-2/domain-models/sales/validation.json
@@ -4,12 +4,12 @@
     "payment"
   ],
   "files": {
-    "catalog.json": "c95b4762a80b7cc408830de48921e5c6869096f8432759698ae78582334424c4",
+    "catalog.json": "c8d9251d1fac64a0d4cdcb86b1331908bcaa7f679830dcb9ef4172b69086f25f",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
     "images/order.png": "44c7ee1667cacf1df757d81474afa1dbebd2f26f32c6c881626b4627975e494d",
-    "images/payment.png": "01807d1d01c73fe431ee26c9dcde933068e28952bafdd433af3ecfeedafaebbc",
-    "index.html": "b3be4b24a73b0da7bbb351bbbf5222fcba96cba312fd23de1db2e8a019023ffa"
+    "images/payment.png": "3010923c328fc757c56221f69e456ba139865607e2058ef91771c015eccdfa65",
+    "index.html": "1925f19f98b63484d99da97ccf4b4070673a81d15df38683c3973afaca8337f5"
   },
   "images": {
     "order": {
```

#### `domain-models/sales/catalog.json`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/sales/catalog.json
+++ codex-1/domain-models/sales/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。",
+      "description": "顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。",
       "id": "order",
       "sources": [
         {
-          "path": "orders.md:2",
-          "quote": "概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
+          "path": "orders.md:1",
+          "quote": "# 受注（図ID: order）\n概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
         }
       ],
       "terms": [
@@ -17,12 +17,12 @@
       "unresolved": []
     },
     {
-      "description": "注文が支払を持つ関係を表す。支払は1件の注文に属する。",
+      "description": "注文は0件または1件の支払を持つ。支払は1件の注文に属する。",
       "id": "payment",
       "sources": [
         {
-          "path": "orders.md:4",
-          "quote": "概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。"
+          "path": "orders.md:3",
+          "quote": "# 支払（図ID: payment）\n概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。"
         }
       ],
       "terms": [
@@ -35,5 +35,5 @@
   ],
   "name": "sales",
   "schema_version": 1,
-  "title": "受注と支払のドメインモデル"
+  "title": "受注・支払の業務モデル"
 }
```

#### `domain-models/sales/index.html`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/sales/index.html
+++ codex-1/domain-models/sales/index.html
@@ -3,24 +3,24 @@
 <head>
 <meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
-<title>受注と支払のドメインモデル — ドメインモデル</title>
+<title>受注・支払の業務モデル — ドメインモデル</title>
 <style>
 :root{color-scheme:light;--ink:#172e36;--muted:#546a71;--line:#d5e0df;--paper:#f3f6f4;--accent:#146358}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ca7e30;outline-offset:4px}header{background:#163f3c;color:#f4faf6;padding:44px max(24px,calc((100vw - 1240px)/2)) 38px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#aed1bf;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{margin:12px 0 0;color:#c2d7d0;max-width:780px}main{max-width:1288px;margin:auto;padding:30px 24px 60px}.toolbar{display:flex;align-items:end;gap:20px;flex-wrap:wrap;margin-bottom:26px}.search{flex:1;min-width:240px}.search label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input{width:100%;padding:13px 16px;border:1px solid #aebfba;border-radius:8px;background:white;color:var(--ink)}#count{margin:0 0 12px;color:var(--muted);font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 18px #143d3010}.card[hidden]{display:none}.preview{background:#e8efeb;border-bottom:1px solid var(--line);padding:22px}.preview button{width:100%;height:264px;display:grid;place-items:center;border:0;background:white;border-radius:8px;padding:18px}.preview img{max-width:100%;max-height:228px;object-fit:contain}.card-body{padding:25px}.diagram-id{font:12px/1.5 ui-monospace,monospace;color:var(--accent);letter-spacing:.05em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px}.card p{color:var(--muted);margin:0 0 15px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:12px;padding:3px 10px;background:#edf4ef;border-radius:5px;color:#365d4c}.unknown{border-left:3px solid #bf8c42;background:#faf4e9;font-size:13px;padding:12px 16px;margin:18px 0}.unknown ul{padding-left:18px;margin:5px 0}.card .confirmed{font-size:13px;color:#427460}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}.sources{padding-left:18px;overflow-wrap:anywhere}.sources li{margin-top:14px}blockquote{margin:8px 0 12px;padding-left:12px;border-left:2px solid #bfccc8;color:var(--muted)}code{font-size:12px}.actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-top:24px;font-size:13px}.primary{border:0;border-radius:6px;background:var(--accent);color:white;padding:9px 15px}.empty{padding:60px 20px;text-align:center;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px;margin-top:36px;color:var(--muted);font-size:12px}dialog{width:min(1400px,96vw);max-width:96vw;max-height:94vh;border:1px solid #bbc9c2;border-radius:12px;padding:0;color:var(--ink)}dialog::backdrop{background:#0a2425b3}.dialog-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--paper)}.dialog-bar h2{font-size:18px;margin:0}.zoom-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.zoom-controls button{background:white;border:1px solid #aebfba;border-radius:5px;padding:5px 12px}#viewport{overflow:auto;max-height:73vh;padding:24px;background:white}#zoom-image{display:block;width:100%;max-width:none;height:auto}#zoom-label{min-width:44px;font-size:12px;text-align:center}@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:30px 24px}.dialog-bar{align-items:start;flex-direction:column}.preview button{height:230px}.preview img{max-height:196px}}
 </style>
 </head>
 <body>
-<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注と支払のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
+<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注・支払の業務モデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">2件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
+<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="受注" aria-label="受注の図を拡大"><img src="images/order.png" alt="受注のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:1</code><blockquote># 受注（図ID: order）&#10;概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="受注">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="支払 注文が支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="支払 注文は0件または1件の支払を持つ。支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="支払" aria-label="支払の図を拡大"><img src="images/payment.png" alt="支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文が支払を持つ関係を表す。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文は0件または1件の支払を持つ。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:3</code><blockquote># 支払（図ID: payment）&#10;概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="payment" data-title="支払">図を拡大</button><a href="diagrams/payment.mmd" download>Mermaid原本</a><a href="images/payment.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/sales/validation.json`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/sales/validation.json
+++ codex-1/domain-models/sales/validation.json
@@ -4,12 +4,12 @@
     "payment"
   ],
   "files": {
-    "catalog.json": "c95b4762a80b7cc408830de48921e5c6869096f8432759698ae78582334424c4",
+    "catalog.json": "bda89bcdaa86cee36f936737ea245d159f26a8f616919c4605094587aff93696",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
-    "images/order.png": "44c7ee1667cacf1df757d81474afa1dbebd2f26f32c6c881626b4627975e494d",
-    "images/payment.png": "01807d1d01c73fe431ee26c9dcde933068e28952bafdd433af3ecfeedafaebbc",
-    "index.html": "b3be4b24a73b0da7bbb351bbbf5222fcba96cba312fd23de1db2e8a019023ffa"
+    "images/order.png": "b2a0b162415c29eb442c0d893835847d9a6d0b164316e70d8260fa5e061ad223",
+    "images/payment.png": "7501850f4b8722e150162565096f6c3473fb7d84e6ce10030f597c9287ec9947",
+    "index.html": "e89917fb16ca987580eb4c143040f9d7e2cbb1ca6e36d50032ed67d1289ce17e"
   },
   "images": {
     "order": {
```


## T2-default

### 実行の状態（期待: done）

- claude-1: done
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: なし
- claude-2: なし
- codex-1: なし
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `domain-models/domain/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/domain/catalog.json
+++ claude-2/domain-models/domain/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "利用者が予約を行う関係を表す。",
+      "description": "利用者が予約を行う関係を表す。資料では多重度を定めていないため、関係のみを図にし多重度は未確認事項とする。",
       "id": "reservation",
       "sources": [
         {
           "path": "unknown.md:2",
-          "quote": "概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。"
+          "quote": "概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。"
         }
       ],
       "terms": [
@@ -15,7 +15,7 @@
       ],
       "title": "利用者と予約",
       "unresolved": [
-        "利用者(User)と予約(Reservation)の間の多重度は資料で定めていないため図にしていない。"
+        "利用者(User)と予約(Reservation)の間の多重度は資料で定められていないため図にしていない"
       ]
     }
   ],
```

#### `domain-models/domain/index.html`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/domain/index.html
+++ claude-2/domain-models/domain/index.html
@@ -12,10 +12,10 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>予約業務のモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。 予約 利用者">
+<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。資料では多重度を定めていないため、関係のみを図にし多重度は未確認事項とする。 予約 利用者">
 <div class="preview"><button class="open-diagram" data-id="reservation" data-title="利用者と予約" aria-label="利用者と予約の図を拡大"><img src="images/reservation.png" alt="利用者と予約のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者(User)と予約(Reservation)の間の多重度は資料で定めていないため図にしていない。</li></ul></div>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:2</code><blockquote>概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。資料では多重度を定めていないため、関係のみを図にし多重度は未確認事項とする。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者(User)と予約(Reservation)の間の多重度は資料で定められていないため図にしていない</li></ul></div>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:2</code><blockquote>概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="reservation" data-title="利用者と予約">図を拡大</button><a href="diagrams/reservation.mmd" download>Mermaid原本</a><a href="images/reservation.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/domain/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/domain-models/domain/validation.json
+++ claude-2/domain-models/domain/validation.json
@@ -3,10 +3,10 @@
     "reservation"
   ],
   "files": {
-    "catalog.json": "f32eb9fa92155f8d3d43e3d33cd028c800073391355da223e3cef69a825f7eca",
+    "catalog.json": "a0f3713de819bc183668e0bfa50581713273f701b24d3fb5350feea42aea853b",
     "diagrams/reservation.mmd": "a801e21e647e497db3419cacc4b954ab1e6eca7376ccda5ad043713331ff418f",
     "images/reservation.png": "183082480b8c3699793b600cd37dc8b84555bdd91c5cc28aed2286f532cf3abc",
-    "index.html": "9bd3ac09d3461841e64d7302a47032eee734cc90f79f9995f72b3756090c7895"
+    "index.html": "fd7be675db3f80145dba8d2c664602007c9de22cc1f2b5da3432d9dfa2b5633b"
   },
   "images": {
     "reservation": {
```

#### `domain-models/domain/catalog.json`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/domain/catalog.json
+++ codex-1/domain-models/domain/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "利用者が予約を行う関係を表す。",
+      "description": "利用者が予約を行う関係を表す。多重度は資料に定められていないため、図には記載しない。",
       "id": "reservation",
       "sources": [
         {
-          "path": "unknown.md:2",
-          "quote": "概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。"
+          "path": "unknown.md:1",
+          "quote": "# 図ID: reservation\n概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。"
         }
       ],
       "terms": [
@@ -15,11 +15,11 @@
       ],
       "title": "利用者と予約",
       "unresolved": [
-        "利用者(User)と予約(Reservation)の間の多重度は資料で定めていないため図にしていない。"
+        "利用者と予約の関係の多重度は資料に定められていないため、未確認。"
       ]
     }
   ],
   "name": "domain",
   "schema_version": 1,
-  "title": "予約業務のモデル"
+  "title": "予約業務のドメインモデル"
 }
```

#### `domain-models/domain/diagrams/reservation.mmd`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/domain/diagrams/reservation.mmd
+++ codex-1/domain-models/domain/diagrams/reservation.mmd
@@ -2,4 +2,4 @@
     direction LR
     class User["利用者"]
     class Reservation["予約"]
-    User -- Reservation : 行う
+    User -- Reservation : 予約を行う
```

#### `domain-models/domain/index.html`（claude-1 と codex-1）

```diff
--- claude-1/domain-models/domain/index.html
+++ codex-1/domain-models/domain/index.html
@@ -3,19 +3,19 @@
 <head>
 <meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
-<title>予約業務のモデル — ドメインモデル</title>
+<title>予約業務のドメインモデル — ドメインモデル</title>
 <style>
 :root{color-scheme:light;--ink:#172e36;--muted:#546a71;--line:#d5e0df;--paper:#f3f6f4;--accent:#146358}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ca7e30;outline-offset:4px}header{background:#163f3c;color:#f4faf6;padding:44px max(24px,calc((100vw - 1240px)/2)) 38px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#aed1bf;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{margin:12px 0 0;color:#c2d7d0;max-width:780px}main{max-width:1288px;margin:auto;padding:30px 24px 60px}.toolbar{display:flex;align-items:end;gap:20px;flex-wrap:wrap;margin-bottom:26px}.search{flex:1;min-width:240px}.search label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input{width:100%;padding:13px 16px;border:1px solid #aebfba;border-radius:8px;background:white;color:var(--ink)}#count{margin:0 0 12px;color:var(--muted);font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 18px #143d3010}.card[hidden]{display:none}.preview{background:#e8efeb;border-bottom:1px solid var(--line);padding:22px}.preview button{width:100%;height:264px;display:grid;place-items:center;border:0;background:white;border-radius:8px;padding:18px}.preview img{max-width:100%;max-height:228px;object-fit:contain}.card-body{padding:25px}.diagram-id{font:12px/1.5 ui-monospace,monospace;color:var(--accent);letter-spacing:.05em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px}.card p{color:var(--muted);margin:0 0 15px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:12px;padding:3px 10px;background:#edf4ef;border-radius:5px;color:#365d4c}.unknown{border-left:3px solid #bf8c42;background:#faf4e9;font-size:13px;padding:12px 16px;margin:18px 0}.unknown ul{padding-left:18px;margin:5px 0}.card .confirmed{font-size:13px;color:#427460}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}.sources{padding-left:18px;overflow-wrap:anywhere}.sources li{margin-top:14px}blockquote{margin:8px 0 12px;padding-left:12px;border-left:2px solid #bfccc8;color:var(--muted)}code{font-size:12px}.actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-top:24px;font-size:13px}.primary{border:0;border-radius:6px;background:var(--accent);color:white;padding:9px 15px}.empty{padding:60px 20px;text-align:center;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px;margin-top:36px;color:var(--muted);font-size:12px}dialog{width:min(1400px,96vw);max-width:96vw;max-height:94vh;border:1px solid #bbc9c2;border-radius:12px;padding:0;color:var(--ink)}dialog::backdrop{background:#0a2425b3}.dialog-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--paper)}.dialog-bar h2{font-size:18px;margin:0}.zoom-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.zoom-controls button{background:white;border:1px solid #aebfba;border-radius:5px;padding:5px 12px}#viewport{overflow:auto;max-height:73vh;padding:24px;background:white}#zoom-image{display:block;width:100%;max-width:none;height:auto}#zoom-label{min-width:44px;font-size:12px;text-align:center}@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:30px 24px}.dialog-bar{align-items:start;flex-direction:column}.preview button{height:230px}.preview img{max-height:196px}}
 </style>
 </head>
 <body>
-<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>予約業務のモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
+<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>予約業務のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。 予約 利用者">
+<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。多重度は資料に定められていないため、図には記載しない。 予約 利用者">
 <div class="preview"><button class="open-diagram" data-id="reservation" data-title="利用者と予約" aria-label="利用者と予約の図を拡大"><img src="images/reservation.png" alt="利用者と予約のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者(User)と予約(Reservation)の間の多重度は資料で定めていないため図にしていない。</li></ul></div>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:2</code><blockquote>概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。多重度は資料に定められていないため、図には記載しない。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者と予約の関係の多重度は資料に定められていないため、未確認。</li></ul></div>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:1</code><blockquote># 図ID: reservation&#10;概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="reservation" data-title="利用者と予約">図を拡大</button><a href="diagrams/reservation.mmd" download>Mermaid原本</a><a href="images/reservation.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```


## T3-edge

### 実行の状態（期待: done）

- claude-1: unused
- claude-2: unused
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: なし
- claude-2: なし
- codex-1: `orders`
- codex-2: `orders`

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-domain-model/notes.md`: codex-1, codex-2
- `domain-models/sample/catalog.json`: codex-1, codex-2
- `domain-models/sample/diagrams/payment.mmd`: codex-1, codex-2
- `domain-models/sample/images/payment.png`: codex-1, codex-2
- `domain-models/sample/index.html`: codex-1, codex-2
- `domain-models/sample/validation.json`: codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-domain-model/notes.md`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-domain-model/notes.md
+++ codex-2/.skill-runs/generate-domain-model/notes.md
@@ -1,3 +1,3 @@
 - 資料照合: 確認済み
 - PNG表示: 確認済み
-- HTML操作: 未実施（ブラウザーのセキュリティポリシーがローカルHTMLの表示を拒否したため）
+- HTML操作: 未実施（ブラウザの自動承認審査でローカルHTMLを開く操作が拒否されたため）
```

#### `domain-models/sample/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/catalog.json
+++ codex-2/domain-models/sample/catalog.json
@@ -17,7 +17,7 @@
       "unresolved": []
     },
     {
-      "description": "注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。",
+      "description": "注文は0件または1件の支払を持ち、支払は1件の注文に属する。",
       "id": "payment",
       "sources": [
         {
@@ -35,5 +35,5 @@
   ],
   "name": "sample",
   "schema_version": 1,
-  "title": "受注業務のモデル"
+  "title": "受注・支払業務のモデル"
 }
```

#### `domain-models/sample/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/index.html
+++ codex-2/domain-models/sample/index.html
@@ -3,13 +3,13 @@
 <head>
 <meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
-<title>受注業務のモデル — ドメインモデル</title>
+<title>受注・支払業務のモデル — ドメインモデル</title>
 <style>
 :root{color-scheme:light;--ink:#172e36;--muted:#546a71;--line:#d5e0df;--paper:#f3f6f4;--accent:#146358}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ca7e30;outline-offset:4px}header{background:#163f3c;color:#f4faf6;padding:44px max(24px,calc((100vw - 1240px)/2)) 38px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#aed1bf;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{margin:12px 0 0;color:#c2d7d0;max-width:780px}main{max-width:1288px;margin:auto;padding:30px 24px 60px}.toolbar{display:flex;align-items:end;gap:20px;flex-wrap:wrap;margin-bottom:26px}.search{flex:1;min-width:240px}.search label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input{width:100%;padding:13px 16px;border:1px solid #aebfba;border-radius:8px;background:white;color:var(--ink)}#count{margin:0 0 12px;color:var(--muted);font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 18px #143d3010}.card[hidden]{display:none}.preview{background:#e8efeb;border-bottom:1px solid var(--line);padding:22px}.preview button{width:100%;height:264px;display:grid;place-items:center;border:0;background:white;border-radius:8px;padding:18px}.preview img{max-width:100%;max-height:228px;object-fit:contain}.card-body{padding:25px}.diagram-id{font:12px/1.5 ui-monospace,monospace;color:var(--accent);letter-spacing:.05em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px}.card p{color:var(--muted);margin:0 0 15px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:12px;padding:3px 10px;background:#edf4ef;border-radius:5px;color:#365d4c}.unknown{border-left:3px solid #bf8c42;background:#faf4e9;font-size:13px;padding:12px 16px;margin:18px 0}.unknown ul{padding-left:18px;margin:5px 0}.card .confirmed{font-size:13px;color:#427460}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}.sources{padding-left:18px;overflow-wrap:anywhere}.sources li{margin-top:14px}blockquote{margin:8px 0 12px;padding-left:12px;border-left:2px solid #bfccc8;color:var(--muted)}code{font-size:12px}.actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-top:24px;font-size:13px}.primary{border:0;border-radius:6px;background:var(--accent);color:white;padding:9px 15px}.empty{padding:60px 20px;text-align:center;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px;margin-top:36px;color:var(--muted);font-size:12px}dialog{width:min(1400px,96vw);max-width:96vw;max-height:94vh;border:1px solid #bbc9c2;border-radius:12px;padding:0;color:var(--ink)}dialog::backdrop{background:#0a2425b3}.dialog-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--paper)}.dialog-bar h2{font-size:18px;margin:0}.zoom-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.zoom-controls button{background:white;border:1px solid #aebfba;border-radius:5px;padding:5px 12px}#viewport{overflow:auto;max-height:73vh;padding:24px;background:white}#zoom-image{display:block;width:100%;max-width:none;height:auto}#zoom-label{min-width:44px;font-size:12px;text-align:center}@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:30px 24px}.dialog-bar{align-items:start;flex-direction:column}.preview button{height:230px}.preview img{max-height:196px}}
 </style>
 </head>
 <body>
-<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注業務のモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
+<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注・支払業務のモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">2件のモデル</p></div>
 <div class="grid" id="models"><article class="card" id="order" data-search="顧客と注文 顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
@@ -17,9 +17,9 @@
 <div class="card-body"><div class="diagram-id">order</div><h2>顧客と注文</h2><p>顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
 <details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="顧客と注文">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="注文と支払 注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="注文と支払 注文は0件または1件の支払を持ち、支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="注文と支払" aria-label="注文と支払の図を拡大"><img src="images/payment.png" alt="注文と支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>注文と支払</h2><p>注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<div class="card-body"><div class="diagram-id">payment</div><h2>注文と支払</h2><p>注文は0件または1件の支払を持ち、支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
 <details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="payment" data-title="注文と支払">図を拡大</button><a href="diagrams/payment.mmd" download>Mermaid原本</a><a href="images/payment.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
```

#### `domain-models/sample/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/validation.json
+++ codex-2/domain-models/sample/validation.json
@@ -4,12 +4,12 @@
     "payment"
   ],
   "files": {
-    "catalog.json": "5c6e762528f6013234a5a75bea9292e70c005e127f7bd595e0671e909c69295e",
+    "catalog.json": "ec4f228258f9a6bae426d5eb08a45e6edcd5fb752113422a5192dcf630369a0d",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
     "images/order.png": "d18f863a4b6fa25bce551f17857f23337f1be0387b2259fb5dc69850cd7adcc4",
     "images/payment.png": "7501850f4b8722e150162565096f6c3473fb7d84e6ce10030f597c9287ec9947",
-    "index.html": "b7c0ef45157c789acfe2778d77824b6d99f291887aaf0e0688049b259be70bc9"
+    "index.html": "4eb011d31e48893df3ec4fb515dfdfce347808e5df3f733b0d1b337d55a84503"
   },
   "images": {
     "order": {
```
