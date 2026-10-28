---
title: generate-domain-model — 業務の概念を図とカタログにする
sidebar_label: generate-domain-model
---

# generate-domain-model

業務説明・仕様・指定されたコード・既存のMermaidから、業務の概念と関係を整理します。編集できるMermaid原本とPNGを生成し、複数の図をHTMLカタログで一覧・検索・拡大できます。

図には業務の概念、主な属性、関係名、資料に書かれた多重度を載せます。根拠となる資料と実際の記述を図ごとに残し、資料だけで確定できない関係や多重度は「確認したいこと」として示します。

## 渡す情報

- 図にしたい業務説明、仕様、コードのパス、または `classDiagram`。
- カタログ名。指定がなければ `domain` になります。
- 既存カタログを更新するときは、その名前と更新内容。

Python 3.9以上と、実行できる公式Mermaid CLIの `mmdc` が必要です。スキルは依存を自動でインストールしません。Mermaid CLI 12.0.0ではNode.js 22.13.0以上とPuppeteerで起動できるブラウザが必要です。[環境の準備](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/references/setup.md)を参照してください。

## 依頼例

```text
generate-domain-modelを使って、docs/order-spec.mdの業務の概念と関係を図にしてください。
カタログ名はsalesです。受注と支払の2つの図に分け、Mermaid原本・PNG・HTMLカタログを作ってください。
資料にない多重度は推測せず、確認したい点として残してください。
```

## 進め方

1. 資料と図の対象を確認し、業務領域ごとの概念・属性・関係を整理します。
2. 新規カタログを作るか、更新対象の既存IDを読みます。
3. Mermaid原本とカタログ情報を書き、全図のPNGを生成します。
4. HTML一覧とファイルの対応、PNGの破損、検証記録を確認します。
5. 根拠と図を照合し、PNGとHTMLの表示を確認して結果を返します。

生成先は `domain-models/<カタログ名>/` です。`index.html` を直接開けます。閲覧時のCDN・サーバー・外部APIは不要です。Mermaid原本とPNGへのリンクもカタログにあります。複数ファイルを渡すときはディレクトリ全体を保持してください。

既存カタログの更新では同じ図のIDを維持し、追加・内容修正を行います。依頼のない既存図の削除や未知のファイルの上書きは拒否します。変換に失敗した場合、生成済みの正常な画像とHTMLは置き換えません。

## 配布と導入

Claude CodeとCodexを対象にします。出力検査用のhooksを同梱するため、[generate-domain-model plugin](../../plugins/generate-domain-model.md)として配布物を生成します。hooksが利用できない実行環境でも `run.py check` と `finish` がカタログ全体を検査します。

DBのテーブルと外部キーを表すER図や、コードの全クラスとメソッドを示す図には[archify-jp](archify-jp.md)を使います。このスキルでは業務の概念を扱います。

## 成果物の例

受注と配送の業務資料から顧客・注文・配送の2図を新規生成しました。資料にない配送の多重度は確認事項に残しています。

**到達点：新規生成・PNGと実画面の目視・HTML操作・check・finish・ZIP照合まで完了。利用者の最終確認と製品内hooks自動発火は未実施。。**

### 実行した依頼

```text
架空の「受注と配送業務」のドメインモデルを作成してください。
カタログ名は sales、図のIDは order と shipment の2図にしてください。
Mermaid原本、実際に描画したPNG、オフラインで一覧・検索・拡大できるHTMLカタログを生成してください。
資料にある概念・属性・関係・多重度を表し、資料にない多重度は図に書かず、未確認事項に残してください。

業務資料:
顧客(Customer)は顧客番号・氏名を持つ。
注文(Order)は注文番号・注文日を持つ。
顧客は0件以上の注文を申し込み、注文は必ず1人の顧客に属する。
配送(Shipment)は追跡番号を持つ。
注文を配送する関係があるが、注文と配送の多重度は資料では決めていない。

order は顧客と注文、shipment は注文と配送を対象にしてください。
生成した図・説明とこの資料の意味を照合し、PNGとHTMLを実際に表示して確認してください。
既存カタログの更新は依頼していません。
```

### 実際の画面

![受注と配送の業務資料から顧客・注文・配送の2図を新規生成しました。資料にない配送の多重度は確認事項に残しています。](/skills/generate-domain-model/preview.png)

[画像を原寸で開く](pathname:///skills/generate-domain-model/preview.png)

新規生成したカタログの実画面を保存し、画像を開いて確認しました。利用者の最終確認は未実施です。

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
## 結果

generate-domain-model: 完了（検証に合格）

図: 2件
カタログ: [開く](/private/tmp/context-model-refresh/generate-domain-model/project/domain-models/sales/index.html)
検証: 原本・画像・HTML・全ファイルの対応に合格

## 出力

- `domain-models/sales/catalog.json`（catalog カタログ情報）
- `domain-models/sales/index.html`（index HTMLカタログ）
- `domain-models/sales/validation.json`（validation 変換検証結果）
- `domain-models/sales/diagrams/order.mmd`（mermaid Mermaid原本）
- `domain-models/sales/diagrams/shipment.mmd`（mermaid Mermaid原本）

````

### 成果物を取得する

- [HTML・Mermaid原本・PNGの一式（ZIP）](pathname:///skills/generate-domain-model/sales-catalog.zip#download)
- [finishの実出力全文（Markdown）](pathname:///skills/generate-domain-model/output.md#download)
- [実行と検証の記録（JSON）](pathname:///skills/generate-domain-model/verification.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/generate-domain-model/domain-models/sales/index.html)
- [実行入力の原本](pathname:///skills/generate-domain-model/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/generate-domain-model/execution.json#download)

### 確認した結果

- start・inspect・deps・build・check・finish を実行し、指摘0件で終了。
- 全2枚のPNGとPC1440px・モバイル390pxの実画面を開き、属性・日本語・関係線・多重度を資料と目視照合。
- 両画面で検索4通り、全2図の拡大と閉じるを確認。file://でも画像・検索・拡大が動作。横はみ出し・JavaScriptエラー・外部HTTP通信は0件。
- HTTPループバックで原本・PNG全4件を実ダウンロードし、生成ファイルと全byte一致。
- 公開前に個人ホーム名と実環境の詳細版をマスク。ZIP全件の展開内容が公開ファイルとbyte一致。正本全体は実行前後で不変。
- マスク後の公開カタログを正本catalog.pyのcheck/verifyで再検査し合格。

## 確認するポイント

- 資料の業務用語と、図の概念・関係・説明が一致しているか。
- 資料にない多重度が断定されず、未確認事項に残っているか。
- PNG内の日本語、画像の欠け、拡大時の読みやすさを確認できるか。
- HTMLから対象の図を検索し、対応する原本とPNGを取得できるか。

検査はファイルの形式・対応と描画結果を確かめます。業務上の意味の正しさは資料と照合して判断します。フォントと描画環境が違うPNGのバイト一致は保証しません。

## 正本を読む

[SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/SKILL.md)と[同梱ファイル](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/design/generate-domain-model)を参照してください。
