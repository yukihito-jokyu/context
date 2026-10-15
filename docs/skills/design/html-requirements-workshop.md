---
title: html-requirements-workshop — HTML画面案と指摘を反復する
sidebar_label: html-requirements-workshop
---

# html-requirements-workshop

画面の構想が曖昧で、HTMLモックを見ながら要件を決めたいときに使います。画面案と要件の記録を往復させます。

## 渡す情報

誰が使うか、達成したいこと、最初に確かめる画面・操作、保存先を渡します。

## 依頼例

```text
html-requirements-workshopを使って、依頼一覧のHTMLモックを作りながら要件を固めたいです。担当者が未対応を見つける画面から始め、一覧の情報量を確認したいです。
```

## 進め方

1. 最初の対話で目的を確認し、モック作成の依頼後に入力を作ります。
2. スナップショットを生成・検証し、画面の確認ポイントと詳細設計を提示します。
3. コメントを新しい入力とrunへ反映し、全項目が承認された画面と統合要件を保管します。

## 成果物の例

同梱スクリプトで生成した初回モックと要件です。図は実際のarchify-jp出力を使っています。

**到達点：run-001生成・検証済み／内容の承認待ち。**

**移行時の確認：既存の実行記録を移行しました。本文の一致は確認しましたが、過去の実行時の同梱資料全体は特定できていません。**

このハッシュは移行時の変更検出用の基準です。同梱資料全体をこの版で再実行した証拠ではありません。

### 実行した依頼

```text
archify-jpで生成した実HTMLと撮影画像を使い、実行依頼、実画面、HTML原本の取得を確認する画面案を生成してください。確認ポイントと画面詳細設計を保存し、初回案として検証してください。
```

### 実際の画面

![生成したHTMLモックを実ブラウザで検証中の画面](/skills/html-requirements-workshop/preview.png)

[画像を原寸で開く](pathname:///skills/html-requirements-workshop/preview.png)

正規のブラウザ検証中に撮影した画像です。注釈の検証操作を含み、人間の承認を示すものではありません。

### 成果物を取得する

- [生成した原本（HTML）](pathname:///skills/html-requirements-workshop/output.html#download)
- [生成した要件（Markdown）](pathname:///skills/html-requirements-workshop/requirements.md#download)
- [生成に使った入力（JSON）](pathname:///skills/html-requirements-workshop/input.json#download)
- [成果物・入力の一式（ZIP）](pathname:///skills/html-requirements-workshop/bundle.zip#download)
- [ブラウザ検証結果（環境パスを伏せたJSON）](pathname:///skills/html-requirements-workshop/browser-validation.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/html-requirements-workshop/output.html)
- [実行入力の原本](pathname:///skills/html-requirements-workshop/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/html-requirements-workshop/execution.json#download)

### 確認した結果

- generate_snapshot / validate_workspace成功。runのチェックサム検証を実施。
- 実ブラウザで1568×784、1280×800、1024×768の注釈、スクロール追従、当たり判定、モード分離がvalid。
- 承認履歴・承認済み画面は生成していません。

## 確認するポイント

この構造例は題材のファイル名を当てはめた抜粋です。確認ポイントの承認、画面詳細設計、承認済み内容の維持を確認します。過去runは上書きせず、修正は新しいrunへ残します。

## 関連するスキル

- [react-requirements-workshop](../design/react-requirements-workshop.md)：Reactで操作を確かめる。
- [plan](../planning/plan.md)：承認済み要件から実装計画へ進む。

## 正本を読む

詳細な手順と制約は[html-requirements-workshopのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/html-requirements-workshop/SKILL.md)を参照してください。
