---
title: react-requirements-workshop — React画面案と操作を反復する
sidebar_label: react-requirements-workshop
---

# react-requirements-workshop

Reactの動く画面案やDesign Systemの部品を使って、要件をすり合わせたいときに使います。画面案とレビューUIを一つの作業領域で管理します。

## 渡す情報

対象ユーザー、達成したいこと、画面・操作、参照デザイン、保存先を渡します。

## 依頼例

```text
react-requirements-workshopを使って、依頼一覧の操作をReact画面案で確認したいです。担当者フィルターと未対応表示を試せる案を作り、指摘を次の案へ反映してください。
```

## 進め方

1. 目的を確認し、画面案の依頼後に作業領域を初期化します。
2. 同梱Design Systemを確認してTSXとJSONの案を追加し、型・表示・注釈を検証します。
3. 画面案を固定してコメントを受け、新しい番号へ反映します。承認済みの画面と要件を保管します。

## 成果物の例

Design System部品を導入して生成したReact画面案です。表示一式とソースを別々のZIPで取得できます。

**到達点：初回画面案生成・検証済み／内容の承認待ち。**

### 実行した依頼

```text
unknownsの実出力を読むReact画面案を、Design Systemのdetail-pageで作ってください。抜粋と全文の切り替え、Markdown原本取得を用意し、初回案のTSX・JSON・表示一式を保存して検証してください。
```

### 実際の画面

![生成したReact画面案を1568×784で検証中の画面](/examples/react-requirements-workshop/preview.png)

[画像を原寸で開く](pathname:///examples/react-requirements-workshop/preview.png)

表示ZIPは展開してローカルサーバーで開けます。ソースZIPには導入済み部品を含み、npm ci → npm run devで確認できます。公開Registryの404に対してローカル正本を使った経緯は検証記録に残しています。

### 成果物を取得する

- [生成した要件（Markdown）](pathname:///examples/react-requirements-workshop/requirements.md#download)
- [生成に使った入力（JSON）](pathname:///examples/react-requirements-workshop/input.json#download)
- [生成した画面一式（ZIP）](pathname:///examples/react-requirements-workshop/rendered.zip#download)
- [画面ソース一式（ZIP）](pathname:///examples/react-requirements-workshop/source.zip#download)
- [ブラウザ検証結果（環境パスを伏せたJSON）](pathname:///examples/react-requirements-workshop/browser-validation.json#download)
- [実行入力の原本](pathname:///examples/react-requirements-workshop/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/react-requirements-workshop/execution.json#download)

### 確認した結果

- 公開Registryのdetail-page.jsonは404。提供元のローカル正本コピーをshadcn buildし、同じRegistryからview/addで導入。
- validate_snapshot、typecheck、lint、freeze_snapshotのproduction build成功。
- ブラウザ検証は初回に必要なChromium版を起動できず失敗。対応する設定で既存Chromeを指定して再実行。
- 1568×784、1280×800、1024×768、800×900の注釈、モード分離、画面枠の検証がすべてvalid。

## 確認するポイント

これは保存物の一部を示す構造例です。TSXとJSONの対応、実際に提示した画面のzip、指摘の反映と承認履歴を確認します。既存のアプリとサーバーを案ごとに初期化し直しません。

## 関連するスキル

- [html-requirements-workshop](../design/html-requirements-workshop.md)：単体HTMLで議論する。
- [plan](../planning/plan.md)：合意した画面を実装計画へ渡す。

## 正本を読む

詳細な手順と制約は[react-requirements-workshopのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/react-requirements-workshop/SKILL.md)を参照してください。
