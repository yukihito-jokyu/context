# 収束テスト ラウンド 4

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | done | 1.000 | 1.000 | 1.000 | 0.871 | 全員通過 | codex 1.000 | 満たす |
| T2-default | done | 1.000 | 1.000 | 1.000 | 0.825 | 全員通過 | codex 1.000 | 満たす |
| T3-edge | done | 1.000 | 1.000 | 1.000 | 0.902 | 全員通過 | codex 1.000 | 満たす |
| H1-holdout | done | 1.000 | 1.000 | 1.000 | 0.900 | 全員通過 | codex 1.000 | 満たす |

## T1-typical

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: `orders`, `sales`
- codex-2: `orders`, `sales`

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-domain-model/notes.md`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-domain-model/notes.md
+++ codex-2/.skill-runs/generate-domain-model/notes.md
@@ -1,3 +1,3 @@
 - 資料照合: 確認済み
 - PNG表示: 確認済み
-- HTML操作: 未実施（ブラウザーの安全制約によりローカルファイルの表示が拒否されたため）
+- HTML操作: 未実施（閲覧環境の安全制限により表示できないため）
```

#### `domain-models/sales/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sales/catalog.json
+++ codex-2/domain-models/sales/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。",
+      "description": "顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。概念の英字IDはCustomerとOrder。",
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
-      "description": "注文は0件または1件の支払を持つ。支払は1件の注文に属する。",
+      "description": "注文は0件または1件の支払を持つ。支払は1件の注文に属する。概念の英字IDはOrderとPayment。",
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
-  "title": "受注・支払のドメインモデル"
+  "title": "受注・支払の業務モデル"
 }
```

#### `domain-models/sales/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sales/index.html
+++ codex-2/domain-models/sales/index.html
@@ -3,24 +3,24 @@
 <head>
 <meta charset="utf-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
-<title>受注・支払のドメインモデル — ドメインモデル</title>
+<title>受注・支払の業務モデル — ドメインモデル</title>
 <style>
 :root{color-scheme:light;--ink:#172e36;--muted:#546a71;--line:#d5e0df;--paper:#f3f6f4;--accent:#146358}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}a{color:var(--accent);text-underline-offset:3px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ca7e30;outline-offset:4px}header{background:#163f3c;color:#f4faf6;padding:44px max(24px,calc((100vw - 1240px)/2)) 38px}.eyebrow{font-size:12px;letter-spacing:.18em;color:#aed1bf;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.35;margin:12px 0}header p{margin:12px 0 0;color:#c2d7d0;max-width:780px}main{max-width:1288px;margin:auto;padding:30px 24px 60px}.toolbar{display:flex;align-items:end;gap:20px;flex-wrap:wrap;margin-bottom:26px}.search{flex:1;min-width:240px}.search label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input{width:100%;padding:13px 16px;border:1px solid #aebfba;border-radius:8px;background:white;color:var(--ink)}#count{margin:0 0 12px;color:var(--muted);font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 18px #143d3010}.card[hidden]{display:none}.preview{background:#e8efeb;border-bottom:1px solid var(--line);padding:22px}.preview button{width:100%;height:264px;display:grid;place-items:center;border:0;background:white;border-radius:8px;padding:18px}.preview img{max-width:100%;max-height:228px;object-fit:contain}.card-body{padding:25px}.diagram-id{font:12px/1.5 ui-monospace,monospace;color:var(--accent);letter-spacing:.05em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px}.card p{color:var(--muted);margin:0 0 15px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:12px;padding:3px 10px;background:#edf4ef;border-radius:5px;color:#365d4c}.unknown{border-left:3px solid #bf8c42;background:#faf4e9;font-size:13px;padding:12px 16px;margin:18px 0}.unknown ul{padding-left:18px;margin:5px 0}.card .confirmed{font-size:13px;color:#427460}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}.sources{padding-left:18px;overflow-wrap:anywhere}.sources li{margin-top:14px}blockquote{margin:8px 0 12px;padding-left:12px;border-left:2px solid #bfccc8;color:var(--muted)}code{font-size:12px}.actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-top:24px;font-size:13px}.primary{border:0;border-radius:6px;background:var(--accent);color:white;padding:9px 15px}.empty{padding:60px 20px;text-align:center;color:var(--muted)}footer{border-top:1px solid var(--line);padding-top:24px;margin-top:36px;color:var(--muted);font-size:12px}dialog{width:min(1400px,96vw);max-width:96vw;max-height:94vh;border:1px solid #bbc9c2;border-radius:12px;padding:0;color:var(--ink)}dialog::backdrop{background:#0a2425b3}.dialog-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--paper)}.dialog-bar h2{font-size:18px;margin:0}.zoom-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.zoom-controls button{background:white;border:1px solid #aebfba;border-radius:5px;padding:5px 12px}#viewport{overflow:auto;max-height:73vh;padding:24px;background:white}#zoom-image{display:block;width:100%;max-width:none;height:auto}#zoom-label{min-width:44px;font-size:12px;text-align:center}@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:30px 24px}.dialog-bar{align-items:start;flex-direction:column}.preview button{height:230px}.preview img{max-height:196px}}
 </style>
 </head>
 <body>
-<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注・支払のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
+<header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注・支払の業務モデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">2件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。 注文 顧客">
+<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。概念の英字IDはCustomerとOrder。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="受注" aria-label="受注の図を拡大"><img src="images/order.png" alt="受注のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。概念の英字IDはCustomerとOrder。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:1</code><blockquote># 受注（図ID: order）&#10;概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="受注">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="支払 注文は0件または1件の支払を持つ。支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="支払 注文は0件または1件の支払を持つ。支払は1件の注文に属する。概念の英字IDはOrderとPayment。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="支払" aria-label="支払の図を拡大"><img src="images/payment.png" alt="支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文は0件または1件の支払を持つ。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文は0件または1件の支払を持つ。支払は1件の注文に属する。概念の英字IDはOrderとPayment。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:3</code><blockquote># 支払（図ID: payment）&#10;概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="payment" data-title="支払">図を拡大</button><a href="diagrams/payment.mmd" download>Mermaid原本</a><a href="images/payment.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/sales/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sales/validation.json
+++ codex-2/domain-models/sales/validation.json
@@ -4,12 +4,12 @@
     "payment"
   ],
   "files": {
-    "catalog.json": "ec39f8e8e6d40f03634a1a45e72b17a1f9b9cbe6ecb0918a8d14b4d9eda65d1f",
+    "catalog.json": "8f8083acc95c0f0a4f950f839a9897c4338ee676f55764ca36d892d7d2167795",
     "diagrams/order.mmd": "66cbd4ba9ae7bba076be4a37951f21691e762c8cb376eb6bb7410748300d8722",
     "diagrams/payment.mmd": "3855e54638462b4b1f01b53de376778a619c861297f65508a7d4ef786fbec908",
     "images/order.png": "194733bd887003de2329bacd5d08d2c531075e7a51f97b23a802465c68a85157",
     "images/payment.png": "984755cb2dc676fe912d499e147f7f28883c4afb4c24e7f67941ee5c445d0c02",
-    "index.html": "757deb22cefadbb7473ed88c496d82ea362e738efdc44475abeed6e8ccb2ff20"
+    "index.html": "b94ae91bda39b7df243728b3eb65544eb0d1adb0c06f241dabd6e839d1339c82"
   },
   "images": {
     "order": {
```


## T2-default

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: なし
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-domain-model/notes.md`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-domain-model/notes.md
+++ codex-2/.skill-runs/generate-domain-model/notes.md
@@ -1,3 +1,3 @@
 - 資料照合: 確認済み
 - PNG表示: 確認済み
-- HTML操作: 未実施（ブラウザの安全制限によりローカルファイルを開けなかったため）
+- HTML操作: 未実施（ブラウザの安全審査でローカルファイルの表示が拒否されたため）
```

#### `domain-models/domain/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/catalog.json
+++ codex-2/domain-models/domain/catalog.json
@@ -1,11 +1,11 @@
 {
   "diagrams": [
     {
-      "description": "利用者が予約を行う関係を表す。多重度は資料で定められていないため図には記載しない。",
+      "description": "利用者が予約を行う関係を表す。多重度は資料で定められていないため、未確認事項に記載している。",
       "id": "reservation",
       "sources": [
         {
-          "path": "unknown.md:1-2",
+          "path": "unknown.md:1",
           "quote": "# 図ID: reservation\n概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。"
         }
       ],
@@ -15,7 +15,7 @@
       ],
       "title": "利用者と予約",
       "unresolved": [
-        "利用者と予約の関係の多重度は資料で定められていない。"
+        "利用者と予約の関係の多重度は資料では定められていないため、未確認。"
       ]
     }
   ],
```

#### `domain-models/domain/diagrams/reservation.mmd`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/diagrams/reservation.mmd
+++ codex-2/domain-models/domain/diagrams/reservation.mmd
@@ -2,4 +2,4 @@
     direction LR
     class User["利用者"]
     class Reservation["予約"]
-    User --> Reservation : 予約を行う
+    User -- Reservation : 予約を行う
```

#### `domain-models/domain/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/index.html
+++ codex-2/domain-models/domain/index.html
@@ -12,10 +12,10 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>予約業務のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。多重度は資料で定められていないため図には記載しない。 予約 利用者">
+<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。多重度は資料で定められていないため、未確認事項に記載している。 予約 利用者">
 <div class="preview"><button class="open-diagram" data-id="reservation" data-title="利用者と予約" aria-label="利用者と予約の図を拡大"><img src="images/reservation.png" alt="利用者と予約のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。多重度は資料で定められていないため図には記載しない。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者と予約の関係の多重度は資料で定められていない。</li></ul></div>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:1-2</code><blockquote># 図ID: reservation&#10;概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。多重度は資料で定められていないため、未確認事項に記載している。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者と予約の関係の多重度は資料では定められていないため、未確認。</li></ul></div>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:1</code><blockquote># 図ID: reservation&#10;概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="reservation" data-title="利用者と予約">図を拡大</button><a href="diagrams/reservation.mmd" download>Mermaid原本</a><a href="images/reservation.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/domain/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/validation.json
+++ codex-2/domain-models/domain/validation.json
@@ -3,10 +3,10 @@
     "reservation"
   ],
   "files": {
-    "catalog.json": "7ba1dfe716bc5c97606b1f60e87691c18b96a7a576b95ef055b073b3862874ee",
-    "diagrams/reservation.mmd": "a13fd0a0b9bac94f40f9bd4a1dc54ca13ecbbdf546aafe7c790bd6214a5e9f6e",
-    "images/reservation.png": "0dc1da88c52d9bfa2da9e8e9e0a83cfe5fc67fc735cc50b525aef02d3578249c",
-    "index.html": "d4a79cdb174af2567f88f071350b41dc7a87804409d41fb94d10ca853e40d894"
+    "catalog.json": "e3b58feba2dce9c8d3e25e68f439a5ff956a594077e10e32c55865b3fa505319",
+    "diagrams/reservation.mmd": "853d3467015f69c91ca6b4f4d30205a851b3e92596b6b4e05519fab211369977",
+    "images/reservation.png": "0e1e5e08714db2a81e5da9bc3ec9ba12bedc3531ed3c34e375abc96701dcac2d",
+    "index.html": "8391aff9eb6378d2f4fa296800fc16230cf2ec10713130c1a236bb5ce95b7e9d"
   },
   "images": {
     "reservation": {
```


## T3-edge

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: `orders`
- codex-2: `orders`

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-domain-model/notes.md`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-domain-model/notes.md
+++ codex-2/.skill-runs/generate-domain-model/notes.md
@@ -1,3 +1,3 @@
 - 資料照合: 確認済み
 - PNG表示: 確認済み
-- HTML操作: 未実施（ブラウザーの安全規則がローカルファイルの表示を拒否したため）
+- HTML操作: 確認済み
```

#### `domain-models/sample/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/catalog.json
+++ codex-2/domain-models/sample/catalog.json
@@ -5,8 +5,8 @@
       "id": "order",
       "sources": [
         {
-          "path": "orders.md:2",
-          "quote": "概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
+          "path": "input.md:1",
+          "quote": "顧客は0件以上の注文を申し込める。注文は必ず1人の顧客に属する。"
         }
       ],
       "terms": [
```

#### `domain-models/sample/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/index.html
+++ codex-2/domain-models/sample/index.html
@@ -15,7 +15,7 @@
 <div class="grid" id="models"><article class="card" id="order" data-search="顧客と注文 顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="顧客と注文" aria-label="顧客と注文の図を拡大"><img src="images/order.png" alt="顧客と注文のドメインモデル図"></button></div>
 <div class="card-body"><div class="diagram-id">order</div><h2>顧客と注文</h2><p>顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>input.md:1</code><blockquote>顧客は0件以上の注文を申し込める。注文は必ず1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="顧客と注文">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
 <article class="card" id="payment" data-search="注文と支払 注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="注文と支払" aria-label="注文と支払の図を拡大"><img src="images/payment.png" alt="注文と支払のドメインモデル図"></button></div>
```

#### `domain-models/sample/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/validation.json
+++ codex-2/domain-models/sample/validation.json
@@ -4,12 +4,12 @@
     "payment"
   ],
   "files": {
-    "catalog.json": "0f29a2622233ef9dfb48aea6c48c1c1b71de255ad513b7ad4d294a3ddef91780",
+    "catalog.json": "0afa40e1f1150903fc43e46cd412ed5e1a9fc08ed043104264ba0dbd4786969a",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
     "images/order.png": "d18f863a4b6fa25bce551f17857f23337f1be0387b2259fb5dc69850cd7adcc4",
-    "images/payment.png": "0711922747c657ec053c5b599df8674be3c75b6387df953c3da4eabb02765bc4",
-    "index.html": "54f48aae039c24d4bc0d8cfbd4aba2b709221efb4a8e8edd1dad5340856d7ee8"
+    "images/payment.png": "7501850f4b8722e150162565096f6c3473fb7d84e6ce10030f597c9287ec9947",
+    "index.html": "b3815d89ffa01b5ccbca2f1d6ee03a065249db118e97e33297438d7bd3d0f313"
   },
   "images": {
     "order": {
```


## H1-holdout

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: `library`, `quot`
- codex-2: `library`, `quot`

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-domain-model/notes.md`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-domain-model/notes.md
+++ codex-2/.skill-runs/generate-domain-model/notes.md
@@ -1,3 +1,3 @@
 - 資料照合: 確認済み
 - PNG表示: 確認済み
-- HTML操作: 未実施（ブラウザーの安全設定でローカルファイルを開けないため）
+- HTML操作: 未実施（ブラウザーの制限で表示と操作を確認できない）
```

#### `domain-models/library/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/catalog.json
+++ codex-2/domain-models/library/catalog.json
@@ -1,7 +1,7 @@
 {
   "diagrams": [
     {
-      "description": "図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、各貸出に対応する図書は1件。",
+      "description": "図書（Book）と貸出（Loan）の「貸し出される」関係を表す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。",
       "id": "library",
       "sources": [
         {
```

#### `domain-models/library/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/index.html
+++ codex-2/domain-models/library/index.html
@@ -12,9 +12,9 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>図書と貸出のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="library" data-search="図書と貸出 図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、各貸出に対応する図書は1件。 図書 貸出">
+<div class="grid" id="models"><article class="card" id="library" data-search="図書と貸出 図書（Book）と貸出（Loan）の「貸し出される」関係を表す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。 図書 貸出">
 <div class="preview"><button class="open-diagram" data-id="library" data-title="図書と貸出" aria-label="図書と貸出の図を拡大"><img src="images/library.png" alt="図書と貸出のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">library</div><h2>図書と貸出</h2><p>図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、各貸出に対応する図書は1件。</p><div class="tags"><span class="tag">図書</span><span class="tag">貸出</span></div><p class="confirmed">未確認事項なし</p>
+<div class="card-body"><div class="diagram-id">library</div><h2>図書と貸出</h2><p>図書（Book）と貸出（Loan）の「貸し出される」関係を表す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。</p><div class="tags"><span class="tag">図書</span><span class="tag">貸出</span></div><p class="confirmed">未確認事項なし</p>
 <details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>library.mmd:1-5</code><blockquote>classDiagram&#10;    direction LR&#10;    class Book[&quot;図書&quot;]&#10;    class Loan[&quot;貸出&quot;]&#10;    Book &quot;1&quot; -- &quot;0..*&quot; Loan : 貸し出される</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="library" data-title="図書と貸出">図を拡大</button><a href="diagrams/library.mmd" download>Mermaid原本</a><a href="images/library.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
```

#### `domain-models/library/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/validation.json
+++ codex-2/domain-models/library/validation.json
@@ -3,10 +3,10 @@
     "library"
   ],
   "files": {
-    "catalog.json": "95d077aa6ce61dcdb07be0ec746463c49c430f4b12fe43a79b0001e671e46b06",
+    "catalog.json": "b7422abbae9ef0a8dcc15879b067ca7f5821944efac772d940015003bfee708a",
     "diagrams/library.mmd": "dd9306de33ca1999fd937ce7953464d4268b0351e11999579cf90144145bf80e",
     "images/library.png": "2484259f3447bcda73c848dfa366aa75ecbbecf89785e1ed6d1b731175f4b6cc",
-    "index.html": "b4be156e93cf3bdd3ea732e4f6fc79159fc33681cf8a38ddd52c3aa0b31ec6d4"
+    "index.html": "11f09c59ec65617a0a27a65c781a3ed0b7b9c3c2207982a89d145e54c6d0ee73"
   },
   "images": {
     "library": {
```
