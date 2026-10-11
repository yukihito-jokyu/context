---
title: agent-trace — 操作の証跡と再現手順を残す
sidebar_label: agent-trace
---

# agent-trace

作業開始からの操作や判断を追えるログが欲しいときに使います。必要に応じて、成功経路だけの手順書へまとめます。

## 渡す情報

対象リポジトリ、タスク、記録したい範囲を渡します。手順書が欲しいときは「ログをまとめて」と依頼します。

## 依頼例

```text
agent-traceを使って、依頼一覧の表示不具合調査を開始時点から記録してください。終わったら、ログをまとめて再現と確認の手順書にしてください。
```

## 進め方

1. 開始時に.agent-trace内へログを作ります。
2. 調査・判断・操作・結果・失敗を、作業中に時系列で追記します。
3. 手順書の依頼後、確認できた成功経路から最短の再現手順を作ります。

## 成果物の例

検証作業の開始時点にログを作り、操作と並行して追記した実証跡です。手順書は成功したコマンドから整理しました。

**到達点：検証ログ・手順書作成／サイトの人間確認は未完了。**

### 実行した依頼

```text
この時点からarchify-jpの成果物検証と公開用保存の操作をMarkdownに同時記録し、実際に成功したコマンドから簡易手順書を作成してください。以前の時刻は補作しないでください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# Agent Trace: artifact-validation

## Task

- 目的: archify-jpの実成果物を検証し、ダウンロード用の実行例を作る。
- 開始日時: 2026-10-11T10:52:52.929089+09:00
- セッションディレクトリ: 20261011-105252
- 作業対象: context-skill-examples（サンプル作業領域）

## Trace

### 1. 作業開始

- 内容: この時点から成果物検証の操作と結果を記録する。以前の作業時刻は補作しない。

### 2. 生成と検証
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/agent-trace/output.md#download)
- [実ログから整理した手順書](pathname:///examples/agent-trace/guide.md#download)
- [実行入力の原本](pathname:///examples/agent-trace/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/agent-trace/execution.json#download)

### 確認した結果

- 生成物はMarkdownのログと手順書。過去の作業時刻を遡って作成していません。

## 確認するポイント

ログは失敗も含む事実の記録、手順書は再現に必要な成功経路です。.agent-trace/<開始日時>/にMarkdownとして保存し、秘密情報を含めません。

## 関連するスキル

- [issue-trace](../documentation/issue-trace.md)：Issue上で段階ごとの根拠を共有する。
- [notes](../documentation/notes.md)：判断を整理する。

## 正本を読む

詳細な手順と制約は[agent-traceのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/agent-trace/SKILL.md)を参照してください。
