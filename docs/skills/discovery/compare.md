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

実際のsearchDocumentsへ空本文と実本文を渡し、同じ6検索語の全返却値から比較HTMLを新規制作しました。

**到達点：実関数の実行・5図の標準SVG出力・単体HTML生成・表示と操作確認済み。**

### 実行した依頼

```text
contextのsearchDocumentsへタイトルだけを渡す場合と実本文も渡す場合を、同じ検索語で実際に実行して比較してください。実入力と全返却値を保存し、仕組み、コード、制限、使い分け、根拠を図付き単体HTMLにしてください。
```

### 実際の画面

![新しく制作した比較HTMLのPC実画面](/skills/compare/preview.png)

[画像を原寸で開く](pathname:///skills/compare/preview.png)

### 成果物を取得する

- [図とコードの比較原本（HTML）](pathname:///skills/compare/output.html#download)
- [入力・全返却値・図・再現コード一式（ZIP）](pathname:///skills/compare/bundle.zip#download)
- [全検索結果（JSON）](pathname:///skills/compare/search-results.json#download)
- [実入力（JSON）](pathname:///skills/compare/search-input.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/compare/output.html)
- [実行入力の原本](pathname:///skills/compare/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/compare/execution.json#download)

### 確認した結果

- 4文書×同じ6検索語をA/B各条件で実関数へ入力。全返却値とlimit検証を保存。
- 更新後の依存記録を読んだ後、別の新規作業場所から入力構築、関数実行、5モデルdeliver、Chrome標準SVG出力、HTML組立てを再実行。
- sync_vendor.py --check、check_overviews.py（5ページ）、check_coverage.py（11項目）が成功。
- Chromeで1440px/390px×5ページ、ページ移動・深いリンク・details・戻る/進む・連続移動・段階再生・有限終了・reduced-motion・JavaScript無効を検査。
- PC全体像・PC実装・390pxシナリオ・390px使い分けの4静止画像を目視。狭幅の図は内部横スクロールと原図リンク。再生の時間方向の目視・タブ非表示・印刷は未実施。
- 正本や実行ログの個人ホームパス、詳細環境版をマスクし、作業パスは<workdir>へ置換。ZIPもマスク後のファイルから新規生成。成果物SHAはマスク後。
- 利用者承認は要求も実施もしていない。外部投稿なし。

## 確認するポイント

例は完成HTMLの構成を説明するものです。実成果物では、全体図・本文・コードの対応、ページ移動、出典、確認した範囲を見ます。Archifyはこのスキルに同梱されています。

## 関連するスキル

- [explanation-design](../documentation/explanation-design.md)：説明順を設計する。
- [archify-jp](../design/archify-jp.md)：構造や順序を図にする。

## 正本を読む

詳細な手順と制約は[compareのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/compare/SKILL.md)を参照してください。
