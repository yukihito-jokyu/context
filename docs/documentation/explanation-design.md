---
title: explanation-design — 読者が理解できる説明順を設計する
sidebar_label: explanation-design
---

# explanation-design

資料や解説の素材はあるが、読み手へ何から伝えるかが決まっていないときに使います。文章やHTMLの前に情報のつながりを設計します。

## 渡す情報

素材、想定読者、理解してほしいこと、出力形式、長さや前提知識の制約を渡します。

## 依頼例

```text
explanation-designを使って、担当者条件をURLへ保存する仕組みの説明順を設計してください。読者は一覧画面を使う担当者です。ブラウザの内部実装は知らない前提で、共有リンクの効果を理解できるようにしたいです。
```

## 進め方

1. 最終的に伝えたいことと読者の前提を整理します。
2. 必要な前提知識と情報の依存関係から説明順を決めます。
3. 伝達設計を提示し、人間の承認後に文章やHTMLへ変換します。

## 成果物の例

現在の要件を入力に、所定の7項目で作成した伝達設計です。

**到達点：伝達設計案・完成本文への変換前。**

### 実行した依頼

```text
スキルを使う前に実際の成果物を確かめたい読者へ、実入力、実出力、画面画像、原本取得、検証結果を説明する順序を設計してください。まず伝達設計を出してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# 伝達設計

## 1. 最終的に伝えたいこと

このスキルへどの情報を渡すと、どの成果物が得られ、利用者が何を確認できるのか。

## 2. 読者の前提

スキルの名前と目的は説明ページで読める。実行前に成果物の形を確かめたい利用者を想定する。

## 3. 必要な前提知識

文章を出すスキルと、操作できるHTMLや複数ファイルを出すスキルがある。対話や承認を含むスキルは、初回出力と最終確定物が異なる。

## 4. 情報同士のつながり

````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/explanation-design/output.md#download)
- [実行入力の原本](pathname:///examples/explanation-design/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/explanation-design/execution.json#download)

### 確認した結果

- 伝達設計を保存。承認済みの完成本文としては扱っていません。

## 確認するポイント

見た目の構成より先に、前提から結論へつながる説明順があるかを確認します。完成本文へ進む前に伝達設計を承認します。

## 関連するスキル

- [compare](../discovery/compare.md)：比較のHTMLへ変換する。
- [archify-jp](../design/archify-jp.md)：必要な関係を図にする。

## 正本を読む

詳細な手順と制約は[explanation-designのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/explanation-design/SKILL.md)を参照してください。
