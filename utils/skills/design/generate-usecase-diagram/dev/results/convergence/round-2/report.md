# 収束テスト ラウンド 2

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | active、done | 0.944 | 1.000 | 1.000 | 0.930 | 全員通過 | claude 0.889、codex 1.000 | 満たさない |
| T2-default | done、failed | 0.944 | 1.000 | 1.000 | 0.875 | 全員通過 | claude 0.889、codex 1.000 | 満たさない |
| T3-edge | done、unused | 0.333 | 1.000 | 0.333 | 0.958 | 全員通過 | claude 1.000、codex 1.000 | 満たさない |

## T1-typical

### 実行の状態（期待: done）

- claude-1: active
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: なし
- claude-2: なし
- codex-1: なし
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-usecase-diagram/notes.md`: claude-2, codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/preview.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/preview.json
+++ claude-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "22e80c3446efd2b14dd0d1401f4679b88d35eddf87ddcc59f1f4f3f958713ee8",
-  "screenshot_sha256": "73006fc172cb91989441fa06aeb06455e0b56458341863f125628cbca4bce016",
+  "catalog_sha256": "d2f21ba926e1ecce814371406b0d5630204eb2403a4e79b29a6d855803853639",
+  "screenshot_sha256": "60f63476bdeec8f7b5552f56207ac9e44bc6342a695379bd024e2da3c9a0a5df",
   "checks": {
     "cards": 1,
     "imagesValid": true,
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ claude-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,11 +1,11 @@
 {
   "title": "蔵書検索",
-  "description": "図書館システムで、会員が蔵書を検索する。",
+  "description": "会員が図書館システムで蔵書を検索する。",
   "diagrams": [
     {
       "id": "d01",
       "title": "蔵書検索",
-      "summary": "会員は図書館システムで蔵書を検索する。",
+      "summary": "会員は蔵書を検索する。",
       "mermaid": "usecase-beta\ndirection LR\nactor A01(\"会員\")\nsystemBoundary S01[\"図書館システム\"]\n  U01(\"蔵書を検索する\")\nend\nA01 -- U01\n"
     }
   ]
```

#### `artifacts/usecase/library/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/catalog.json
+++ claude-2/artifacts/usecase/library/catalog.json
@@ -1,12 +1,12 @@
 {
   "schema_version": 1,
   "title": "蔵書検索",
-  "description": "図書館システムで、会員が蔵書を検索する。",
+  "description": "会員が図書館システムで蔵書を検索する。",
   "diagrams": [
     {
       "id": "d01",
       "title": "蔵書検索",
-      "summary": "会員は図書館システムで蔵書を検索する。",
+      "summary": "会員は蔵書を検索する。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
       "actors": [
```

#### `artifacts/usecase/library/index.html`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/index.html
+++ claude-2/artifacts/usecase/library/index.html
@@ -4,9 +4,9 @@
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>蔵書検索</h1><p>図書館システムで、会員が蔵書を検索する。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>蔵書検索</h1><p>会員が図書館システムで蔵書を検索する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>蔵書検索</h2><p>会員は図書館システムで蔵書を検索する。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="蔵書検索"><img src="diagrams/d01.png" alt="蔵書検索：会員は図書館システムで蔵書を検索する。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>蔵書検索</h2><p>会員は蔵書を検索する。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="蔵書検索"><img src="diagrams/d01.png" alt="蔵書検索：会員は蔵書を検索する。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor A01(&quot;会員&quot;)
 systemBoundary S01[&quot;図書館システム&quot;]
@@ -14,7 +14,7 @@
 end
 A01 -- U01
 </code></pre></details></div></article></section><p id="empty" hidden>一致する図はありません。</p>
-<footer>図を選ぶとPNGを拡大できます。Mermaid原本から図を編集・再生成できます。<br>目視確認：確認待ち · <a href="catalog.json" download>カタログ情報</a> · <a href="validation.json" download>変換・検証記録</a></footer>
+<footer>図を選ぶとPNGを拡大できます。Mermaid原本から図を編集・再生成できます。<br>目視確認：確認済み（内容は検証記録を参照） · <a href="catalog.json" download>カタログ情報</a> · <a href="validation.json" download>変換・検証記録</a></footer>
 </main><dialog id="viewer" aria-labelledby="viewer-title"><div class="dialog-top"><strong id="viewer-title"></strong><button id="close" type="button">閉じる</button></div><img id="viewer-image" alt=""></dialog>
 <script>
 const cards=[...document.querySelectorAll('article')],search=document.getElementById('search'),dialog=document.getElementById('viewer');
```

#### `artifacts/usecase/library/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/validation.json
+++ claude-2/artifacts/usecase/library/validation.json
@@ -2,8 +2,8 @@
   "schema_version": 1,
   "status": "passed",
   "visual_review": {
-    "status": "pending",
-    "notes": ""
+    "status": "reviewed",
+    "notes": "PNGの日本語・関連線・境界、HTMLの一覧・検索・拡大・原本取得を確認した"
   },
   "diagrams": [
     {
@@ -59,6 +59,6 @@
       "png_sha256": "7d1ce333f11da52e581e36a3a526c887cd1a91bbdad9a81b3809c35280af298f"
     }
   ],
-  "catalog_sha256": "22e80c3446efd2b14dd0d1401f4679b88d35eddf87ddcc59f1f4f3f958713ee8",
-  "html_sha256": "e8e51aa7ee180758f40816a220fac23b039694c7b9b796c75271c3803342ebc1"
+  "catalog_sha256": "d2f21ba926e1ecce814371406b0d5630204eb2403a4e79b29a6d855803853639",
+  "html_sha256": "0886fdc04b915a0654d3a7a0213fd221f6b05710299760611f131fdad019e048"
 }
```

#### `.skill-runs/generate-usecase-diagram/preview.json`（claude-1 と codex-1）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/preview.json
+++ codex-1/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "22e80c3446efd2b14dd0d1401f4679b88d35eddf87ddcc59f1f4f3f958713ee8",
-  "screenshot_sha256": "73006fc172cb91989441fa06aeb06455e0b56458341863f125628cbca4bce016",
+  "catalog_sha256": "644bc64af1980fbf0bb9e590da08d4b35aa6aec449a276707ce8687bec0f4a1e",
+  "screenshot_sha256": "d29b1f7be7679ed2512c3c93e6f95e7eaf122aa8a8f21a315841989a712e8673",
   "checks": {
     "cards": 1,
     "imagesValid": true,
```


## T2-default

### 実行の状態（期待: done）

- claude-1: failed
- claude-2: failed
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: なし
- claude-2: なし
- codex-1: なし
- codex-2: なし

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-usecase-diagram/notes.md`: claude-1, codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/preview.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/preview.json
+++ claude-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "e6b6f7516077a06a94bad45dfd558fc25e1361ff0a8538fa7fcf3efc12a5b75d",
-  "screenshot_sha256": "c957783ac6fcd043c60650ef2f5431a5a603c4839d22f4d61f193b139b1327e5",
+  "catalog_sha256": "8d506748f477d8e6dc1c57938fd468b30ba120374c694facb858f83181d4d89f",
+  "screenshot_sha256": "b9753878838ab39b334180c10200e496b2ec30d9ca1a376c0904a55259b93571",
   "checks": {
     "cards": 1,
     "imagesValid": true,
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ claude-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,6 +1,6 @@
 {
   "title": "図書館システムのユースケース",
-  "description": "会員が図書館システムで本を借りるユースケースを確認する。",
+  "description": "会員が図書館システムで本を借りる様子を1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
```

#### `artifacts/usecase/catalog/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/catalog/catalog.json
+++ claude-2/artifacts/usecase/catalog/catalog.json
@@ -1,7 +1,7 @@
 {
   "schema_version": 1,
   "title": "図書館システムのユースケース",
-  "description": "会員が図書館システムで本を借りるユースケースを確認する。",
+  "description": "会員が図書館システムで本を借りる様子を1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
```

#### `artifacts/usecase/catalog/index.html`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/catalog/index.html
+++ claude-2/artifacts/usecase/catalog/index.html
@@ -4,7 +4,7 @@
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>図書館システムのユースケース</h1><p>会員が図書館システムで本を借りるユースケースを確認する。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>図書館システムのユースケース</h1><p>会員が図書館システムで本を借りる様子を1つの図で確認する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
 <section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>会員が本を借りる</h2><p>会員は図書館システムで本を借りる。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="会員が本を借りる"><img src="diagrams/d01.png" alt="会員が本を借りる：会員は図書館システムで本を借りる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
@@ -14,7 +14,7 @@
 end
 A01 -- U01
 </code></pre></details></div></article></section><p id="empty" hidden>一致する図はありません。</p>
-<footer>図を選ぶとPNGを拡大できます。Mermaid原本から図を編集・再生成できます。<br>目視確認：確認済み（内容は検証記録を参照） · <a href="catalog.json" download>カタログ情報</a> · <a href="validation.json" download>変換・検証記録</a></footer>
+<footer>図を選ぶとPNGを拡大できます。Mermaid原本から図を編集・再生成できます。<br>目視確認：確認待ち · <a href="catalog.json" download>カタログ情報</a> · <a href="validation.json" download>変換・検証記録</a></footer>
 </main><dialog id="viewer" aria-labelledby="viewer-title"><div class="dialog-top"><strong id="viewer-title"></strong><button id="close" type="button">閉じる</button></div><img id="viewer-image" alt=""></dialog>
 <script>
 const cards=[...document.querySelectorAll('article')],search=document.getElementById('search'),dialog=document.getElementById('viewer');
```

#### `artifacts/usecase/catalog/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/catalog/validation.json
+++ claude-2/artifacts/usecase/catalog/validation.json
@@ -2,8 +2,8 @@
   "schema_version": 1,
   "status": "passed",
   "visual_review": {
-    "status": "reviewed",
-    "notes": "previewによるHTML操作検査（一覧1件、検索、拡大ダイアログの開閉、原本表示、PNGと原本の取得リンク4件、外部リンクなし、画面のはみ出しなし）と、buildによるPNG生成検査を確認した"
+    "status": "pending",
+    "notes": ""
   },
   "diagrams": [
     {
@@ -59,6 +59,6 @@
       "png_sha256": "478f386cd66c3711e9c8378e809cda56ae52d881d7d8096acd1766e8d8dc550b"
     }
   ],
-  "catalog_sha256": "e6b6f7516077a06a94bad45dfd558fc25e1361ff0a8538fa7fcf3efc12a5b75d",
-  "html_sha256": "4b1b8df366d893c72ceec303adc3589608c98034b917e80ec3727ecfd0f17056"
+  "catalog_sha256": "8d506748f477d8e6dc1c57938fd468b30ba120374c694facb858f83181d4d89f",
+  "html_sha256": "850326f9dfa8e2f95baa107e5627704c1c3a44eac12e4073de23aad3c6d6e1a9"
 }
```

#### `.skill-runs/generate-usecase-diagram/notes.md`（claude-1 と codex-1）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/notes.md
+++ codex-1/.skill-runs/generate-usecase-diagram/notes.md
@@ -1 +1 @@
-- PNGの日本語表示と線の重なりについて、画像解析ツールが利用できなかったため目視確認は実施できていない（previewの操作検査とbuildのPNG検査は通過）
+- なし
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
- codex-1: `Checkout`, `Customer`, `Order`, `Payment`, `order`
- codex-2: `Checkout`, `Customer`, `Order`, `Payment`, `order`

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-usecase-diagram/notes.md`: codex-1, codex-2
- `.skill-runs/generate-usecase-diagram/preview.json`: codex-1, codex-2
- `.skill-runs/generate-usecase-diagram/preview.png`: codex-1, codex-2
- `.skill-runs/generate-usecase-diagram/source/order.mmd`: codex-1, codex-2
- `.skill-runs/generate-usecase-diagram/source/request.json`: codex-1, codex-2
- `artifacts/usecase/order/catalog.json`: codex-1, codex-2
- `artifacts/usecase/order/diagrams/d01.mmd`: codex-1, codex-2
- `artifacts/usecase/order/diagrams/d01.png`: codex-1, codex-2
- `artifacts/usecase/order/index.html`: codex-1, codex-2
- `artifacts/usecase/order/validation.json`: codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/preview.json`（codex-1 と codex-2）

```diff
--- codex-1/.skill-runs/generate-usecase-diagram/preview.json
+++ codex-2/.skill-runs/generate-usecase-diagram/preview.json
@@ -1,6 +1,6 @@
 {
-  "catalog_sha256": "5b5acc11f0f1f8ed321b15041aa271ef438ad3a37aab14807b4388dc682bcfca",
-  "screenshot_sha256": "9f2971d04263969aee833246c73ae70bcf279213cd2c2b410630a4b86f5ca95f",
+  "catalog_sha256": "8ea250fd8c63558e83c6688f5774cce4456c8601c1bc6b2f282ec2e0af11c2f8",
+  "screenshot_sha256": "adf0a42789295e232bc575ba3cc513b4fa4242ea7a92d70c3f66f7623fafb0cf",
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
       "title": "顧客が注文する",
-      "summary": "顧客が注文する。注文には支払いを含む。",
+      "summary": "顧客は注文する。注文には支払いが必須処理として含まれる。",
       "source": "order.mmd"
     }
   ]
```

#### `artifacts/usecase/order/catalog.json`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/order/catalog.json
+++ codex-2/artifacts/usecase/order/catalog.json
@@ -6,7 +6,7 @@
     {
       "id": "d01",
       "title": "顧客が注文する",
-      "summary": "顧客が注文する。注文には支払いを含む。",
+      "summary": "顧客は注文する。注文には支払いが必須処理として含まれる。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
       "actors": [
```

#### `artifacts/usecase/order/index.html`（codex-1 と codex-2）

```diff
--- codex-1/artifacts/usecase/order/index.html
+++ codex-2/artifacts/usecase/order/index.html
@@ -6,7 +6,7 @@
 </style></head><body><main>
 <header><div class="eyebrow">USE CASE CATALOG</div><h1>注文システムのユースケース</h1><p>顧客の注文と、注文に含まれる支払いを1枚の図で確認する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>顧客が注文する</h2><p>顧客が注文する。注文には支払いを含む。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="顧客が注文する"><img src="diagrams/d01.png" alt="顧客が注文する：顧客が注文する。注文には支払いを含む。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>顧客が注文する</h2><p>顧客は注文する。注文には支払いが必須処理として含まれる。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="顧客が注文する"><img src="diagrams/d01.png" alt="顧客が注文する：顧客は注文する。注文には支払いが必須処理として含まれる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
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
-    "notes": "PNG全1枚とHTMLの保存画面を目視し、日本語、システム境界、顧客と注文の関連、注文から支払いへのinclude矢印に欠けや重なりがないことを確認した。previewの一覧・検索・拡大・閉じる・原本表示・取得リンクの操作検査に合格し、原本は入力とバイト単位で一致した。"
+    "notes": "全1図のPNGとHTMLプレビューを開き、日本語、境界外の顧客、境界内の注文・支払い、注文から支払いへのinclude矢印に欠けや重なりがないことを確認。previewによる一覧・検索・拡大・閉じる・原本表示・取得リンクの動作検査に合格し、保存原本と入力原本のバイト単位の一致も確認した。"
   },
   "diagrams": [
     {
@@ -71,6 +71,6 @@
       "png_sha256": "7660f14de941df4e626be561b48e6dac6a7b814b29353e4e1467c69b67bf0603"
     }
   ],
-  "catalog_sha256": "5b5acc11f0f1f8ed321b15041aa271ef438ad3a37aab14807b4388dc682bcfca",
-  "html_sha256": "7ab4e1e0ca95d350efe21eea5d8e39e33dfde97956e5e2040b0fbf63c2c91af2"
+  "catalog_sha256": "8ea250fd8c63558e83c6688f5774cce4456c8601c1bc6b2f282ec2e0af11c2f8",
+  "html_sha256": "43a2d29297316e0dc283885d1d1ae3a56522848e9a2d71469316ec9c0a89a09d"
 }
```
