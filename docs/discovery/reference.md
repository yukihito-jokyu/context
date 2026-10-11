---
title: reference — 現物から合わせるべき仕様を抽出する
sidebar_label: reference
---

# reference

既存コード、画面、仕様、過去の成果物に合わせたいときに使います。見た目のコピーだけでなく、命名や責務、動作の意図を取り出します。

## 渡す情報

参照対象の場所、今回の対象、合わせたい観点を渡します。

## 依頼例

```text
referenceを使って、既存の顧客一覧を参考に依頼一覧の設計ルールを整理してください。検索、空状態、エラー表示を合わせたいです。顧客固有の表示項目は引き継ぎません。
```

## 進め方

1. 参照対象を実際に読み、仕様や設計意図を抽出します。
2. 合わせるべき点と、今回合わせなくてよい点を分けます。
3. 参照対象との差分と適用方針を示します。

## 成果物の例

指定されたruleの設定と、contextの実ファイルを参照した分析です。

**到達点：参照分析。**

### 実行した依頼

```text
ruleのdocusaurus.config.tsとcontextの設定・検索・utilsカタログを実際に読み、実成果物展示へ合わせるべき点と差分を抽出してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
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
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/reference/output.md#download)
- [実行入力の原本](pathname:///examples/reference/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/reference/execution.json#download)

### 確認した結果

- SKILL.mdを読み、今回の実要件と参照対象へ適用して出力を保存。内容の人間確認は未実施。

## 確認するポイント

根拠のファイルや箇所を開けるか、参照のどの部分を採用したかが明確かを確認します。

## 関連するスキル

- [plan](../planning/plan.md)：適用方針を計画にする。

## 正本を読む

詳細な手順と制約は[referenceのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/reference/SKILL.md)を参照してください。
