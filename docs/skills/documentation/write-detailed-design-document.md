---
title: write-detailed-design-document — 実装と試験へ渡す詳細設計書
sidebar_label: write-detailed-design-document
---

# write-detailed-design-document

要件と基本設計を読み、処理・通信・物理データ・画面・障害時動作の条件がつながる詳細設計書を作ります。基本設計にある振る舞いを、境界の両側と実装・試験の担当者が同じ意味で扱えるまで具体化します。

## 依頼例

```text
docs/requirement.mdとdocs/basic-design.mdから、受付、同じ会話の順次処理、承認回答の詳細設計書を作ってください。
docs/detailed-designに入口文書と関連する設計をまとめ、実装と試験へ渡せるようにしてください。
```

資料を指定しない場合は、`docs`直下の要件と基本設計の一組を探します。候補が複数ある場合は対象を確認します。保存先を指定しない場合は、`.skill-runs/write-detailed-design-document/out/detailed-design/`に作成します。

構成や採用理由を決める段階は[write-basic-design-document](write-basic-design-document.md)、必要な振る舞いや受入条件の整理は[write-requirement-document](write-requirement-document.md)を使います。このスキルでは、入力項目と検査順、状態の遷移条件、保存の確定範囲、同時実行の勝敗、途中停止後の回復と確認条件まで具体化します。

## 進め方

初めに用語、責務、状態、時刻の基準を定義します。そのうえで、機能ごとに目的と根拠、開始条件と入力、処理の流れ、結果、異常・競合・中断、確認方法の順に記述します。

状態名と参照先の食い違いを減らすため、編集する正本を`design.json`に集め、分野別のMarkdownと閲覧用HTMLを同梱スクリプトで生成します。

```text
detailed-design/
├── design.json
├── README.md
├── common.md
├── features.md
├── interfaces.md
├── data.md
├── ui.md
├── recovery.md
├── verification.md
├── evidence.md
└── review.html
```

入口は読む順序と設計の状態を示します。各要件から機能と確認条件を辿り、同じ状態を遷移・保存・画面・返却でどう扱うかを確認できます。対象外や非該当の分野には理由を残します。

`review.html`では、同じ台帳の内容を機能・通信・物理データ・画面・確認条件・状態・並行制御・回復・判断・未決の分野別に読めます。判定役が長い台帳の先頭しか読めなくなることを避けるため、Evalもこの分野単位で判定し、すべての項目の通過を求めます。

図は処理順をシーケンス図、状態を状態図、データの関係をER図で示します。Mermaidの記述をMarkdownへ埋め込み、厳密な条件は台帳の表へつなぎます。採った図と省いた図の理由も残します。画像への変換やブラウザでの描画確認は、このスキルの自動検査には含みません。

## 競合と未検証事項を具体化する

同時到着、重複、期限の直前・等号・直後、保存失敗、応答切断、保存と外部作用の前後の停止、再起動を点検します。保護するデータ、排他範囲、取得順、枠の確保と解放、成否の確定点、再試行の条件を記します。

資料から引き継いだ内容、新しい提案、採用判断、試験で観測した結果を区別します。未検証事項には影響する設計、検証内容、採用できる結果、担当、独立して進められる範囲を残します。資料の不一致や要件変更には、変更前後、理由、影響と判断の出典を付けます。

## 検査と導入

Python 3.9以上の標準ライブラリだけを使います。対象資料と引用の一致、SHA-256、IDと参照、要件と確認条件、採用・検証の証拠の種類、生成文書と台帳の一致を検査します。主キーと一意キーの構成を一か所で定義し、列との整合を確かめます。各境界の要求・応答には項目と型を持たせ、結果による状態変更を共通の遷移へ対応付けます。手書き文書や生成後に編集されたMarkdown・HTMLは上書きしません。

構造検査の通過は、競合時の実装の正しさや、外部接続の実機検証の完了を意味しません。実装へ渡せる具体性、条件の意味、文章のつながり、証拠が主張を支えるかは内容を読んで確認します。

独立測定の第4回は、対象99判定中92件通過、7件不合格でした。nullを許す項目と一律拒否の方針、保存失敗時の状態、返せないエラー、完了済みに対する未完了応答という4種類の不整合が残っています。構造と名前の一致度も未達であり、全項目が収束したスキルとしては扱いません。利用者の選択により追加測定を終え、これらを[既知の限界](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-detailed-design-document/references/limitations.md)として公開しています。利用時は該当する条件を本文で照合してください。

編集する正本は`utils/skills/documentation/write-detailed-design-document/`です。今回の利用者の選択に従い、hooksは導入するプロジェクトの設定へ登録し、利用中の指摘を手元の`.skill-feedback/`へ記録します。Codexの参照先は`.agents/skills/write-detailed-design-document/`です。

```text
python3 .agents/skills/write-detailed-design-document/scripts/setup.py --project .
```

設定と差分を確認して登録します。Codexでは、登録したhooksを`/hooks`で信頼してから自動検査が働きます。`run.py check`と`finish`による検査も同じ契約を使います。

## 成果物の例

備品予約の要件と基本設計から、作成・取消・期限処理・切断後の結果照会を具体化した詳細設計書を作りました。状態、保存の確定、在庫の排他、画面、確認条件をつなぎ、未採用の提案と未検証の影響を分けています。

**到達点：新規作成、本文照合と修正、11文書の生成・検査・finishまで完了。実装・実DB試験・採用承認・実描画は未実施。**

### 実行した依頼

```text
作業ディレクトリは `/private/tmp/write-detailed-design-public-6rui8g6x` です。この中だけで作業してください。

このプロジェクトの `.agents/skills/write-detailed-design-document/SKILL.md` を読み、そのスキルを使って、`docs/requirement.md` と `docs/basic-design.md` から備品予約の詳細設計書を新規作成してください。作成・取消・期限処理・切断後の結果照会を対象とし、実装と試験へ渡せるように `out/detailed-design` へ入口と関連設計をまとめてください。

入力資料とスキルのファイルは変更しないでください。必要な検査と修正は作成した台帳と生成物に対して行い、スキルに従って検査とfinishまで進めてください。実装・実DB・外部サービスへの接続試験と設計採用の承認は行わず、未実施として記録してください。ブラウザの起動やネットワークアクセスは行わないでください。導入・hooks登録・外部投稿・コミット・pushは行わないでください。古い成果物を参照せず、今回の入力から作成してください。最終の返答はスキルのfinishが出した本文をそのまま返してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
<!-- generated-by: write-detailed-design-document; body-sha256: 474c0920395e3e36df45a17781c01bc2e854bff3fbb7c99c753610d799875ca6 -->
# 備品予約の詳細設計書（設計案）

同じ備品を複数の利用者が予約しても在庫を負にせず、取消と期限処理で予約数量を一度だけ戻す設計案である。保存の確定と画面への到達を分け、受付結果の照会で切断後も事実を確認する。共通条件から機能、通信、物理データ、画面、回復、試験条件へ辿る構成とする。採用承認と実装・実DB・外部接続試験は未実施であり、文書検査の通過はこれらを代替しない。

本書は設計書である。文書検査の通過は、採用承認・実装・結合試験の完了を意味しない。

## 対象と状態

数量指定による予約作成、利用者の取消、10分経過時の期限処理、切断・再起動後の受付結果照会と、それらを支える在庫・予約の表示を対象とする。

対象外: 備品の登録・入出庫・総数の変更、アカウント登録、認証方式の実装は対象外とする。既存の認証済みactor_idを受け取る契約だけを定める。<br>外部実行基盤、エージェント、メール、プッシュ送信は使わない。通知は保存後のHTTP応答だけとする。<br>実装作成、実DBの構築・移行実行、負荷・競合試験、外部サービスへの接続、ブラウザとMermaidの実描画確認、採用承認は実施しない。

機能 / 要件 / 未決: 4 / 5 / 5

## 読む順序
````

### 成果物を取得する

- [入口Markdown](pathname:///skills/write-detailed-design-document/out/detailed-design/README.md#download)
- [原本JSON](pathname:///skills/write-detailed-design-document/out/detailed-design/design.json#download)
- [全出力・入力資料ZIP](pathname:///skills/write-detailed-design-document/detailed-design.zip#download)
- [実行担当の最終返答](pathname:///skills/write-detailed-design-document/output.md#download)
- [検証と移動後の再生成手順](pathname:///skills/write-detailed-design-document/verification.md#download)
- [文書検査の記録](pathname:///skills/write-detailed-design-document/validation.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/write-detailed-design-document/out/detailed-design/review.html)
- [実行入力の原本](pathname:///skills/write-detailed-design-document/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/write-detailed-design-document/execution.json#download)

### 確認した結果

- 最終版のスキル全50ファイルを新しい作業場所へコピーし、新しい担当が入力から作成しました。実行前後の正本と実行用コピーは全ハッシュが一致しました。
- 4機能・5要件・5境界・3表・15遷移・16確認条件・未決5件・3図を具体化しました。追加した制約と採用判断・実証結果を区別しています。
- 本文照合で見つかったエラー項目とnull条件を実行担当が修正・再生成・再読し、checkとfinishは指摘0件でした。最終返答とreport本文は一致しました。
- 別の保存場所でrenderとcheckが成功し、元の11出力のハッシュは不変でした。ZIPのCRCと全17ファイルの内容も確認しました。
- 原本中の引用リンクは実行時の一時作業場所を指します。移動先では同梱入力と台帳から再生成できます。
- この例を収束テストの全通過とは扱いません。スキル全体には4種類の不整合と構造・名前の一致度の未達が残っています。
- 実装・実DBの競合試験等・採用承認・ブラウザ操作とHTML/Mermaidの実描画は未実施です。16の確認条件は試験計画です。

## 確認するポイント

- 対象の各要件が、設計または影響付きの未決と確認条件につながっているか。
- 境界の入力・出力・エラーと、保存の責任・原子性が具体的か。
- 競合と途中失敗の勝敗・回復条件が、画面と返却にも一貫しているか。
- 未検証を採用済み・実装済み・検証成功と取り違えていないか。
- 元の記述と場所から、提案・要件変更の理由と影響を追えるか。

## 正本を読む

手順と契約は[SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-detailed-design-document/SKILL.md)、台帳の書き方は同梱の`references/design-guide.md`にあります。
