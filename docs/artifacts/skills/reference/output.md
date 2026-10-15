# Reference Analysis

## 1. 参照対象

- ruleリポジトリのdocusaurus.config.tsを実際に読んだ。
- contextのdocusaurus.config.ts、plugins/site-search/index.js、utils/skills/README.mdを実際に読んだ。
- Docusaurus 3.10.2の公式Assets資料を確認した。https://docusaurus.io/docs/markdown-features/assets

## 2. 抽出した意図

- ruleはmarkdown.formatをmdにし、Markdownリンクと画像の欠落をビルドで検出する。
- ruleは日本語を既定ロケールとし、独自site-searchプラグインを使う。
- contextの検索は公開ドキュメントの本文を読んで索引を作る。原本を文書に含めると索引にも入る。
- contextの共通スキルは6分類に所属し、SKILL.mdが正本、READMEがカタログである。

## 3. 合わせるべき点

- 日本語、md形式、欠落リンク検出、独自検索という設定意図。
- utilsの分類とスキル名をガイドの構造に対応させる。
- 原本を別の説明文で置き換えず、実際に保存したファイルを配る。

## 4. 合わせなくてよい点

- ruleのurlはlocalhost、baseUrlは/。contextではGitHub Pagesの/context/が必要。
- ruleのルール集向けのナビゲーション名やdocsルート。

## 5. 今回の作業への適用方針

- 成果物をdocs/artifacts/examplesへ保存し、静的配信元に設定する。
- artifacts配下はドキュメント探索から除外する。
- Markdownの画像・ファイル参照を使う。原本取得にはルーターを通さないダウンロードリンクを用意する。
- この分析はファイル確認と公式資料の読解結果。実サイトの公開成功を示すものではない。
