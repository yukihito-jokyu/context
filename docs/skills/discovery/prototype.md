---
title: prototype — 具体物から判断基準を引き出す
sidebar_label: prototype
---

# prototype

見れば判断できるが、言葉だけでは期待を説明しにくいときに使います。UI、レポート、資料の軽い試作で認識を合わせます。

## 渡す情報

作りたいもの、対象ユーザー、必要な情報、制約、ダミーデータの可否、比較したい観点を渡します。

## 依頼例

```text
prototypeを使って、依頼一覧の画面案を二つ作ってください。ダミーデータを使い、一覧の情報量と未対応依頼の見つけやすさを比べたいです。バックエンド接続は不要です。
```

## 進め方

1. 試作で確認したい未知を決めます。
2. 軽い具体物を作り、必要なら差分が分かる複数案を提示します。
3. 人間の反応を判断基準と未決定事項へ変換します。

## 成果物の例

unknownsの実Markdownをそのまま表示し、同じ原本を取得する画面案を作りました。

**到達点：初回プロトタイプ生成・人間の確認待ち。**

**移行時の確認：既存の実行記録を移行しました。本文の一致は確認しましたが、過去の実行時の同梱資料全体は特定できていません。**

このハッシュは移行時の変更検出用の基準です。同梱資料全体をこの版で再実行した証拠ではありません。

### 実行した依頼

```text
unknownsの実出力を、実行した依頼、抜粋、全文展開、原本ダウンロードの順に読める単体HTMLのプロトタイプにしてください。初回案として確認する点を示してください。
```

### 実際の画面

![unknownsの実出力を表示した初回プロトタイプ](/skills/prototype/preview.jpg)

[画像を原寸で開く](pathname:///skills/prototype/preview.jpg)

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# Prototype

## 1. 目的

文章の実出力を、読者が入力から確認し、全文へ進める順序を具体的な画面で確かめる。

## 2. 前提

unknownsを実際に適用して作成したoutput.mdを使用する。バックエンドや保存機能は不要。生成した単体HTMLを開いて確認する。

## 3. プロトタイプ案

入力 → 実出力の抜粋 → 全文展開 → Markdown原本取得の順にした。実出力をHTMLへエスケープして表示し、同じ原本をdata URLで取得する。

## 4. 確認してほしい観点

````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///skills/prototype/output.md#download)
- [生成した原本（HTML）](pathname:///skills/prototype/output.html#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/prototype/output.html)
- [実行入力の原本](pathname:///skills/prototype/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/prototype/execution.json#download)

### 確認した結果

- 生成したHTMLをブラウザで開いて表示を確認。画像はその実画面を撮影。

## 確認するポイント

何を確かめる試作か、フィードバックによって何が決まったかを確認します。試作が動いても本実装の完了とは扱いません。

## 関連するスキル

- [html-requirements-workshop](../design/html-requirements-workshop.md)：HTML案で反復する。
- [react-requirements-workshop](../design/react-requirements-workshop.md)：React案で反復する。

## 正本を読む

詳細な手順と制約は[prototypeのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/prototype/SKILL.md)を参照してください。
