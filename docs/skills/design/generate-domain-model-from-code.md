---
title: generate-domain-model-from-code — コードから業務概念と関係を図にする
sidebar_label: generate-domain-model-from-code
---

# generate-domain-model-from-code

リポジトリのコードを読み、業務上の概念・属性・関係をMermaid原本、PNG、HTMLカタログにまとめます。HTMLでは概念を検索し、領域を選び、図を拡大してコードの根拠を確認できます。

AIがコードを読んでモデル情報を作り、同梱スクリプトが根拠の行と抜粋を検査して図を生成します。コードの意味を完全に自動抽出する解析器ではありません。確認できない分類や多重度は断定せず、確認事項として残します。領域はコードのディレクトリ単位で、DDD上の境界を保証しません。

説明は日本語で書き、図の概念名と関係名にはコードの識別子・参照メンバー名を使います。実行するAIによって訳語が変わることを避け、コードへ辿りやすくします。分類を明示する宣言がないクラスは `concept` とし、idという属性名やfrozenの指定だけでentity・valueとは断定しません。

## 渡す情報

対象リポジトリと調査範囲を渡します。省略すると作業中のリポジトリ全体が対象です。出力名の既定値は `domain-model` で、同名の出力がある場合は別名を指定します。出力先の希望がある場合は、検査後にカタログ全体を渡す場所として伝えます。

Python 3.9以上、インストール済みのMermaid CLIと、CLIから起動できるブラウザーが必要です。CLIを自動取得する処理はありません。`mmdc` がPATH上にない場合は `MMDC`、ブラウザーを指定する場合は `PUPPETEER_EXECUTABLE_PATH` を設定します。対応拡張子・除外対象は[モデル情報の仕様](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model-from-code/references/model-format.md)で確認できます。

Skill単体の取得は[初めて使う](../getting-started.md)、hooksと一緒に使う配布単位は[pluginガイド](../../plugins/generate-domain-model-from-code.md)を参照してください。

## 依頼例

```text
このリポジトリの注文と支払いのコードから、ドメインモデル図を作ってください。
対象はsalesとpaymentsです。根拠のコードを辿れるようにして、Mermaid原本・PNG・HTMLカタログを渡してください。
出力の名前はshopにしてください。
```

## 進め方

1. 対象範囲と出力名を確認し、コードの一覧とGitの状態を記録します。
2. コードを読み、概念・属性・関係と根拠の抜粋をモデル情報へまとめます。未読範囲と判断できない点も記録します。
3. モデル情報からMermaidとPNGを生成し、検索・絞り込み・拡大ができるHTMLへまとめます。
4. コードと抜粋、ID、生成物の対応、PNGの構造とハッシュを検査し、実際の図とHTMLの操作を確認します。
5. `.skill-runs/generate-domain-model-from-code/out/<出力名>/` のカタログを渡します。希望する出力先があれば、検査済みの一式をコピーします。

## 成果物の例

定期契約と請求のTypeScript2ファイルを読み、4概念・3参照・2領域を整理した全体図と領域別の3図を新規生成しました。

**到達点：新規生成・PNGと実画面の目視・HTML操作・check・finish・ZIP照合まで完了。利用者の最終確認と製品内hooks自動発火は未実施。。**

### 実行した依頼

```text
# コードからドメインモデルを生成する公開サンプル

このリポジトリのTypeScriptコードを読み、顧客・契約・料金プラン・請求書の業務概念と関係を、コードの行番号と抜粋を根拠にしたドメインモデルにしてください。Mermaid原本、PNG、検索・領域選択・拡大・原本取得が使えるHTMLカタログを生成してください。

name: subscription-billing
repo: .

scopeは未指定のため既定値を使います。分類や多重度、寿命の所有をコードから断定できない場合は確認事項へ残してください。対象コードと正本Skillは変更しないでください。既存の出力はありません。

公開先は `docs/artifacts/skills/generate-domain-model-from-code/` です。隔離したGitプロジェクトで実行し、検査とPNG・HTMLの実表示確認を済ませてから、生成カタログ全体と入力コード、finishの実出力、検証記録、PC・モバイルの実画面、カタログと入力コードを含むZIPを公開先へ保存してください。
```

### 実際の画面

![定期契約と請求のTypeScript2ファイルを読み、4概念・3参照・2領域を整理した全体図と領域別の3図を新規生成しました。](/skills/generate-domain-model-from-code/preview.png)

[画像を原寸で開く](pathname:///skills/generate-domain-model-from-code/preview.png)

新規生成したカタログの実画面を保存し、画像を開いて確認しました。利用者の最終確認は未実施です。

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
## 結果

generate-domain-model-from-code: 完了（検証に合格）

## 出力

- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/model.json`（model モデル情報）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/inventory.json`（inventory コードのスナップショット）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/index.html`（catalog HTMLカタログ）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/manifest.json`（manifest 画像と派生物の検証記録）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/diagrams/domain_0c95c7ece1ce.mmd`（mermaid Mermaid原本）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/diagrams/domain_9cac91c1f544.mmd`（mermaid Mermaid原本）
- `.skill-runs/generate-domain-model-from-code/out/subscription-billing/diagrams/overview.mmd`（mermaid Mermaid原本）

## 既定値で決めた値

````

### 成果物を取得する

- [HTML・Mermaid原本・PNGの一式（ZIP）](pathname:///skills/generate-domain-model-from-code/subscription-billing.zip#download)
- [finishの実出力全文（Markdown）](pathname:///skills/generate-domain-model-from-code/report.md#download)
- [実行と検証の記録（JSON）](pathname:///skills/generate-domain-model-from-code/verification.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/generate-domain-model-from-code/catalog/index.html)
- [実行入力の原本](pathname:///skills/generate-domain-model-from-code/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/generate-domain-model-from-code/execution.json#download)

### 確認した結果

- start・inspect・READMEとコード全22行の読解・新規model作成・build・check・finish を実行し、指摘0件で終了。scopeは未指定の既定値["."]。
- Planはリテラル型を根拠にenum、他3クラスはconcept。参照3本はassociation・参照先1・逆方向nullとしてコードの実記述と根拠行を照合。
- 全3枚のPNGとPC1440px・モバイル390pxの実画面を開き、ラベル・属性・関係線・領域間の参照と可読性を目視。
- 両画面で検索5通り・領域2種類と解除・根拠展開・全3図の拡大と閉じるを操作。横はみ出し・JavaScriptエラー・外部HTTP通信は0件。
- Mermaid全3件を実ダウンロードしbyte一致、全3枚のPNGをブラウザーでも開いて寸法を確認。
- 公開前に個人ホーム名と実環境の詳細版をマスク。ZIP全件の展開内容が公開ファイルとbyte一致。正本全体は実行前後で不変。
- マスク後の公開カタログを正本catalog.pyのcheck/verifyで再検査し合格。

## 確認するポイント

概念・属性・関係がコードの抜粋から言えるかを確認します。抜粋の一致を機械検査できても、業務上の意味の正しさまでは保証しません。コレクション型だけから最小件数や逆方向の多重度を断定したり、参照だけから寿命の所有を断定したりしていないかを見ます。

PNG変換に失敗した場合は成功として渡しません。MermaidとPNGとHTMLはモデル情報からまとめて生成するため、修正はモデル情報へ戻って行います。カタログは外部CDNなしで開けます。

## 正本を読む

[Skill正本](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model-from-code/SKILL.md)と[モデル情報・根拠の仕様](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model-from-code/references/model-format.md)を参照してください。
