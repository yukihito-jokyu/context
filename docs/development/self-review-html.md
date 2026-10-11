---
title: self-review-html — 差分の評価をHTMLで確認する
sidebar_label: self-review-html
---

# self-review-html

PR前に、差分の各行が指定ルールに適合しているかを確認したいときに使います。評価と指摘を同じレビュー画面で扱います。

## 渡す情報

比較対象、対象パス、評価ルール、成果物の保存先を渡します。

## 依頼例

```text
self-review-htmlを使って、mainとの差分をレビューしてください。対象は依頼一覧関連のファイルです。ルールはAGENTS.mdとこのIssueの受け入れ条件です。HTMLで評価と指摘を確認したいです。
```

## 進め方

1. 比較対象とルールを確定し、差分を収集します。
2. 行単位の評価と根拠、ルール不足候補をまとめます。
3. 検証済みのレビューHTMLを提示し、人間の承認や指摘を受けます。

## 成果物の例

実際のGit差分へAI評価を付け、正規スクリプトで生成したレビューHTMLです。人間の指摘JSONはまだ受信していません。

**到達点：差分評価・HTML生成・人間のレビュー待ち。**

### 実行した依頼

```text
隔離したcommit-demoで、target=HEAD、source=WORKTREE、対象=README.md、指定ルール=rules.mdの差分を収集し、行単位のレビューHTMLを生成してください。正規スクリプトで行網羅と決定性を検証してください。
```

### 実際の画面

![実Git差分とAI評価を表示したレビューHTML](/examples/self-review-html/preview.jpg)

[画像を原寸で開く](pathname:///examples/self-review-html/preview.jpg)

### 成果物を取得する

- [レビュー原本（HTML）](pathname:///examples/self-review-html/report.html#download)
- [成果物・入力の一式（ZIP）](pathname:///examples/self-review-html/bundle.zip#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/self-review-html/report.html)
- [実行入力の原本](pathname:///examples/self-review-html/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/self-review-html/execution.json#download)

### 確認した結果

- collect_diffで追加1行・削除1行を収集。
- validate_reviewで全変更行を通常評価で覆い、別カードのrule_gapを検証。
- render_report --verify-determinism成功。Chromeで実差分と3評価カードを確認。

## 確認するポイント

評価に実際の行と根拠があるか、適用したルールを確認できるかを見ます。feedback.jsonは指摘が送信された場合に保存されます。

## 関連するスキル

- [commit](../development/commit.md)：修正済み差分をコミットする。
- [pitch](../documentation/pitch.md)：レビュー観点を説明する。

## 正本を読む

詳細な手順と制約は[self-review-htmlのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/development/self-review-html/SKILL.md)を参照してください。
