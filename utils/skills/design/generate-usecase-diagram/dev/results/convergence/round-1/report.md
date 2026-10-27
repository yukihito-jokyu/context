# 収束テスト ラウンド 1

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | done | 0.938 | 1.000 | 0.778 | 0.924 | 全員通過 | claude 0.875、codex 1.000 | 満たさない |
| T2-default | done | 0.487 | 1.000 | 0.699 | 0.887 | 全員通過 | claude 1.000、codex 1.000 | 満たさない |
| T3-edge | done | 0.950 | 1.000 | 0.808 | 0.937 | 全員通過 | claude 0.900、codex 1.000 | 満たさない |

## T1-typical

### 実行の状態（期待: done）

- claude-1: done
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: `T1-typical`, `claude-1`, `folders`, `library`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- claude-2: `T1-typical`, `claude-2`, `folders`, `library`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-1: `T1-typical`, `codex-1`, `folders`, `library`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-2: `T1-typical`, `codex-2`, `folders`, `library`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-usecase-diagram/preview.png`: claude-1, codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ claude-2/.skill-runs/generate-usecase-diagram/report.md
@@ -4,7 +4,7 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T1-typical/claude-1/artifacts/usecase/library/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T1-typical/claude-2/artifacts/usecase/library/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ claude-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,6 +1,6 @@
 {
-  "title": "蔵書検索",
-  "description": "図書館システムで、会員が蔵書を検索する。",
+  "title": "図書館システムのユースケース",
+  "description": "図書館システムで会員が蔵書を検索するようすを1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
```

#### `artifacts/usecase/library/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/catalog.json
+++ claude-2/artifacts/usecase/library/catalog.json
@@ -1,7 +1,7 @@
 {
   "schema_version": 1,
-  "title": "蔵書検索",
-  "description": "図書館システムで、会員が蔵書を検索する。",
+  "title": "図書館システムのユースケース",
+  "description": "図書館システムで会員が蔵書を検索するようすを1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
```

#### `artifacts/usecase/library/index.html`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/index.html
+++ claude-2/artifacts/usecase/library/index.html
@@ -1,10 +1,10 @@
 <!doctype html>
 <html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
-<title>蔵書検索 — ユースケース図</title>
+<title>図書館システムのユースケース — ユースケース図</title>
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>蔵書検索</h1><p>図書館システムで、会員が蔵書を検索する。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>図書館システムのユースケース</h1><p>図書館システムで会員が蔵書を検索するようすを1つの図で確認する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
 <section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>蔵書検索</h2><p>会員は図書館システムで蔵書を検索する。</p><div class="tags"><span class="tag">会員</span></div></div><a class="preview" href="diagrams/d01.png" data-title="蔵書検索"><img src="diagrams/d01.png" alt="蔵書検索：会員は図書館システムで蔵書を検索する。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
```

#### `artifacts/usecase/library/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/library/validation.json
+++ claude-2/artifacts/usecase/library/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "d01.pngの日本語（会員・図書館システム・蔵書を検索する）、関連線の接続、重なりの無さを確認した。HTMLカタログの一覧・検索・拡大・閉じる・原本表示・PNGとMermaid原本の取得リンクを確認した"
+    "notes": "PNGを目視し、アクター会員・境界図書館システム・ユースケース蔵書を検索する・関連線と日本語の欠けなしを確認。HTMLに図一覧とPNG・原本の参照があることを確認。"
   },
   "diagrams": [
     {
@@ -59,6 +59,6 @@
       "png_sha256": "7d1ce333f11da52e581e36a3a526c887cd1a91bbdad9a81b3809c35280af298f"
     }
   ],
-  "catalog_sha256": "22e80c3446efd2b14dd0d1401f4679b88d35eddf87ddcc59f1f4f3f958713ee8",
-  "html_sha256": "a2d884dc534443ce9b8d5b1ee5e1b99d898483a7788c033f9b970d58a7385fa9"
+  "catalog_sha256": "a610d7680b3c4074b3ee51996fdc2c6a16ebde15c5728b03b29f06acf95b8ead",
+  "html_sha256": "93eb1b161a4d858aede2aa83a2af1a4f7639119d76139f6d1e47e6dbd11d0003"
 }
```

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と codex-1）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ codex-1/.skill-runs/generate-usecase-diagram/report.md
@@ -4,7 +4,7 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T1-typical/claude-1/artifacts/usecase/library/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T1-typical/codex-1/artifacts/usecase/library/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
```


## T2-default

### 実行の状態（期待: done）

- claude-1: done
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: `T2-default`, `claude-1`, `folders`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- claude-2: `T2-default`, `claude-2`, `folders`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-1: `T2-default`, `codex-1`, `folders`, `library-borrowing`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-2: `T2-default`, `codex-2`, `folders`, `library-borrowing`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`

### 一部のエージェントだけが作った・変えたファイル

- `artifacts/usecase/catalog/catalog.json`: claude-1, claude-2
- `artifacts/usecase/catalog/diagrams/d01.mmd`: claude-1, claude-2
- `artifacts/usecase/catalog/diagrams/d01.png`: claude-1, claude-2
- `artifacts/usecase/catalog/index.html`: claude-1, claude-2
- `artifacts/usecase/catalog/validation.json`: claude-1, claude-2
- `artifacts/usecase/library-borrowing/catalog.json`: codex-1, codex-2
- `artifacts/usecase/library-borrowing/diagrams/d01.mmd`: codex-1, codex-2
- `artifacts/usecase/library-borrowing/diagrams/d01.png`: codex-1, codex-2
- `artifacts/usecase/library-borrowing/index.html`: codex-1, codex-2
- `artifacts/usecase/library-borrowing/validation.json`: codex-1, codex-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ claude-2/.skill-runs/generate-usecase-diagram/report.md
@@ -4,7 +4,7 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T2-default/claude-1/artifacts/usecase/catalog/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T2-default/claude-2/artifacts/usecase/catalog/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
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
```

#### `artifacts/usecase/catalog/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/catalog/validation.json
+++ claude-2/artifacts/usecase/catalog/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "PNGの日本語（会員・図書館システム・本を借りる）の欠けなし、関連線1本の重なりなし、アクターは境界外・ユースケースは境界内を確認。HTMLは一覧1件、検索、拡大ダイアログの開閉、原本表示、PNGと原本の取得リンクをpreviewで確認した"
+    "notes": "PNGの日本語ラベル（会員・図書館システム・本を借りる）と関連線、HTMLの一覧・検索・拡大・閉じる・原本表示・取得リンクを確認した"
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
+  "html_sha256": "ff951a20a8e2d073c0ce2ab1d5d847311a4ad9839c5b5ee5832eb7e0ba2f6a81"
 }
```

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と codex-1）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ codex-1/.skill-runs/generate-usecase-diagram/report.md
@@ -4,20 +4,20 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T2-default/claude-1/artifacts/usecase/catalog/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T2-default/codex-1/artifacts/usecase/library-borrowing/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
 ## 出力
 
-- `artifacts/usecase/catalog/catalog.json`（catalog カタログ情報）
-- `artifacts/usecase/catalog/index.html`（html HTMLカタログ）
-- `artifacts/usecase/catalog/validation.json`（validation 変換と検証の記録）
-- `artifacts/usecase/catalog/diagrams/d01.mmd`（mermaid Mermaid原本）
+- `artifacts/usecase/library-borrowing/catalog.json`（catalog カタログ情報）
+- `artifacts/usecase/library-borrowing/index.html`（html HTMLカタログ）
+- `artifacts/usecase/library-borrowing/validation.json`（validation 変換と検証の記録）
+- `artifacts/usecase/library-borrowing/diagrams/d01.mmd`（mermaid Mermaid原本）
 
 ## 既定値で決めた値
 
-- カタログ名（name）: "catalog"
+- なし
 
 ## 入力で読めなかった値
 
```


## T3-edge

### 実行の状態（期待: done）

- claude-1: done
- claude-2: done
- codex-1: done
- codex-2: done

### 新しく作った名前（names。先頭 40 件）

- claude-1: `Checkout`, `Customer`, `Order`, `Payment`, `T3-edge`, `claude-1`, `folders`, `order`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- claude-2: `Checkout`, `Customer`, `Order`, `Payment`, `T3-edge`, `claude-2`, `folders`, `order`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-1: `Checkout`, `Customer`, `Order`, `Payment`, `T3-edge`, `cmp`, `codex-1`, `folders`, `order`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`
- codex-2: `Checkout`, `Customer`, `Order`, `Payment`, `T3-edge`, `cmp`, `codex-2`, `folders`, `order`, `private`, `round-1`, `sd6ft4gx5v9c66gcpv2snfdc0000gn`, `var`

### 一部のエージェントだけが作った・変えたファイル

- `.skill-runs/generate-usecase-diagram/notes.md`: claude-2

### 中身の違い（抜粋）

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ claude-2/.skill-runs/generate-usecase-diagram/report.md
@@ -4,7 +4,7 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T3-edge/claude-1/artifacts/usecase/order/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T3-edge/claude-2/artifacts/usecase/order/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
@@ -29,4 +29,4 @@
 
 ## 補足
 
-- なし
+- 画像解析の初回指摘でアクター名が「願客」に見えるとの報告があったが、原本・catalog.json・index.htmlのすべてが「顧客」であり、拡大精査で「顧客」と正しく表示されていることを確認した（解析側の誤読）
```

#### `.skill-runs/generate-usecase-diagram/source/request.json`（claude-1 と claude-2）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/source/request.json
+++ claude-2/.skill-runs/generate-usecase-diagram/source/request.json
@@ -1,11 +1,11 @@
 {
   "title": "注文システムのユースケース",
-  "description": "顧客が注文システムで注文し、注文には支払いが含まれる。",
+  "description": "顧客が注文システムで注文し、注文には支払いが必須であることを1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
       "title": "顧客が注文する",
-      "summary": "顧客は注文する。注文には支払いが必須で含まれる。",
+      "summary": "顧客は注文する。注文には支払いが含まれる。",
       "source": "order.mmd"
     }
   ]
```

#### `artifacts/usecase/order/catalog.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/order/catalog.json
+++ claude-2/artifacts/usecase/order/catalog.json
@@ -1,12 +1,12 @@
 {
   "schema_version": 1,
   "title": "注文システムのユースケース",
-  "description": "顧客が注文システムで注文し、注文には支払いが含まれる。",
+  "description": "顧客が注文システムで注文し、注文には支払いが必須であることを1つの図で確認する。",
   "diagrams": [
     {
       "id": "d01",
       "title": "顧客が注文する",
-      "summary": "顧客は注文する。注文には支払いが必須で含まれる。",
+      "summary": "顧客は注文する。注文には支払いが含まれる。",
       "source": "diagrams/d01.mmd",
       "image": "diagrams/d01.png",
       "actors": [
```

#### `artifacts/usecase/order/index.html`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/order/index.html
+++ claude-2/artifacts/usecase/order/index.html
@@ -4,9 +4,9 @@
 <style>
 :root{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif;color:#19372f;background:#f5f4ee;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:50px 32px 72px}header{border-bottom:1px solid #cbd4c9;padding-bottom:30px;margin-bottom:28px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#607b70}h1{font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.3;margin:16px 0}header p{max-width:760px;line-height:1.85;color:#52675f}.toolbar{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:25px}.toolbar p{color:#61766b;font-size:13px}.toolbar input{border:1px solid #b7c6ba;background:white;border-radius:8px;padding:12px 14px;width:min(360px,65%);font:inherit;color:inherit}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:24px}article{border:1px solid #d4ddd2;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 20px #19372f05}article[hidden]{display:none}.card-body{padding:24px}.diagram-id{font-size:11px;letter-spacing:.12em;color:#678475}h2{font-size:22px;line-height:1.5;margin:8px 0 12px}article p{font-size:14px;line-height:1.85;color:#5a6e64}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}.tag{font-size:11px;border-radius:20px;background:#edf3ec;color:#416650;padding:5px 10px}.preview{display:block;background:#fafbf8;border-top:1px solid #edf0e9;border-bottom:1px solid #edf0e9;text-align:center;padding:12px;cursor:zoom-in}.preview img{display:block;width:100%;height:290px;object-fit:contain}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#1e7158;text-underline-offset:4px}.button{border:1px solid #b9cfc2;padding:9px 13px;border-radius:6px;text-decoration:none;font-size:12px}.button.primary{background:#225d49;color:#fff;border-color:#225d49}details{border-top:1px solid #e6ece3;padding-top:16px;margin-top:20px}summary{font-size:13px;cursor:pointer}pre{font:12px/1.8 ui-monospace,monospace;color:#355349;background:#f5f7f1;padding:16px;overflow:auto;border-radius:6px;max-height:400px}footer{margin-top:35px;color:#6b7d72;font-size:12px;line-height:1.9}dialog{width:min(96vw,1600px);max-width:96vw;max-height:95vh;border:1px solid #b4cbbd;border-radius:14px;padding:20px;background:#fff}dialog::backdrop{background:#102d22bb}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog .dialog-top{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:16px}button{font:inherit;cursor:pointer;border:1px solid #adc8b8;background:#f2f6ef;color:#19372f;padding:8px 16px;border-radius:6px}#empty{color:#61766b}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #af7119;outline-offset:4px}@media(max-width:600px){main{padding:30px 18px}h2{font-size:20px}.card-body{padding:20px}.preview img{height:230px}}
 </style></head><body><main>
-<header><div class="eyebrow">USE CASE CATALOG</div><h1>注文システムのユースケース</h1><p>顧客が注文システムで注文し、注文には支払いが含まれる。</p></header>
+<header><div class="eyebrow">USE CASE CATALOG</div><h1>注文システムのユースケース</h1><p>顧客が注文システムで注文し、注文には支払いが必須であることを1つの図で確認する。</p></header>
 <div class="toolbar"><p id="count">1 diagrams</p><input id="search" type="search" aria-label="図の題名・説明・アクターで検索" placeholder="題名・アクターで検索"></div>
-<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>顧客が注文する</h2><p>顧客は注文する。注文には支払いが必須で含まれる。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="顧客が注文する"><img src="diagrams/d01.png" alt="顧客が注文する：顧客は注文する。注文には支払いが必須で含まれる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
+<section id="cards" aria-label="ユースケース図一覧"><article id="d01"><div class="card-body"><span class="diagram-id">d01</span><h2>顧客が注文する</h2><p>顧客は注文する。注文には支払いが含まれる。</p><div class="tags"><span class="tag">顧客</span></div></div><a class="preview" href="diagrams/d01.png" data-title="顧客が注文する"><img src="diagrams/d01.png" alt="顧客が注文する：顧客は注文する。注文には支払いが含まれる。" loading="lazy"></a><div class="card-body"><div class="actions"><a class="button primary" href="diagrams/d01.png" download>PNGを取得</a><a class="button" href="diagrams/d01.mmd" download>Mermaid原本を取得</a></div><details><summary>Mermaid原本を表示</summary><pre><code>usecase-beta
 direction LR
 actor Customer(&quot;顧客&quot;)
 systemBoundary Order[&quot;注文システム&quot;]
```

#### `artifacts/usecase/order/validation.json`（claude-1 と claude-2）

```diff
--- claude-1/artifacts/usecase/order/validation.json
+++ claude-2/artifacts/usecase/order/validation.json
@@ -3,7 +3,7 @@
   "status": "passed",
   "visual_review": {
     "status": "reviewed",
-    "notes": "d01のPNGで顧客・注文システム境界・注文する・支払うの日本語表示、関連線とinclude点線矢印の接続、文字の欠けと重なりがないことを確認した。HTMLはpreviewで一覧・検索・拡大・閉じる・原本表示・取得リンクを確認した。"
+    "notes": "PNGの日本語（顧客・注文する・支払う・注文システム・include）と線の重なりなしを確認した。HTMLの一覧・検索・拡大・閉じる・原本表示・取得リンクをpreviewで確認した。入力のMermaid原本と図の意味（顧客--注文する、注文する..>include支払う）が一致していることを照合した。"
   },
   "diagrams": [
     {
@@ -71,6 +71,6 @@
       "png_sha256": "7660f14de941df4e626be561b48e6dac6a7b814b29353e4e1467c69b67bf0603"
     }
   ],
-  "catalog_sha256": "aa68007e0371644326604be68ecdc355d3c3908fc3cbbe2d0a232fe9245bd6e6",
-  "html_sha256": "49a6f93a35c8fac9bbf6649b324f3ce55a5031e72436842107e1c32808c8fdd6"
+  "catalog_sha256": "f033b73b0695eaee3d555054b517dc08bcddf83f84a0927f60c60ac9536e81e9",
+  "html_sha256": "a746cb7915c466f57c139a9664226776ed0e6b7911a0cbdaf1a19cdddc136caf"
 }
```

#### `.skill-runs/generate-usecase-diagram/report.md`（claude-1 と codex-1）

```diff
--- claude-1/.skill-runs/generate-usecase-diagram/report.md
+++ codex-1/.skill-runs/generate-usecase-diagram/report.md
@@ -4,7 +4,7 @@
 
 ## カタログ
 
-- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T3-edge/claude-1/artifacts/usecase/order/index.html)
+- [HTMLを開く](/private/var/folders/0m/sd6ft4gx5v9c66gcpv2snfdc0000gn/T/skill-foundation/generate-usecase-diagram/round-1/T3-edge/codex-1/artifacts/usecase/order/index.html)
 - 図: 1枚。原本・PNG・HTML・変換記録の対応を検査済み。
 - 目視: reviewed
 
```
