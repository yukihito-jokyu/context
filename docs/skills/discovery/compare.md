---
title: compare — 似た仕組みを図とコードで比較する
sidebar_label: compare
---

# compare

二つの仕組みの違いを、全体像から具体的な動作まで追いたいときに使います。同じ題材で比べることで、使い分けの理由を理解できます。

## 渡す情報

比較対象、理解したい問い、対象バージョン、一次資料やコード、読み手の前提を渡します。

## 依頼例

```text
compareを使って、WebSocketとServer-Sent Eventsを比較するHTMLを作ってください。読者はHTTPを理解しています。同じ通知を受信する例で、接続、送受信、切断後の処理を図とコードで追えるようにしてください。
```

## 進め方

1. 比較範囲と読み手の問いを整理し、一次資料を確認します。
2. 各関心の全体図と、同じ入力を使った動作・コードを対応づけます。
3. 関心別のページを持つ単体HTMLを作り、情報の網羅性と操作・表示を確認します。

## 成果物の例

既存の検索関数を実行し、実入出力とコードから比較HTMLを作成しました。図は同梱Archifyで生成し標準SVGエクスポートを埋め込みました。

**到達点：比較HTML生成・構造確認・実表示確認済み。**

**移行時の確認：既存の実行記録を移行しました。本文の一致は確認しましたが、過去の実行時の同梱資料全体は特定できていません。**

このハッシュは移行時の変更検出用の基準です。同梱資料全体をこの版で再実行した証拠ではありません。

### 実行した依頼

```text
contextのsearchDocumentsへタイトルだけを渡す場合と実本文も渡す場合を、同じ検索語で実際に実行して比較してください。実入力と全返却値を保存し、仕組み、コード、制限、使い分け、根拠を図付き単体HTMLにしてください。
```

### 実際の画面

![生成した比較HTMLの全体像ページ](/skills/compare/preview.jpg)

[画像を原寸で開く](pathname:///skills/compare/preview.jpg)

### 成果物を取得する

- [生成した原本（HTML）](pathname:///skills/compare/output.html#download)
- [成果物・入力の一式（ZIP）](pathname:///skills/compare/bundle.zip#download)
- [実際の検索結果（JSON）](pathname:///skills/compare/search-results.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/compare/output.html)
- [実行入力の原本](pathname:///skills/compare/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/compare/execution.json#download)

### 確認した結果

- 6種類の検索語を同じ実関数で実行し、A/Bの全返却値をJSONへ保存。
- 5図のshowcase検証9項目とdeliver成功。標準serializeSvgの補助処理でSVGを出力。ブラウザのPNGエクスポートとの一致は未検証。
- check_overviewsは5ページ・5図、check_coverageは12項目で成功。本文とソースの意味を読み合わせ。
- Chromeで全体像、コードページへの切り替え、直接再読込を確認。性能比較は未実施。

## 確認するポイント

例は完成HTMLの構成を説明するものです。実成果物では、全体図・本文・コードの対応、ページ移動、出典、確認した範囲を見ます。Archifyはこのスキルに同梱されています。

## 関連するスキル

- [explanation-design](../documentation/explanation-design.md)：説明順を設計する。
- [archify-jp](../design/archify-jp.md)：構造や順序を図にする。

## 正本を読む

詳細な手順と制約は[compareのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/compare/SKILL.md)を参照してください。
