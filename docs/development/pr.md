---
title: pr — 変更理由と確認結果をPRにまとめる
sidebar_label: pr
---

# pr

コミットした変更をGitHubでレビューしてもらいたいときに使います。対象ブランチの内容を確認し、プロジェクトのテンプレートでPRを作成します。

## 渡す情報

対象ブランチ、関連Issue、変更内容、検証結果、レビューしてほしい点を渡します。

## 依頼例

```text
prを使って、担当者フィルターのブランチからPRを作成してください。Issue #123に対応し、URL復元のテストは成功しています。未割り当て条件の表示を重点的に確認してほしいです。
```

## 進め方

1. ブランチのコミットと変更内容を確認します。
2. PRテンプレートに沿って日本語で概要と確認事項をまとめます。
3. PRを提出し、作成先のリンクを示します。

## 成果物の例

サンプルの実コミットを確認して作成したPR本文です。架空のPR番号や投稿URLは付けていません。

**到達点：PR本文作成・GitHub投稿前。**

### 実行した依頼

```text
commit-demoのmainとexample/57の実コミット差分を確認し、contextのPRテンプレートに沿って日本語のPR本文を作ってください。GitHubへの投稿前までに留めてください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# チケット

https://github.com/yukihito-jokyu/context/issues/57

# 概要

隔離したサンプルリポジトリのexample/57ブランチで、説明文だけだったREADMEへ実行済みHTMLの原本リンクを追加しました。リンク先のHTMLも別コミットで保存し、読者が同じ成果物を開けるようにしました。

mainとの差分と2件の実コミットを確認して、contextのPRテンプレートに沿って本文を作成しました。日本語の本文と、その他欄のIssue参照はprスキルの指示に従っています。

確認した範囲: READMEのリンク先が作業領域に存在すること。HTMLはarchify-jpで生成し、生成検証と画面サイズ別の検査を実施済みです。

# その他

resolves #57

````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/pr/output.md#download)
- [実行入力の原本](pathname:///examples/pr/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/pr/execution.json#download)

### 確認した結果

- 実コミット2件とmainとの差分を確認。実PRの作成は未実施。

## 確認するポイント

テンプレートとIssue参照が正しいか、実施していない検証を成功としていないかを確認します。PRの作成はマージまでの完了を意味しません。

## 関連するスキル

- [pitch](../documentation/pitch.md)：説明の背景と理由を整理する。

## 正本を読む

詳細な手順と制約は[prのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/development/pr/SKILL.md)を参照してください。
