---
title: grill-issue — Issueの未決定事項を詰める
sidebar_label: grill-issue
---

# grill-issue

Issueに書かれた要求が曖昧で、そのまま実装すると判断が分かれそうなときに使います。意思決定の依存関係を順番に解消します。

## 渡す情報

対象リポジトリとIssue番号、議論したい設計や制約を渡します。

## 依頼例

```text
grill-issueを使ってIssue #123の要件と実装方針を詰めてください。完了済み依頼と未割り当て依頼の扱いを、一問ずつ確認してから計画にしてください。
```

## 進め方

1. Issueを読み、コードから分かる事項を調べます。
2. 依存する判断を順に、一問ずつ推奨回答とともに確認します。
3. 相互理解が得られた内容を実装計画へまとめます。

## 成果物の例

gh issue viewで実際のIssueを取得し、会話の回答と照合しました。

**到達点：Issue調査・残る分岐の整理。**

**移行時の確認：既存の実行記録を移行しました。本文の一致は確認しましたが、過去の実行時の同梱資料全体は特定できていません。**

このハッシュは移行時の変更検出用の基準です。同梱資料全体をこの版で再実行した証拠ではありません。

### 実行した依頼

```text
Issue 57の本文と全コメントを取得し、Docusaurus採用、スキル限定のdocs、実成果物展示の合意と未決定の分岐を整理してください。回答済みの質問は繰り返さないでください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# Issue #57 の意思決定整理

実際にgh issue view 57 --repo yukihito-jokyu/context --json number,title,body,comments,url,stateを実行し、本文とコメントを確認した。

## 確認したIssue

https://github.com/yukihito-jokyu/context/issues/57

- タイトル: ドキュメントをgithub pagesに移行する。
- 本文: 調査から。
- コメントにはDocusaurus、スキル限定のdocs、実成果物への変更計画が記録されている。

## 解消済みの分岐

1. サイト生成方式: ユーザーが「じゃあDocusaurusで」と選択。
2. 公開対象: docs。既存文書を刷新し、utilsの分類に沿うスキル説明へ限定。
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///skills/grill-issue/output.md#download)
- [実行入力の原本](pathname:///skills/grill-issue/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/grill-issue/execution.json#download)

### 確認した結果

- Issueの本文とコメントを取得。外部サンプル作成範囲は回答待ち。

## 確認するポイント

未決定事項が実際に解消され、コードから調べられることを人間に尋ねていないかを確認します。

## 関連するスキル

- [plan](../planning/plan.md)：判断を計画へまとめる。
- [issue-trace](../documentation/issue-trace.md)：段階ごとの根拠をIssueへ残す。

## 正本を読む

詳細な手順と制約は[grill-issueのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/planning/grill-issue/SKILL.md)を参照してください。
