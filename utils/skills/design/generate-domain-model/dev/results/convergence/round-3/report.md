# 収束テスト ラウンド 3

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | done | 1.000 | 1.000 | 1.000 | 0.879 | 全員通過 | codex 1.000 | 満たす |
| T2-default | done | 1.000 | 1.000 | 1.000 | 0.864 | 全員通過 | codex 1.000 | 満たす |
| T3-edge | done | 1.000 | 1.000 | 1.000 | 0.886 | 全員通過 | codex 1.000 | 満たす |
| H1-holdout | done | 1.000 | 1.000 | 0.250 | 0.885 | 全員通過 | codex 1.000 | 満たさない |

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
-- HTML操作: 未実施（ブラウザの安全制約によりローカルファイルの表示が拒否されたため）
+- HTML操作: 未実施（ブラウザーの安全制限によりローカルファイルを表示できないため）
```

#### `domain-models/sales/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sales/catalog.json
+++ codex-2/domain-models/sales/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "顧客(Customer)と注文(Order)の関係を表す。顧客は0件以上の注文を申し込み、注文は1人の顧客に属する。",
+      "description": "顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。",
       "id": "order",
       "sources": [
         {
-          "path": "orders.md:1",
-          "quote": "# 受注（図ID: order）\n概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
+          "path": "orders.md:2",
+          "quote": "概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。"
         }
       ],
       "terms": [
@@ -17,12 +17,12 @@
       "unresolved": []
     },
     {
-      "description": "注文(Order)と支払(Payment)の関係を表す。注文は0件または1件の支払を持ち、支払は1件の注文に属する。",
+      "description": "注文は0件または1件の支払を持つ。支払は1件の注文に属する。",
       "id": "payment",
       "sources": [
         {
-          "path": "orders.md:3",
-          "quote": "# 支払（図ID: payment）\n概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。"
+          "path": "orders.md:4",
+          "quote": "概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。"
         }
       ],
       "terms": [
```

#### `domain-models/sales/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sales/index.html
+++ codex-2/domain-models/sales/index.html
@@ -12,15 +12,15 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>受注・支払のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">2件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客(Customer)と注文(Order)の関係を表す。顧客は0件以上の注文を申し込み、注文は1人の顧客に属する。 注文 顧客">
+<div class="grid" id="models"><article class="card" id="order" data-search="受注 顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="受注" aria-label="受注の図を拡大"><img src="images/order.png" alt="受注のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客(Customer)と注文(Order)の関係を表す。顧客は0件以上の注文を申し込み、注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:1</code><blockquote># 受注（図ID: order）&#10;概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">order</div><h2>受注</h2><p>顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="受注">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="支払 注文(Order)と支払(Payment)の関係を表す。注文は0件または1件の支払を持ち、支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="支払 注文は0件または1件の支払を持つ。支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="支払" aria-label="支払の図を拡大"><img src="images/payment.png" alt="支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文(Order)と支払(Payment)の関係を表す。注文は0件または1件の支払を持ち、支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:3</code><blockquote># 支払（図ID: payment）&#10;概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">payment</div><h2>支払</h2><p>注文は0件または1件の支払を持つ。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:4</code><blockquote>概念は注文(Order)と支払(Payment)。注文は0件または1件の支払を持つ。支払は1件の注文に属する。</blockquote></li></ul></details>
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
-    "catalog.json": "7a23d7818096822638dbabab28cc8e1b2d29e6c32b3cd3f9581f0477bafdb6a7",
+    "catalog.json": "ec39f8e8e6d40f03634a1a45e72b17a1f9b9cbe6ecb0918a8d14b4d9eda65d1f",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
-    "images/order.png": "44c7ee1667cacf1df757d81474afa1dbebd2f26f32c6c881626b4627975e494d",
+    "images/order.png": "b2a0b162415c29eb442c0d893835847d9a6d0b164316e70d8260fa5e061ad223",
     "images/payment.png": "110a2be6d67601483f9169a5c74b53d1f722a9c20d8f6a4a2a4357dd8c481c49",
-    "index.html": "a1433fb1072c2566972c128b24fcfefbe85ff8d5c642c5b9337e493db705d27f"
+    "index.html": "757deb22cefadbb7473ed88c496d82ea362e738efdc44475abeed6e8ccb2ff20"
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
-- HTML操作: 未実施（ブラウザーの自動安全審査がローカルファイルを開く操作を拒否したため）
+- HTML操作: 未実施（ブラウザーの安全制限でローカルファイルの表示が拒否されたため）
```

#### `domain-models/domain/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/catalog.json
+++ codex-2/domain-models/domain/catalog.json
@@ -1,12 +1,12 @@
 {
   "diagrams": [
     {
-      "description": "利用者が予約を行う関係を表す。資料で定められていない多重度は図に記載せず、未確認事項として残す。",
+      "description": "利用者が予約を行う関係を表す。多重度は資料で定められていないため、図には記載しない。",
       "id": "reservation",
       "sources": [
         {
-          "path": "unknown.md:1-2",
-          "quote": "# 図ID: reservation\n概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。"
+          "path": "unknown.md:2",
+          "quote": "概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。"
         }
       ],
       "terms": [
@@ -15,7 +15,7 @@
       ],
       "title": "利用者と予約",
       "unresolved": [
-        "利用者と予約の関係の多重度は、資料で定められていないため未確認。"
+        "利用者と予約の関係の多重度は資料で定められていない。"
       ]
     }
   ],
```

#### `domain-models/domain/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/domain/index.html
+++ codex-2/domain-models/domain/index.html
@@ -12,10 +12,10 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>予約業務のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。資料で定められていない多重度は図に記載せず、未確認事項として残す。 予約 利用者">
+<div class="grid" id="models"><article class="card" id="reservation" data-search="利用者と予約 利用者が予約を行う関係を表す。多重度は資料で定められていないため、図には記載しない。 予約 利用者">
 <div class="preview"><button class="open-diagram" data-id="reservation" data-title="利用者と予約" aria-label="利用者と予約の図を拡大"><img src="images/reservation.png" alt="利用者と予約のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。資料で定められていない多重度は図に記載せず、未確認事項として残す。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者と予約の関係の多重度は、資料で定められていないため未確認。</li></ul></div>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:1-2</code><blockquote># 図ID: reservation&#10;概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">reservation</div><h2>利用者と予約</h2><p>利用者が予約を行う関係を表す。多重度は資料で定められていないため、図には記載しない。</p><div class="tags"><span class="tag">予約</span><span class="tag">利用者</span></div><div class="unknown"><strong>確認したいこと</strong><ul><li>利用者と予約の関係の多重度は資料で定められていない。</li></ul></div>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>unknown.md:2</code><blockquote>概念は利用者(User)と予約(Reservation)。利用者が予約を行う。資料では多重度は定めていない。多重度を図に断定せず未確認事項に記載する。</blockquote></li></ul></details>
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
-    "catalog.json": "09c613a4cc39a8cb6ae06dfea416cbff0e181322913acd5ce2bbdb345226a593",
+    "catalog.json": "84884bb326e29ff7440038ddd9e595b29bc68618457e20f169da0381bf86f4b8",
     "diagrams/reservation.mmd": "853d3467015f69c91ca6b4f4d30205a851b3e92596b6b4e05519fab211369977",
-    "images/reservation.png": "0e1e5e08714db2a81e5da9bc3ec9ba12bedc3531ed3c34e375abc96701dcac2d",
-    "index.html": "fbfce09669f741e81eb729a5bf9523e7ab7a0cf4a3fd9a38616aa98b8b801be1"
+    "images/reservation.png": "d46e6923589a2f49c06bf061602d91ba9aa153faf9ee1ce7c54a872615b73538",
+    "index.html": "3b9983cbd0d0a363de4e85593f2b13a185b8c14dec4f76e7f1530fc295bd5eb4"
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
-- HTML操作: 未実施（ブラウザーがローカルファイルの表示を許可しないため）
+- HTML操作: 未実施（ブラウザーの自動安全確認でローカル表示が拒否されたため）
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
@@ -17,7 +17,7 @@
       "unresolved": []
     },
     {
-      "description": "注文は0件または1件の支払を持つ。支払は1件の注文に属する。",
+      "description": "注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。",
       "id": "payment",
       "sources": [
         {
```

#### `domain-models/sample/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/sample/index.html
+++ codex-2/domain-models/sample/index.html
@@ -15,11 +15,11 @@
 <div class="grid" id="models"><article class="card" id="order" data-search="顧客と注文 顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。 注文 顧客">
 <div class="preview"><button class="open-diagram" data-id="order" data-title="顧客と注文" aria-label="顧客と注文の図を拡大"><img src="images/order.png" alt="顧客と注文のドメインモデル図"></button></div>
 <div class="card-body"><div class="diagram-id">order</div><h2>顧客と注文</h2><p>顧客が注文を申し込む関係を表す。注文は1人の顧客に属する。</p><div class="tags"><span class="tag">注文</span><span class="tag">顧客</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>orders.md:2</code><blockquote>概念は顧客(Customer)と注文(Order)。顧客は0件以上の注文を申し込む。注文は1人の顧客に属する。</blockquote></li></ul></details>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>input.md:1</code><blockquote>顧客は0件以上の注文を申し込める。注文は必ず1人の顧客に属する。</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="order" data-title="顧客と注文">図を拡大</button><a href="diagrams/order.mmd" download>Mermaid原本</a><a href="images/order.png" download>PNG</a></div></div></article>
-<article class="card" id="payment" data-search="注文と支払 注文は0件または1件の支払を持つ。支払は1件の注文に属する。 支払 注文">
+<article class="card" id="payment" data-search="注文と支払 注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。 支払 注文">
 <div class="preview"><button class="open-diagram" data-id="payment" data-title="注文と支払" aria-label="注文と支払の図を拡大"><img src="images/payment.png" alt="注文と支払のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">payment</div><h2>注文と支払</h2><p>注文は0件または1件の支払を持つ。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
+<div class="card-body"><div class="diagram-id">payment</div><h2>注文と支払</h2><p>注文が0件または1件の支払を持つ関係を表す。支払は1件の注文に属する。</p><div class="tags"><span class="tag">支払</span><span class="tag">注文</span></div><p class="confirmed">未確認事項なし</p>
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
-    "catalog.json": "25fbb6da485c77e39ee25a49f1290ad583abe02fd9b523db6a19dce95fe00331",
+    "catalog.json": "0afa40e1f1150903fc43e46cd412ed5e1a9fc08ed043104264ba0dbd4786969a",
     "diagrams/order.mmd": "ead3a30813e4e1ff44ed86316a890f16f58fd6d04cf80f0f2d56450ff089c52e",
     "diagrams/payment.mmd": "6ce690e886b14ccd3818e51d40cdba192b01b870f985bdc4573b86b22528c850",
     "images/order.png": "d18f863a4b6fa25bce551f17857f23337f1be0387b2259fb5dc69850cd7adcc4",
-    "images/payment.png": "7501850f4b8722e150162565096f6c3473fb7d84e6ce10030f597c9287ec9947",
-    "index.html": "92451bdf3f76da8ed92e7c9b8c3e3fead22e574cb0970cf42e3795c669156524"
+    "images/payment.png": "110a2be6d67601483f9169a5c74b53d1f722a9c20d8f6a4a2a4357dd8c481c49",
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
- codex-2: `H1-holdout`, `codex-2`, `folders`, `library`, `private`, `quot`, `round-3`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`

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
-- HTML操作: 確認済み
+- HTML操作: 未実施（ブラウザの安全方針によりローカルファイルの表示が拒否されたため）
```

#### `domain-models/library/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/catalog.json
+++ codex-2/domain-models/library/catalog.json
@@ -1,11 +1,11 @@
 {
   "diagrams": [
     {
-      "description": "図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、貸出1件に対して図書は1件となる。",
+      "description": "図書（Book）と貸出（Loan）の「貸し出される」関係を示す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。",
       "id": "library",
       "sources": [
         {
-          "path": "library.mmd:1-5",
+          "path": "/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-domain-model/round-3/H1-holdout/codex-2/library.mmd:1-5",
           "quote": "classDiagram\n    direction LR\n    class Book[\"図書\"]\n    class Loan[\"貸出\"]\n    Book \"1\" -- \"0..*\" Loan : 貸し出される"
         }
       ],
```

#### `domain-models/library/index.html`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/index.html
+++ codex-2/domain-models/library/index.html
@@ -12,10 +12,10 @@
 <header><div class="eyebrow">DOMAIN MODEL CATALOG</div><h1>図書と貸出のドメインモデル</h1><p>業務の概念をつなぎ、関係を確かめる。図と根拠を一緒に見ながら、確認したい点を整理できます。</p></header>
 <main>
 <div class="toolbar"><div class="search"><label for="search">モデルを探す</label><input type="search" id="search" placeholder="タイトル・説明・業務用語で検索" autocomplete="off"></div><p id="count" role="status" aria-live="polite">1件のモデル</p></div>
-<div class="grid" id="models"><article class="card" id="library" data-search="図書と貸出 図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、貸出1件に対して図書は1件となる。 図書 貸出">
+<div class="grid" id="models"><article class="card" id="library" data-search="図書と貸出 図書（Book）と貸出（Loan）の「貸し出される」関係を示す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。 図書 貸出">
 <div class="preview"><button class="open-diagram" data-id="library" data-title="図書と貸出" aria-label="図書と貸出の図を拡大"><img src="images/library.png" alt="図書と貸出のドメインモデル図"></button></div>
-<div class="card-body"><div class="diagram-id">library</div><h2>図書と貸出</h2><p>図書（Book）と貸出（Loan）の「貸し出される」関係を表す。図書1件に対して貸出は0件以上、貸出1件に対して図書は1件となる。</p><div class="tags"><span class="tag">図書</span><span class="tag">貸出</span></div><p class="confirmed">未確認事項なし</p>
-<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>library.mmd:1-5</code><blockquote>classDiagram&#10;    direction LR&#10;    class Book[&quot;図書&quot;]&#10;    class Loan[&quot;貸出&quot;]&#10;    Book &quot;1&quot; -- &quot;0..*&quot; Loan : 貸し出される</blockquote></li></ul></details>
+<div class="card-body"><div class="diagram-id">library</div><h2>図書と貸出</h2><p>図書（Book）と貸出（Loan）の「貸し出される」関係を示す。1つの図書に0件以上の貸出が対応し、各貸出には1つの図書が対応する。</p><div class="tags"><span class="tag">図書</span><span class="tag">貸出</span></div><p class="confirmed">未確認事項なし</p>
+<details><summary>根拠となる資料（1件）</summary><ul class="sources"><li><code>/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-domain-model/round-3/H1-holdout/codex-2/library.mmd:1-5</code><blockquote>classDiagram&#10;    direction LR&#10;    class Book[&quot;図書&quot;]&#10;    class Loan[&quot;貸出&quot;]&#10;    Book &quot;1&quot; -- &quot;0..*&quot; Loan : 貸し出される</blockquote></li></ul></details>
 <div class="actions"><button class="open-diagram primary" data-id="library" data-title="図書と貸出">図を拡大</button><a href="diagrams/library.mmd" download>Mermaid原本</a><a href="images/library.png" download>PNG</a></div></div></article></div>
 <p class="empty" id="empty" hidden>一致するモデルがありません。検索する言葉を変えてください。</p>
 <footer>Mermaid原本とPNGは各モデルから取得できます。根拠と未確認事項は、図の説明と一緒に確認してください。</footer>
```

#### `domain-models/library/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/domain-models/library/validation.json
+++ codex-2/domain-models/library/validation.json
@@ -3,10 +3,10 @@
     "library"
   ],
   "files": {
-    "catalog.json": "410de6caac08a1e88991e505aeb47830eb999db2e83746f3cf9f82838ff43487",
+    "catalog.json": "a915849d9ea0234e6055e466b12f834abc38ae0175b67a0d9a2f556c5f46d974",
     "diagrams/library.mmd": "dd9306de33ca1999fd937ce7953464d4268b0351e11999579cf90144145bf80e",
     "images/library.png": "2484259f3447bcda73c848dfa366aa75ecbbecf89785e1ed6d1b731175f4b6cc",
-    "index.html": "80eac84fa8772c16acfa37d3b77da98837daf001e1e05dbede7a8d0bd0663a6d"
+    "index.html": "9200f08fc3a72711bf5c5bd1bcefd793cc3da98aa4581aba86c081b88d80a6e1"
   },
   "images": {
     "library": {
```
