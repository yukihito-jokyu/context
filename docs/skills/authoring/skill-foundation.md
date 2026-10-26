---
title: skill-foundation — 判断と出力を揃えるスキルを作る
sidebar_label: skill-foundation
---

# skill-foundation

同じ依頼でも実行者によって判断や出力が変わる場合に、条件ごとの答えを決定表にまとめ、出力を検査できるスキルを作ります。新規作成と既存スキルへの後付けに対応し、Claude CodeとCodexを対象にします。

`my-skill-creator`はスキルの作成・改善・評価を広く扱います。`skill-foundation`は判断と出力のばらつきを減らすため、決定表、出力の契約、違反例、収束テストを一式で整えます。リポジトリ全体の開発規約を整える場合は[pattern-foundation](../development/pattern-foundation.md)、配置とカタログの整備には[skill-authoring](skill-authoring.md)を使います。

## 渡す情報

何を受け取り、何を出力するスキルかを伝えます。対象製品、言語、収束テストを実行するかに希望があれば併記してください。対象製品は既定でClaude CodeとCodex、言語は依頼文から決まり、収束テストは実行前に回数を示して確認します。

## 依頼例

```text
skill-foundationを使って、Git差分から日本語のコミットメッセージを書くスキルを作ってください。Claude CodeとCodexを対象に、判断と出力の形式を揃え、違反例で検査が働くことを確認したいです。
```

## 進め方

1. 入力と出力を確認し、名前・種類・対象製品を決めて実行を開始します。
2. 仕様を`dev/spec.json`に記録し、スキルの骨組みを生成します。
3. 作業が前提とする仕様を調べ、判断が分かれる点を条件と答えの決定表にまとめます。
4. 出力の形式と検査方法を定め、正常な見本と違反例で検査を確かめます。
5. 収束テストで独立した実行者の結果を比べ、残る違いを記録します。
6. 最終検査と配置を行い、検査済みのファイルのハッシュを保存して仕上げます。

工程ごとに検査を通してから次へ進みます。実行中はスキル自身を変更せず、作成対象の側を直します。

## 配布と導入の状況

正本は`utils/skills/authoring/skill-foundation/`にまとめています。このスキル自身にも実行を制御するhooksがあるため、hooksと一緒に配布する単位は[plugin](../../plugins/distribution.md)と判断します。今回の取り込みではplugin定義・配布物を作成しておらず、インストールやhooksの登録・有効化も行っていません。

Skill単体の取得は[初めて使う](../getting-started.md)を参照してください。単体の取得だけではhooksの登録まで完了しません。正本にはプロジェクトへ配置・登録する`install.py`がありますが、その操作は別途、対象プロジェクトで行います。

## 成果物の例

Git差分から日本語のコミットメッセージを書くスキルに、受付と骨組み生成だけを実際に適用した例です。フェーズ1のlintに合格した後、指定に従ってabortしました。ZIPは未完成の骨組みと実行記録です。

**到達点：フェーズ0・1のみ実施、フェーズ1 lint合格後に中断（スキルはbuilding、実行はaborted）。**

### 実行した依頼

```text
Git差分を受け取り、日本語のコミットメッセージを出力する write-commit-message スキルを新規作成してください。対象は Claude Code と Codex、日本語です。今回は受付と骨組み生成（フェーズ0・1）までを実行し、フェーズ1のlint結果を記録して止めてください。収束テスト、製品仕様の外部調査、インストール、hooks登録は実行しません。完成扱いにせず、実行を abort して中断理由を記録してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
最終の返答は、次の本文をそのまま使う。前後に文を足さず、要約しない。
========================================
## 結果

skill-foundation: 中断（理由: ユーザー指定により受付と骨組み生成（フェーズ0・1）で停止。フェーズ1のlint結果を記録し、調査・決定・契約の実装・違反例・収束テスト・インストール・hooks登録・最終検査は未実施。スキルは未完成（status: building）。）

## 出力

- `.claude/skills/write-commit-message/SKILL.md`（skill-entry 作ったスキルの SKILL.md）

## 既定値で決めた値

- なし

## 入力で読めなかった値

````

### 成果物を取得する

- [中断時の実出力（Markdown）](pathname:///skills/skill-foundation/output.md#download)
- [受付・骨組み一式と実行記録（ZIP・未完成）](pathname:///skills/skill-foundation/write-commit-message-skeleton-incomplete.zip#download)
- [実コマンドと検証結果（JSON）](pathname:///skills/skill-foundation/validation.json#download)
- [実行入力の原本](pathname:///skills/skill-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/skill-foundation/execution.json#download)

### 確認した結果

- run.py start・init_skill.py・skill_lint.py --phase 1・run.py abort はすべて終了コード0。
- 骨組み12ファイルと中断の実行記録をZIPへ保存。TODOと未確定の項目を残した未完成品です。
- abortのstdout全体（返答方法の指示・区切りを含む）をoutput.mdへそのまま保存。ZIPにはランタイムが保存したreport.mdの本文も収録。
- 実行前後のsourceManifestが一致し、正本82ファイルは変更なし。PYTHONDONTWRITEBYTECODE=1で実行。
- 外部調査・収束テスト・インストール・hooks登録・最終検査・finishは実施していません。

## 確認するポイント

決定ごとの検査方法と、機械で検査しない理由を確認します。違反例を検出できることと、実行者による出力の違いが減ったことは、それぞれ違反例の実行結果と収束テストで確かめます。

骨組みだけを作った段階ではスキルは未完成です。掲載例の到達点を確認し、最終検査やhooksの実動作、Claude CodeとCodexでの結果の一致まで確認済みとは扱わないでください。

## 正本を読む

詳細な手順と制約は[skill-foundationのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-foundation/SKILL.md)を参照してください。
