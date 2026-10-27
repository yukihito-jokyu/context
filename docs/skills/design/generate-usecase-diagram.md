---
title: generate-usecase-diagram — ユースケース図をPNGとHTMLカタログにする
sidebar_label: generate-usecase-diagram
---

# generate-usecase-diagram

要件文または既存のMermaidから、アクターとシステムの機能を示すユースケース図を作ります。編集できるMermaid原本とPNGを保存し、複数の図を一覧・拡大・取得できるHTMLカタログにまとめます。HTMLと画像は相対パスでつながるため、出力ディレクトリを渡すとサーバーなしで閲覧できます。

シーケンス・ER・状態遷移を表す場合は[archify-jp](archify-jp.md)を使います。このスキルではMermaidの専用構文`usecase-beta`を使い、役割と機能の関係を表します。[公式構文](https://mermaid.ai/open-source/syntax/usecase.html)

## 依頼例

```text
注文システムのユースケース図をMermaidとPNGで作り、HTMLカタログにしてください。
会員は注文できます。注文時の支払いは必須です。
会員が希望した場合、クーポン適用を注文に追加します。
運用担当は注文を一覧でき、管理者は運用担当の操作を引き継いで注文を取り消せます。
会員向けと運用向けの2枚に分けてください。カタログ名はorderです。
```

既存原本がある場合は、`.mmd`ファイルの場所とカタログ名を指定します。入力にない認証・支払い・権限の機能は追加しません。include・extend・汎化には、必須処理・条件付き追加・継承する役割や機能の根拠が必要です。

## 進め方

1. 対象システム、アクター、機能、関係を入力から整理します。判断に必要な材料がなければ確認します。
2. 要件からMermaidを作るか、既存原本を指定します。構文解析で宣言・境界・関係を確かめます。
3. 全図をPNGへ変換し、アクターと境界を原本から取得してカタログへ反映します。
4. 原本・PNG・HTML・変換記録の対応を検査し、実画像とカタログの操作を確認します。
5. 全図が成功した後に出力を確定します。更新の依頼がある場合だけ既存カタログを置換します。

出力先は`artifacts/usecase/<catalog-name>/`です。`index.html`、`catalog.json`、`validation.json`と、`diagrams/`内のMermaid・PNGを一緒に保管してください。1図の場合も同じ構成になります。

生成にはPython 3.9以上、既存のMermaid 12完全版、Chromeが必要です。スクリプトはパッケージを自動導入しません。標準の探索で見つからない場合は`USECASE_MERMAID_JS`と`USECASE_CHROME`で場所を指定します。描画はPOSIX向けで、Windowsは未対応です。閲覧時にはMermaidもChromeの描画処理も不要です。

このスキルは`skill-foundation`で作成し、決定表、出力契約、違反例、検査スクリプト、Claude Code・Codex用hooksを同梱しています。hooksとまとめて配布する単位は[plugin](../../plugins/distribution.md)と判断しています。今回の対応範囲はスキル正本とガイド・実行例の追加で、専用pluginの配布物作成・公開・利用環境への導入は含みません。installとhooksの検証は隔離した作業用プロジェクトで行います。

## 成果物の例

図書館システムの貸出と蔵書管理を2枚に分け、Mermaid原本・PNG・HTMLカタログを新規生成した例です。必須の資格確認、希望時の貸出票発行、主任司書の役割継承を表します。

**到達点：start・build・preview・全PNGと実画面の目視・review・check・finishを実施（利用者の最終確認は未実施）。**

### 実行した依頼

```text
図書館システムのユースケース図をMermaid原本・PNG・HTMLカタログで作ってください。カタログ名はlibrary、機能範囲別に次の2枚に分けます。
1. 貸出：利用者は本を借りる。司書も利用者に代わって本を貸し出せる。本の貸出には貸出資格の確認が必須である。利用者が希望した場合にだけ、貸出票の発行を貸出に追加する。
2. 蔵書管理：司書は本を登録できる。主任司書は司書の操作を引き継ぎ、本を除籍できる。
要件にない機能を追加せず、日本語ラベル、include・extend・汎化の向きを確認してください。
```

### 実際の画面

![図書館システムの貸出と蔵書管理の2枚を表示したHTMLカタログの実画面](/skills/generate-usecase-diagram/preview.png)

[画像を原寸で開く](pathname:///skills/generate-usecase-diagram/preview.png)

review後に既存Chromeで保存し、view_imageで開いて確認した実画面です。操作は自動検査で確認し、利用者の最終確認は未実施です。

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
最終の返答は、次の本文をそのまま使う。前後に文を足さず、要約しない。
========================================
## 結果

generate-usecase-diagram: 完了（検証に合格）

## カタログ

- [HTMLを開く](/private/tmp/context-85-public-example/artifacts/usecase/library/index.html)
- 図: 2枚。原本・PNG・HTML・変換記録の対応を検査済み。
- 目視: reviewed

## 出力

- `artifacts/usecase/library/catalog.json`（catalog カタログ情報）
- `artifacts/usecase/library/index.html`（html HTMLカタログ）
````

### 成果物を取得する

- [HTML・Mermaid原本・PNG・変換記録の一式（ZIP）](pathname:///skills/generate-usecase-diagram/catalog.zip#download)
- [finishの実出力全文（Markdown）](pathname:///skills/generate-usecase-diagram/output.md#download)
- [コマンド・画像目視・HTML操作の検証記録（JSON）](pathname:///skills/generate-usecase-diagram/validation.json#download)
- [貸出のMermaid原本](pathname:///skills/generate-usecase-diagram/catalog/diagrams/d01.mmd#download)
- [貸出のPNG](pathname:///skills/generate-usecase-diagram/catalog/diagrams/d01.png#download)
- [蔵書管理のMermaid原本](pathname:///skills/generate-usecase-diagram/catalog/diagrams/d02.mmd#download)
- [蔵書管理のPNG](pathname:///skills/generate-usecase-diagram/catalog/diagrams/d02.png#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/generate-usecase-diagram/catalog/index.html)
- [実行入力の原本](pathname:///skills/generate-usecase-diagram/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/generate-usecase-diagram/execution.json#download)

### 確認した結果

- start・build・preview・review・check・finishは成功。sandbox内の初回buildはChrome exit=-6で停止し、その実行だけ権限レビュー後に再実行して成功しました。
- 全2枚のPNGとpreview後・review後の実画面をview_imageで開き、日本語、境界、関係線を目視しました。include・extend・汎化の向きを要件と照合しました。
- Chromeによる自動操作検査で、一覧2枚、検索0件、拡大と閉じる、原本表示、取得リンク6本、相対リンク、横方向のはみ出しなしを確認しました。
- 追加の対話ブラウザでの手動操作はfile://のURLポリシーにより未実施です。利用者の最終確認は未実施です。
- finishのstdout全文をoutput.mdへ保存し、カタログの7ファイルをZIPの同名ファイルとバイト単位で照合しました。
- sourceManifestで実行前後の正本76ファイルが一致しました。verifyExampleSkillSourceとverifyArtifactsを実行し、全公開ファイルをSHA-256付きで登録しました。

## 確認するポイント

- アクター・機能・include・extend・汎化が入力の要件と一致しているか。
- 日本語ラベルが読め、境界や関係線に欠け・重なりがないか。
- 一覧・検索・PNG拡大・原本表示が使え、同じカードからPNGと原本を取得できるか。
- `validation.json`が全図の成功を示し、原本と画像の対応を検査できるか。未実施の目視や利用者の承認を確認済みとしていないか。

PNGの破損とファイルの不一致は機械で検査できます。要件と図の意味が一致するかは、原本と入力を照合して判断します。

## 正本を読む

詳細な手順と契約は[generate-usecase-diagramのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-usecase-diagram/SKILL.md)を参照してください。作成方針は[Issue #85の承認済み計画](https://github.com/yukihito-jokyu/context/issues/85#issuecomment-6419995961)に記録しています。
