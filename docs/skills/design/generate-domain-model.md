---
title: generate-domain-model — コードから業務概念と関係を図にする
sidebar_label: generate-domain-model
---

# generate-domain-model

リポジトリのコードを読み、業務上の概念・属性・関係をMermaid原本、PNG、HTMLカタログにまとめます。HTMLでは概念を検索し、領域を選び、図を拡大してコードの根拠を確認できます。

AIがコードを読んでモデル情報を作り、同梱スクリプトが根拠の行と抜粋を検査して図を生成します。コードの意味を完全に自動抽出する解析器ではありません。確認できない分類や多重度は断定せず、確認事項として残します。領域はコードのディレクトリ単位で、DDD上の境界を保証しません。

説明は日本語で書き、図の概念名と関係名にはコードの識別子・参照メンバー名を使います。実行するAIによって訳語が変わることを避け、コードへ辿りやすくします。分類を明示する宣言がないクラスは `concept` とし、idという属性名やfrozenの指定だけでentity・valueとは断定しません。

## 渡す情報

対象リポジトリと調査範囲を渡します。省略すると作業中のリポジトリ全体が対象です。出力名の既定値は `domain-model` で、同名の出力がある場合は別名を指定します。出力先の希望がある場合は、検査後にカタログ全体を渡す場所として伝えます。

Python 3.9以上、インストール済みのMermaid CLIと、CLIから起動できるブラウザーが必要です。CLIを自動取得する処理はありません。`mmdc` がPATH上にない場合は `MMDC`、ブラウザーを指定する場合は `PUPPETEER_EXECUTABLE_PATH` を設定します。対応拡張子・除外対象は[モデル情報の仕様](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/references/model-format.md)で確認できます。

Skill単体の取得は[初めて使う](../getting-started.md)、hooksと一緒に使う配布単位は[pluginガイド](../../plugins/generate-domain-model.md)を参照してください。

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
5. `.skill-runs/generate-domain-model/out/<出力名>/` のカタログを渡します。希望する出力先があれば、検査済みの一式をコピーします。

## 成果物の例

公開用TypeScriptの顧客・定期契約・プラン・請求を読み、4概念と3関係から全体像と2領域の計3図、実PNG、根拠付きHTMLカタログを新規生成しました。

**到達点：finish完了・実PNGとHTMLの表示と操作を確認済み。**

### 実行した依頼

```text
このリポジトリの公開サンプル用TypeScriptコード（Customer、Subscription、Plan、Invoice）を読み、コードの根拠を辿れる日本語のドメインモデル図、Mermaid原本、実PNG、HTMLカタログを作成してください。出力名はsubscription-billingです。調査範囲の指定がない入力は既定値で進め、コードだけでは断定できない分類・関係・多重度は確認事項に残してください。外部投稿や依存の新規ダウンロードは行わず、インストール済みのMermaid CLIとChromeを使用してください。

対象は同梱の `source/` に保存した公開用TypeScriptコードです。実行時はGitを初期化した隔離作業場所へコピーし、出力の名前を `subscription-billing`、対象リポジトリを `.` に指定しました。調査範囲は指定せず既定値を使用しました。

生成後はPNGとHTMLを開いて、文字・関係・読みやすさ・検索・領域選択・拡大・Mermaid原本の取得を実際に確認し、未確認事項を記録してください。検査済みカタログ一式、入力コード、実行本文、検証記録、デスクトップとモバイルの画面画像、閲覧・再現用ZIPを公開成果物として保存してください。
```

### 実際の画面

![定期契約と請求のドメインモデル。全体像・領域別の実PNGと、4概念・3関係のコード根拠を表示したHTMLカタログ。](/skills/generate-domain-model/screenshots/catalog-desktop.png)

[画像を原寸で開く](pathname:///skills/generate-domain-model/screenshots/catalog-desktop.png)

実際に生成したHTMLをChromeで開いた画面です。幅390pxの画面もZIPと成果物のscreenshots/catalog-mobile.pngへ保存しています。

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
## 結果

generate-domain-model: 完了（検証に合格）

## 出力

- `.skill-runs/generate-domain-model/out/subscription-billing/model.json`（model モデル情報）
- `.skill-runs/generate-domain-model/out/subscription-billing/inventory.json`（inventory コードのスナップショット）
- `.skill-runs/generate-domain-model/out/subscription-billing/index.html`（catalog HTMLカタログ）
- `.skill-runs/generate-domain-model/out/subscription-billing/manifest.json`（manifest 画像と派生物の検証記録）
- `.skill-runs/generate-domain-model/out/subscription-billing/diagrams/domain_0c95c7ece1ce.mmd`（mermaid Mermaid原本）
- `.skill-runs/generate-domain-model/out/subscription-billing/diagrams/domain_9cac91c1f544.mmd`（mermaid Mermaid原本）
- `.skill-runs/generate-domain-model/out/subscription-billing/diagrams/overview.mmd`（mermaid Mermaid原本）

## 既定値で決めた値

````

### 成果物を取得する

- [カタログ・入力コード・検証記録の一式（ZIP）](pathname:///skills/generate-domain-model/catalog.zip#download)
- [実際のfinish本文（Markdown）](pathname:///skills/generate-domain-model/report.md#download)
- [全体像の実PNG](pathname:///skills/generate-domain-model/catalog/diagrams/overview.png#download)
- [全体像のMermaid原本](pathname:///skills/generate-domain-model/catalog/diagrams/overview.mmd#download)
- [コード根拠付きモデル（JSON）](pathname:///skills/generate-domain-model/catalog/model.json#download)
- [実行・表示検査と未確認事項（JSON）](pathname:///skills/generate-domain-model/verification.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/generate-domain-model/catalog/index.html)
- [実行入力の原本](pathname:///skills/generate-domain-model/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/generate-domain-model/execution.json#download)

### 確認した結果

- 隔離Git作業場所でinstallと登録検査、start、inspect、コード2ファイルとREADMEの読解、モデル作成、build、check、表示確認、finishを実行。finishは指摘0件。
- Planをリテラル選択型に基づくenum、ほか3クラスをconceptとし、3つの参照関係をassociationとして記録。逆方向の多重度と寿命の所有は未確認として残した。
- 3図をインストール済みMermaid CLIとChromeから生成。根拠行・抜粋、ID、コードスナップショット、Mermaid/HTMLの再生成、PNGのCRCと圧縮データ、manifestのハッシュ検査に合格。
- view_imageで3PNGとデスクトップ・モバイルの実画像を確認。関係ラベルの重なりとHTMLの日本語の文字化けは見られなかった。
- Chrome headlessで12項目と追加9項目に合格。1440×1000と390×844、検索・両領域の絞り込み・拡大・根拠展開・外部通信なしを確認。3つのMermaidを実ダウンロードし原本と一致。
- finish後にコピーした公開カタログを再検査し合格。ZIP内24ファイルのCRCと展開内容のSHA-256が原本と一致し、report.mdはruntimeの保存本文とバイト一致。
- Codexの/hooksによる信頼とセッション内のhooks自動起動、実モバイル端末での操作は未確認。外部投稿・依存の新規ダウンロード・実ユーザー環境へのインストールは未実施。

## 確認するポイント

概念・属性・関係がコードの抜粋から言えるかを確認します。抜粋の一致を機械検査できても、業務上の意味の正しさまでは保証しません。コレクション型だけから最小件数や逆方向の多重度を断定したり、参照だけから寿命の所有を断定したりしていないかを見ます。

PNG変換に失敗した場合は成功として渡しません。MermaidとPNGとHTMLはモデル情報からまとめて生成するため、修正はモデル情報へ戻って行います。カタログは外部CDNなしで開けます。

## 正本を読む

[Skill正本](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/SKILL.md)と[モデル情報・根拠の仕様](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/references/model-format.md)を参照してください。
