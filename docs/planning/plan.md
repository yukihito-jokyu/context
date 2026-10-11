---
title: plan — 重要判断を先頭にした実装計画を作る
sidebar_label: plan
---

# plan

調査や合意を、レビューできる実装計画へ変えるときに使います。作業手順だけでなく、人間が変更しそうな判断を先頭に置きます。

## 渡す情報

目的、確定仕様、調査結果、制約、受け入れ条件、未決定事項を渡します。

## 依頼例

```text
planを使って、依頼一覧の担当者フィルターを追加する計画を作ってください。条件はURLに保存し、未割り当ても選択できます。重要判断、作業順、検証方法を先に確認したいです。
```

## 進め方

1. 目的と完了条件、データ構造・UX・既存仕様への影響を整理します。
2. 実装手順を依存順に並べ、機械的変更を分けます。
3. 未決定事項、仮定、レビュー観点を示します。

## 成果物の例

実際の修正要件と調査結果から作成した計画です。

**到達点：実装計画の作成。**

### 実行した依頼

```text
全スキルの実入力と実出力を保存し、画像と原本をMarkdownから取得できるようにする修正の計画を作ってください。重要判断、UX、既存仕様への影響を先に示してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# Implementation Plan

## 1. 重要判断

### 1.1 データモデル・構造

- スキルごとに入力、実出力、検証記録、必要な画面画像を保存する。
- 保存先はdocs/artifacts/examples/<skill-name>。Markdown原本を文書探索から除外する。

### 1.2 型・インターフェース

- 実行記録にはskill、skill_sha256、input、stage、artifacts、checksを持たせる。
- artifactsはファイル名、形式、SHA-256を記録する。実行していない検証をpassにしない。

### 1.3 UX・処理フロー

````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/plan/output.md#download)
- [実行入力の原本](pathname:///examples/plan/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/plan/execution.json#download)

### 確認した結果

- SKILL.mdを読み、今回の実要件と参照対象へ適用して出力を保存。内容の人間確認は未実施。

## 確認するポイント

重要判断と作業順のつながり、検証が受け入れ条件を満たすか、未決定事項が残っているかを確認します。

## 関連するスキル

- [notes](../documentation/notes.md)：実装中の判断を残す。
- [to-issues](../planning/to-issues.md)：計画をIssueに分ける。

## 正本を読む

詳細な手順と制約は[planのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/planning/plan/SKILL.md)を参照してください。
