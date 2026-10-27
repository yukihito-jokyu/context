# 収束テスト ラウンド 3

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | done | 1.000 | 1.000 | 0.000 | 0.998 | 全員通過 | codex 1.000 | 満たさない |
| T2-default | done | 1.000 | 1.000 | 1.000 | 0.951 | 全員通過 | codex 1.000 | 満たす |
| T3-edge | done | 1.000 | 1.000 | 1.000 | 0.923 | 全員通過 | codex 1.000 | 満たす |
| T4-holdout | done | 1.000 | 1.000 | 1.000 | 0.939 | 全員通過 | codex 1.000 | 満たす |

## T1-typical

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: `PNG1`
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `artifacts/usecase/library/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/library/validation.json
+++ codex-2/artifacts/usecase/library/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "PNG1図と保存したHTML画面を開き、日本語の表示、会員が境界の外にあること、図書館システム内の蔵書検索への関連線を確認した。HTMLの一覧・検索・拡大・閉じる・原本表示・取得リンクの操作検査も確認した。要件にない機能や関係の追加はなく、題名は蔵書検索、図は1枚である。"
+    "notes": "PNG 1枚とHTMLカタログの保存画面を目視した。会員が境界の外、蔵書を検索する機能が図書館システムの境界内にあり、関連線が1本であること、日本語に欠けや重なりがないこと、題名が蔵書検索であることを確認した。previewの操作検査で一覧・検索・拡大と閉じる・原本表示・取得リンクが正常であることを確認した。要件にない機能や関係は含まれていない。"
   },
   "diagrams": [
     {
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

#### `.skill-runs/generate-usecase-diagram/preview.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/preview.json
+++ codex-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "66d8dfc41bd84eacf09ac23efa75131345384d0280f860dff681dcf3b71ec8ad",
-  "screenshot_sha256": "e28bd2ef52cedc862ef26b27a635c573d722204229343345c3c5f8b89d0c698d",
+  "catalog_sha256": "b89fba9157d44cb00fc732c4acd5bcb421c06c7f74432426b6215502b1f38fac",
+  "screenshot_sha256": "21aff20fb04cb88a7ec22e189856bbe9b185555d759b54bb780c51e32e3bce6f",
   "checks": {
     "cards": 1,
     "imagesValid": true,
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ codex-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -5,7 +5,7 @@
     {
       "id": "d01",
       "title": "会員が本を借りる",
-      "summary": "会員と「本を借りる」の関係を示す。",
+      "summary": "会員と「本を借りる」の関連を示す。",
       "mermaid": "usecase-beta\ndirection LR\nactor A01(\"会員\")\nsystemBoundary S01[\"図書館システム\"]\n  U01(\"本を借りる\")\nend\nA01 -- U01\n"
     }
   ]
```

#### `artifacts/usecase/catalog/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/catalog/catalog.json
+++ codex-2/artifacts/usecase/catalog/catalog.json
@@ -6,7 +6,7 @@
     {
       "id": "d01",
       "title": "会員が本を借りる",
-      "summary": "会員と「本を借りる」の関係を示す。",
+      "summary": "会員と「本を借りる」の関連を示す。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
       "actors": [
```

#### `artifacts/usecase/catalog/index.html`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/catalog/index.html
+++ codex-2/artifacts/usecase/catalog/index.html
@@ -6,7 +6,7 @@
 </style></head><body><main>
 <header><div class="eyebrow">USE CASE CATALOG</div><h1>図書館システムのユースケース</h1><p>会員が図書館システムで本を借りる。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>会員が本を借りる</h2><p>会員と「本を借りる」の関係を示す。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="会員が本を借りる"><img src="diagrams/d01.png" alt="会員が本を借りる：会員と「本を借りる」の関係を示す。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>会員が本を借りる</h2><p>会員と「本を借りる」の関連を示す。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="会員が本を借りる"><img src="diagrams/d01.png" alt="会員が本を借りる：会員と「本を借りる」の関連を示す。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor A01(&quot;会員&quot;)
 systemBoundary S01[&quot;図書館システム&quot;]
```

#### `artifacts/usecase/catalog/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/catalog/validation.json
+++ codex-2/artifacts/usecase/catalog/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "PNG全1図と保存したHTML画面を目視し、日本語の欠けがなく、会員が図書館システム境界の外、本を借りるが境界の中にあり、関連線に不要な重なりがないことを確認した。入力どおり会員1名とユースケース1件のみを描いた。previewによる一覧・検索・拡大・閉じる・原本表示・PNGと原本の取得リンクの検査成功も確認した。"
+    "notes": "PNG全1図とHTML一覧の保存画面を開き、日本語、会員が境界外・本を借りるが境界内であること、関連線に重なりがないこと、依頼どおりアクター1つとユースケース1つだけであることを目視確認した。previewの操作検査で検索・拡大と閉じる・原本表示・PNGと原本の取得リンクを確認した。"
   },
   "diagrams": [
     {
@@ -59,6 +59,6 @@
       "png_sha256": "478f386cd66c3711e9c8378e809cda56ae52d881d7d8096acd1766e8d8dc550b"
     }
   ],
-  "catalog_sha256": "66d8dfc41bd84eacf09ac23efa75131345384d0280f860dff681dcf3b71ec8ad",
-  "html_sha256": "4f2dfe8445d2fb56369b1703d51270ce100402078e8ad34ea16e2acaae612622"
+  "catalog_sha256": "b89fba9157d44cb00fc732c4acd5bcb421c06c7f74432426b6215502b1f38fac",
+  "html_sha256": "313faf0d4214de3f7c0a360707e3b07a435b837acf802fbd3e9369408a5161ac"
 }
```


## T3-edge

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: `Checkout`, `Customer`, `Order`, `Payment`, `order`
- codex-2: `Checkout`, `Customer`, `Order`, `Payment`, `order`

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/preview.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/preview.json
+++ codex-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "6737b6c688393839295df09e38d23b91cd74ebe186bc26f74719bd44ef840714",
-  "screenshot_sha256": "d301ec988b4ee661c71697a07e0230c7524da8b52dbafc7d7c9d6e3fce02e8b2",
+  "catalog_sha256": "6690892e2bca6dee7c5849fa1b81bc94d9768c3b48d82e35744d4d9b69dbbff4",
+  "screenshot_sha256": "2aba6e8bf7cc8e49743e5265693e1d04d581bbf2e33c5f0ce49844406883e957",
   "checks": {
     "cards": 1,
     "imagesValid": true,
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ codex-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,11 +1,11 @@
 {
   "title": "注文システムのユースケース",
-  "description": "顧客の注文と、注文に含まれる支払いを1枚の図で確認する。",
+  "description": "顧客の注文と、注文に必須の支払いを1枚の図で確認する。",
   "diagrams": [
     {
       "id": "d01",
-      "title": "注文する",
-      "summary": "顧客は注文する。注文には支払いを含む。",
+      "title": "顧客が注文する",
+      "summary": "顧客は注文する。注文には支払いが必須である。",
       "source": "order.mmd"
     }
   ]
```

#### `artifacts/usecase/order/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/order/catalog.json
+++ codex-2/artifacts/usecase/order/catalog.json
@@ -1,12 +1,12 @@
 {
   "schema_version": 1,
   "title": "注文システムのユースケース",
-  "description": "顧客の注文と、注文に含まれる支払いを1枚の図で確認する。",
+  "description": "顧客の注文と、注文に必須の支払いを1枚の図で確認する。",
   "diagrams": [
     {
       "id": "d01",
-      "title": "注文する",
-      "summary": "顧客は注文する。注文には支払いを含む。",
+      "title": "顧客が注文する",
+      "summary": "顧客は注文する。注文には支払いが必須である。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
       "actors": [
```

#### `artifacts/usecase/order/index.html`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/order/index.html
+++ codex-2/artifacts/usecase/order/index.html
@@ -4,9 +4,9 @@
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>注文システムのユースケース</h1><p>顧客の注文と、注文に含まれる支払いを1枚の図で確認する。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>注文システムのユースケース</h1><p>顧客の注文と、注文に必須の支払いを1枚の図で確認する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>注文する</h2><p>顧客は注文する。注文には支払いを含む。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="注文する"><img src="diagrams/d01.png" alt="注文する：顧客は注文する。注文には支払いを含む。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>顧客が注文する</h2><p>顧客は注文する。注文には支払いが必須である。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="顧客が注文する"><img src="diagrams/d01.png" alt="顧客が注文する：顧客は注文する。注文には支払いが必須である。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor Customer(&quot;顧客&quot;)
 systemBoundary Order[&quot;注文システム&quot;]
```

#### `artifacts/usecase/order/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/order/validation.json
+++ codex-2/artifacts/usecase/order/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "PNGとHTMLの保存画面で日本語、境界外の顧客、境界内の注文と支払い、注文から支払いへのincludeを確認した。previewの一覧・検索・拡大と閉じる・原本表示・取得リンクの操作検査に合格した。Mermaid原本は入力本文と一致し、改変していない。"
+    "notes": "PNG全1図とHTML画面を目視し、日本語の欠けがなく、顧客が注文システム境界の外、注文する・支払うが境界の中にあり、関連線とCheckoutからPaymentへのinclude矢印が重ならず読めることを確認した。previewの一覧1件・検索・拡大と閉じる・原本表示・PNGと原本の取得リンクの操作検査に合格した。入力原本と出力原本はバイト単位で一致し、要素IDと本文を保持している。"
   },
   "diagrams": [
     {
@@ -71,6 +71,6 @@
       "png_sha256": "7660f14de941df4e626be561b48e6dac6a7b814b29353e4e1467c69b67bf0603"
     }
   ],
-  "catalog_sha256": "6737b6c688393839295df09e38d23b91cd74ebe186bc26f74719bd44ef840714",
-  "html_sha256": "f34b1655edf11da617ef072e90b5c57eb896ffa6df1f8b6ede023adb7e6d8d87"
+  "catalog_sha256": "6690892e2bca6dee7c5849fa1b81bc94d9768c3b48d82e35744d4d9b69dbbff4",
+  "html_sha256": "9cf3037b0241c634571ac0a75365322b712143644575ca7a4499e0f32c63f0c5"
 }
```


## T4-holdout

### 実行の状態（期待: done）

- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- codex-1: なし
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/preview.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/preview.json
+++ codex-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "26a22fde9586608ea6f3127af864991979cd233fa6dfa783954377c4e437934c",
-  "screenshot_sha256": "c43ce6fd484c9f3a46375e0111eb363f8a0cc6722ea1972c2625f8324b4f2876",
+  "catalog_sha256": "1df3e5ca450d2f60008da292f01c708bf91d97b8a2fd94c853785a9f7557e277",
+  "screenshot_sha256": "72f93b0ce6caf137d53c57749bb38cf3331a10bf8dd945360fad63391b20b107",
   "checks": {
     "cards": 2,
     "imagesValid": true,
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ codex-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,16 +1,16 @@
 {
   "title": "病院の予約システムのユースケース",
-  "description": "患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。",
+  "description": "患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。機能はこの2つのみ。",
   "diagrams": [
     {
       "id": "d01",
-      "title": "患者：診療予約する",
+      "title": "患者：診療予約",
       "summary": "患者は病院の予約システムで診療予約できる。",
       "mermaid": "usecase-beta\ndirection LR\nactor A01(\"患者\")\nsystemBoundary S01[\"病院の予約システム\"]\n  U01(\"診療予約する\")\nend\nA01 -- U01\n"
     },
     {
       "id": "d02",
-      "title": "受付担当：予約を確認する",
+      "title": "受付担当：予約確認",
       "summary": "受付担当は病院の予約システムで予約を確認できる。",
       "mermaid": "usecase-beta\ndirection LR\nactor A01(\"受付担当\")\nsystemBoundary S01[\"病院の予約システム\"]\n  U01(\"予約を確認する\")\nend\nA01 -- U01\n"
     }
```

#### `artifacts/usecase/clinic/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/clinic/catalog.json
+++ codex-2/artifacts/usecase/clinic/catalog.json
@@ -1,11 +1,11 @@
 {
   "schema_version": 1,
   "title": "病院の予約システムのユースケース",
-  "description": "患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。",
+  "description": "患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。機能はこの2つのみ。",
   "diagrams": [
     {
       "id": "d01",
-      "title": "患者：診療予約する",
+      "title": "患者：診療予約",
       "summary": "患者は病院の予約システムで診療予約できる。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
@@ -24,7 +24,7 @@
     },
     {
       "id": "d02",
-      "title": "受付担当：予約を確認する",
+      "title": "受付担当：予約確認",
       "summary": "受付担当は病院の予約システムで予約を確認できる。",
       "source": "diagrams/d02.mmd",
       "image": "diagrams/d02.png",
```

#### `artifacts/usecase/clinic/index.html`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/clinic/index.html
+++ codex-2/artifacts/usecase/clinic/index.html
@@ -4,9 +4,9 @@
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>病院の予約システムのユースケース</h1><p>患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>病院の予約システムのユースケース</h1><p>患者の診療予約と受付担当の予約確認を、役割別の2枚のユースケース図で示す。機能はこの2つのみ。</p></header>
 <div class="toolbar"><p id="count">2 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>患者：診療予約する</h2><p>患者は病院の予約システムで診療予約できる。</p><div class="tags"><span class="tag">患者</span></div></div><a class="preview" href="diagrams/d01.png" data-title="患者：診療予約する"><img src="diagrams/d01.png" alt="患者：診療予約する：患者は病院の予約システムで診療予約できる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>患者：診療予約</h2><p>患者は病院の予約システムで診療予約できる。</p><div class="tags"><span class="tag">患者</span></div></div><a class="preview" href="diagrams/d01.png" data-title="患者：診療予約"><img src="diagrams/d01.png" alt="患者：診療予約：患者は病院の予約システムで診療予約できる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor A01(&quot;患者&quot;)
 systemBoundary S01[&quot;病院の予約システム&quot;]
@@ -14,7 +14,7 @@
 end
 A01 -- U01
 </code></pre></details></div></article>
-<article id="d02"><div class="card-body"><span class="diagram-id">d02</span><h2>受付担当：予約を確認する</h2><p>受付担当は病院の予約システムで予約を確認できる。</p><div class="tags"><span class="tag">受付担当</span></div></div><a class="preview" href="diagrams/d02.png" data-title="受付担当：予約を確認する"><img src="diagrams/d02.png" alt="受付担当：予約を確認する：受付担当は病院の予約システムで予約を確認できる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d02.png" download>PNGを取得</a><a class="button" href="diagrams/d02.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<article id="d02"><div class="card-body"><span class="diagram-id">d02</span><h2>受付担当：予約確認</h2><p>受付担当は病院の予約システムで予約を確認できる。</p><div class="tags"><span class="tag">受付担当</span></div></div><a class="preview" href="diagrams/d02.png" data-title="受付担当：予約確認"><img src="diagrams/d02.png" alt="受付担当：予約確認：受付担当は病院の予約システムで予約を確認できる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d02.png" download>PNGを取得</a><a class="button" href="diagrams/d02.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor A01(&quot;受付担当&quot;)
 systemBoundary S01[&quot;病院の予約システム&quot;]
```

#### `artifacts/usecase/clinic/validation.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/clinic/validation.json
+++ codex-2/artifacts/usecase/clinic/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "PNG全2図とカタログの保存画面を開き、日本語の欠けがないこと、アクターが境界外・ユースケースが境界内に配置され関連線が接続されていること、患者の診療予約と受付担当の予約確認の2機能のみであることを確認した。previewで一覧2件・検索・拡大と閉じる・原本表示・ローカルの取得リンクを検証した。"
+    "notes": "全2枚のPNGとカタログ画面を開き、日本語、境界外の患者・受付担当、境界内の診療予約・予約確認、関連線の重なりがないことを目視確認した。previewで一覧・検索・拡大と閉じる・原本表示・取得リンクを検査し、要求された2機能のみであることを照合した。"
   },
   "diagrams": [
     {
@@ -111,6 +111,6 @@
       "png_sha256": "0269e05a16ad292d43b0f31647f49bb9f482e4d58ead3411ee3aab957e1d6860"
     }
   ],
-  "catalog_sha256": "26a22fde9586608ea6f3127af864991979cd233fa6dfa783954377c4e437934c",
-  "html_sha256": "9b2dc0a5e371c7b80c81c1a91cfb7bd9fc80b5bcb4814dc7eb60503272b59177"
+  "catalog_sha256": "1df3e5ca450d2f60008da292f01c708bf91d97b8a2fd94c853785a9f7557e277",
+  "html_sha256": "1e09aa7ec641846c718dfb80931dd2dd9819fb79147d68cf8c7969d8503a43af"
 }
```
