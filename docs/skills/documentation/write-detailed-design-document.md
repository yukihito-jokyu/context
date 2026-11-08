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

資料を指定しない場合は、`docs`直下の要件と基本設計の一組を探します。候補が複数ある場合は対象を確認します。保存先は依頼の明示指定、会話で合意した先、既存の設計の保存先を優先します。いずれもなければ`docs/detailed-design/`を使い、選んだ場所を報告します。成果物を`.skill-runs`配下に固定しません。

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
├── review.html
└── diagrams/  # Mermaidの.mmd、PNG、対応とハッシュのmanifest.json
```

入口は読む順序と設計の状態を示します。各要件から機能と確認条件を辿り、同じ状態を遷移・保存・画面・返却でどう扱うかを確認できます。対象外や非該当の分野には理由を残します。

`review.html`では、同じ台帳の内容を機能・通信・物理データ・画面・確認条件・状態・並行制御・回復・判断・未決の分野別に読めます。判定役が長い台帳の先頭しか読めなくなることを避けるため、Evalもこの分野単位で判定し、すべての項目の通過を求めます。

図は各項目の説明の近くに置き、処理順、状態と遷移、要求と応答、物理列、確認条件などを示します。MermaidをMarkdownに記載し、同じ内容の`.mmd`と、実際に変換したPNGを保存します。画像の欠落やソースとの不一致を検査し、文字切れや重なりはPNGを開いて確認します。図で省いた条件の全文は、同じ項目の表に残します。

根拠や関連仕様へのリンクには、その場で必要な条件の引用や要約を添えます。たとえば承認の根拠なら、リンクの直後に「未回答かつ期限前の場合だけ最初の判断を確定する」という条件も読めるようにします。目次やダウンロードを除き、IDや資料名のリンクだけで説明を終えません。

## 競合と未検証事項を具体化する

同時到着、重複、期限の直前・等号・直後、保存失敗、応答切断、保存と外部作用の前後の停止、再起動を点検します。保護するデータ、排他範囲、取得順、枠の確保と解放、成否の確定点、再試行の条件を記します。

資料から引き継いだ内容、新しい提案、採用判断、試験で観測した結果を区別します。未検証事項には影響する設計、検証内容、採用できる結果、担当、独立して進められる範囲を残します。資料の不一致や要件変更には、変更前後、理由、影響と判断の出典を付けます。

## 検査と導入

固有スクリプトはPython 3.9以上の標準ライブラリを使い、PNG変換には既存のNode.js、Mermaid CLIと描画用ブラウザーを使います。追加のパッケージは自動取得しません。対象資料と引用の一致、SHA-256、IDと参照、要件と確認条件、採用・検証の証拠の種類、生成文書と台帳の一致を検査します。主キーと一意キーの構成を一か所で定義し、列との整合を確かめます。各境界の要求・応答には項目と型を持たせ、結果による状態変更を共通の遷移へ対応付けます。手書き文書や生成後に編集されたMarkdown・HTML・図は上書きしません。

構造検査の通過は、競合時の実装の正しさや、外部接続の実機検証の完了を意味しません。実装へ渡せる具体性、条件の意味、文章のつながり、証拠が主張を支えるかは内容を読んで確認します。

保存先・図・参照を新しい価値として、2回の収束テストを行いました。1回目は3題材を各2人が作成し、個別PNG変換、状態図の遷移IDと近くの凡例、入力・応答の抜粋、全文を省略しない分野別読取を修正しました。2回目も同じ3題材を各2人が作成し、予約管理を各2人で追加しました。

| 確認対象 | 1回目：同じ3題材6出力 | 修正後：同じ3題材6出力 | 2回目のみの予約2出力 |
| --- | --- | --- | --- |
| 指定または既定の保存先 | 6/6 | 6/6 | 2/2 |
| 項目に対応し、PNGを読める図 | 3/6 | 6/6 | 2/2 |
| リンクを開かずに必要条件を読める参照 | 2/6 | 6/6 | 2/2 |
| 処理・通信・データ等の内容のAI判定 | 64/73 | 70/74 | 24/25 |

図と参照は独立した担当が実画像と全Markdownを読みました。1回目は446図・54文書、2回目は520図・72文書を確認しました。PNGと引用の存在だけを調べる形式検査は、1回目18/18、2回目24/24通過です。内容の分母は対象のある判定窓で、空の割当は除いています。判定入力の途中省略はありません。

新たな価値は2回目の全8出力で通過しましたが、スキル全体は未収束です。第2回には、履歴世代の制約、保存後の接続失敗、保存試行失敗の応答とエラー一覧、必須ID欠落時の返却、内部引数に関する5判定の不合格が残りました。名前の一致度は.475〜.523で基準.8に届かず、予約管理はファイル集合も.720で未達でした。[既知の限界](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-detailed-design-document/references/limitations.md)には、各不整合を実装前にどう照合するかを記載しています。図の合格を、実装や実DB・実アダプターの検証成功とは扱いません。

違反例37件とhooks11件は通過し、4種類の意味の違反見本は各2人が全件検出しました。確認記録は出力先の`verification-review.md`へ保存します。`qa/`は一覧画像の生成専用であり、手書き記録を置くと次の一覧更新が上書き保護で停止します。

編集する正本は`utils/skills/documentation/write-detailed-design-document/`です。今回の利用者の選択に従い、hooksは導入するプロジェクトの設定へ登録し、利用中の指摘を手元の`.skill-feedback/`へ記録します。Codexの参照先は`.agents/skills/write-detailed-design-document/`です。

```text
python3 .agents/skills/write-detailed-design-document/scripts/setup.py --project .
```

設定と差分を確認して登録します。Codexでは、登録したhooksを`/hooks`で信頼してから自動検査が働きます。`run.py check`と`finish`による検査も同じ契約を使います。

## 成果物の例

備品予約の要件と基本設計から、作成・取消・期限処理・切断後の照会を詳細化しました。指定した保存先へ、各項目に近いMermaidとPNG、リンク先の必要条件の抜粋を備えた文書を新規作成しました。

**到達点：新規作成、本文の修正と再生成、70組のMermaid・PNGの実画像確認、check・finishまで完了。実装・実DB試験・設計採用承認は未実施。**

### 実行した依頼

```text
作業ディレクトリは `/private/tmp/detailed-design-public-nu7gtxsu` です。この中だけで作業してください。

このプロジェクトの `.agents/skills/write-detailed-design-document/SKILL.md` を読み、そのスキルを使って、`docs/requirement.md` と `docs/basic-design.md` から備品予約の詳細設計書を新規作成してください。作成・取消・期限処理・切断後の結果照会を対象とし、実装と試験へ渡せるように `deliverables/reservation-design` へ入口と関連設計をまとめてください。

入力資料とスキルのファイルは変更しないでください。必要な検査と修正は作成した台帳と生成物に対して行い、スキルに従って全PNGの実画像と本文を確認し、checkとfinishまで進めてください。PNG変換と確認用一覧のため、既存のMermaid CLIとローカルブラウザーは利用できます。環境がブラウザー起動を制限する場合は正規の権限要求で再試行してください。追加パッケージの取得や外部へのネットワークアクセスは行わないでください。実装・実DB・外部サービスへの接続試験と設計採用の承認は行わず、未実施として記録してください。導入・hooks登録・外部投稿・コミット・pushは行わないでください。古い成果物を参照せず、今回の入力から作成してください。最終の返答はスキルのfinishが出した本文をそのまま返してください。
```

### 実際の画面

![予約の業務状態遷移図：Mermaidから変換した実PNG](/skills/write-detailed-design-document/deliverables/reservation-design/diagrams/local-ST001.png)

[画像を原寸で開く](pathname:///skills/write-detailed-design-document/deliverables/reservation-design/diagrams/local-ST001.png)

予約の業務状態を示す図です。未保存のabsentからactiveへ進み、期限前の取消でcancelled、保存側の判定時刻が期限以上ならexpiredへ進みます。取消と期限処理が競合しても在庫返却は1回だけです。TR001〜TR003の保存・排他条件は、common.mdの図と同じ項目に記載しています。

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
<!-- generated-by: write-detailed-design-document; body-sha256: 3936242a6a8c1b00ff98343732d12b43a91f9d44c363e124b833e2d26929f3a3 -->
# 備品予約の詳細設計書

利用者は数量を指定して10分間の予約を作成する。保存側で在庫と予約と受付結果を同時に確定し、取消と期限切れの返却を一度に制限する。本書は入力資料を具体化した未承認の設計案であり、実装・実DB・外部サービス接続・負荷試験は未実施である。文書と図の検査は採用承認や動作検証を意味しない。

本書は設計書である。文書検査の通過は、採用承認・実装・結合試験の完了を意味しない。

## 対象と状態

備品予約の作成・取消・期限処理・切断後の結果照会と、それを支える画面・保存・確認条件を設計する。

対象外: 備品の登録・補充・廃棄と認証基盤の実装は対象外とする。備品の総数は予約中に変更しない前提で設計する。<br>貸出・決済・メール・外部実行基盤は入力資料にないため対象外とする。<br>実装、実DBや外部サービスへの接続試験、設計採用の承認は行わず、U001〜U003へ残す。

機能 / 要件 / 未決: 4 / 5 / 3

## 読む順序
````

### 成果物を取得する

- [入口Markdown](pathname:///skills/write-detailed-design-document/deliverables/reservation-design/README.md#download)
- [設計台帳JSON](pathname:///skills/write-detailed-design-document/deliverables/reservation-design/design.json#download)
- [全出力・入力・Mermaid・PNGのZIP](pathname:///skills/write-detailed-design-document/detailed-design.zip#download)
- [実行担当の最終返答](pathname:///skills/write-detailed-design-document/output.md#download)
- [公開例と2回の測定結果](pathname:///skills/write-detailed-design-document/verification.md#download)
- [検査と移動後の再生成記録](pathname:///skills/write-detailed-design-document/validation.json#download)
- [2回の収束テストの数値と残課題](pathname:///skills/write-detailed-design-document/convergence-results.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/write-detailed-design-document/deliverables/reservation-design/review.html)
- [実行入力の原本](pathname:///skills/write-detailed-design-document/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/write-detailed-design-document/execution.json#download)

### 確認した結果

- 最終版のスキル全139ファイルを新しい作業場所へコピーし、新しい担当が入力から実行しました。実行前後の正本とコピーのハッシュは全件一致しました。
- 4機能・5要件・5境界・3表・8遷移・14確認条件・未決3件を具体化し、70組のMermaidとPNGを項目の近くへ配置しました。
- 実行担当が全70図を18枚の一覧で実画像確認し、35図を原PNGでも拡大しました。12分野25ページの照合と修正後の確認をverification-review.mdに記録し、qaには手書き記録を置いていません。親担当も読む順序・作成処理・状態・物理列の代表4PNGを確認しました。
- checkとfinishは指摘0件で、保存した最終返答はreport本文と一致しました。別の保存場所でrenderとcheckも通過し、元の成果物のハッシュは不変でした。ZIPの全179メンバーの内容とCRCを確認しました。
- 同じ3題材6出力で、図の対応と読みやすさは3/6から6/6、参照の必要条件は2/6から6/6へ改善しました。2回目だけの予約2出力も双方通過しました。保存先は全出力で指定または既定に一致しました。
- 第2回の内容評価は94/99通過、5件不合格です。名前の一致度と予約管理のファイル集合も未達で、スキル全体は未収束です。新しい価値の合格と、内容の残課題を分けて記録しました。
- 実装・実DB・外部接続・負荷・移行の試験と採用承認は未実施です。14確認条件は試験計画であり、文書検査とPNGの表示確認を製品試験の成功とは扱いません。原本の出典リンクは実行時の作業場所を指すため、移動先では同梱入力から再生成できます。

## 確認するポイント

- 対象の各要件が、設計または影響付きの未決と確認条件につながっているか。
- 境界の入力・出力・エラーと、保存の責任・原子性が具体的か。
- 競合と途中失敗の勝敗・回復条件が、画面と返却にも一貫しているか。
- 未検証を採用済み・実装済み・検証成功と取り違えていないか。
- 元の記述と場所から、提案・要件変更の理由と影響を追えるか。

## 正本を読む

手順と契約は[SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-detailed-design-document/SKILL.md)、台帳の書き方は同梱の`references/design-guide.md`にあります。
