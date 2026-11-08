# 文書とPNGの確認記録

2026-11-08に、最終生成物を対象として人手相当の本文照合と実画像確認を行った。図の生成・文書検査と、採用承認・実装・実DB試験は別の確認である。

## 対象

- design.json SHA-256: `ec53a1ca119204242466b9dd35166254d62a39a46c706219444bf2d10397bfa3`
- 既存Mermaid CLI 11.16.0とローカルChromeで70組の.mmd・PNGを生成した。追加取得と外部ネットワーク接続は行っていない。
- sandboxでブラウザー起動が拒否されたため、同じローカルrenderとsheetsを正規の権限要求で再試行した。
- 最後のrenderは終了コード0、MarkdownとHTMLは10件である。生成Markdown・HTMLを直接変更していない。

## 本文の読取りと意味の照合

- design.py readの12分野・全25ページを省略なく読んだ。overview 1/1、sources 1/1、features 1/2〜2/2、interfaces 1/11〜11/11、tables 1/2〜2/2、screens 1/1、checks 1/2〜2/2、states 1/1、concurrency 1/1、recovery 1/1、decisions 1/1、issues 1/1を対象にした。
- 最終生成のREADME.md 1〜62行、evidence.md 1〜429行、70図の説明を読んだ。長い358行目も1〜4500、4501〜9000、9001〜13500、13501〜17754文字に分けて全文を読み、リンク付きの条件を省略していない。
- 要求の必須・任意・NULL方針を照合した。任意の予約IDは欠落を許し、指定nullを拒否する。識別子欠落の事前拒否は応答のrequest_id=nullを許し、foundの保存済みrequest_id・result_atはNULL不可とした。
- 全境界の応答候補ごとにcodeの値域とエラー一覧を照合した。期限処理のapplied・no_op・failed・unconfirmed、結果照会のunrecordedとfailedの項目は互いに独立した定義として再読した。
- ロールバック確認済みのSAVE_FAILEDは状態を保つ。COMMIT結果不明には業務状態維持を断定せず、画面unknownと識別子照会へつなげた。IF004未記録は未着・処理中・不成立を区別できない条件を確認した。
- TR001〜TR003・IF001〜IF003・保存単位・P001/P002・RC001〜RC003・C001〜C014を照合した。期限直前は取消、等号と直後はexpiredであり、ロック待機前の時刻を使わない。終端のended_at必須を保存制約でも明記した。
- 同時識別子衝突は在庫・予約を含め全ROLLBACK後に勝者結果を読む。取消・期限処理はactive条件で一回返却する。過去の作成activeと現在expiredを別の照会・表示として保つ。
- 修正後、F004の照会拒否、IF001〜IF005の変更項目と全候補code、ST002.known、T002.constraints、P001.limit_update、C010.thenを再読した。依存するU001〜U003、C010/C014、UI001と回復条件も照合した。
- 要件変更はなくchangesは非該当とする理由を読んだ。外部実行基盤・外部通知がないため外部作用前後の停止は非該当とする理由を読んだ。
- 各項目直下のMermaidとPNG、厳密な条件の場所、根拠の原文引用・絶対パス行番号リンクと関連条件の要約を確認した。文書の分量は入口62行、各分野3000行以下である。

## 全シートの実画像確認

全18枚をview_imageで実際に開き、全70図について枠・矢印・文字の欠け、重なり、読取り可能性を確認した。図中の「…」は表示側の省略であり、厳密な全文は項目本文に残る。

| シート | 確認した図 | 確認結果 |
| --- | --- | --- |
| [qa/sheet-001.png](qa/sheet-001.png) | local-overview, local-S001, local-S002, local-S003 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-002.png](qa/sheet-002.png) | local-S004, local-S005, local-S006, local-S007 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-003.png](qa/sheet-003.png) | local-S008, local-S009, local-M001, local-M002 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-004.png](qa/sheet-004.png) | local-M003, local-M004, local-ST001, local-ST002 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-005.png](qa/sheet-005.png) | local-D001, local-D002, local-D003, local-D004 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-006.png](qa/sheet-006.png) | local-R001, local-R002, local-R003, local-R004 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-007.png](qa/sheet-007.png) | local-R005, local-F001, local-F002, local-F003 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-008.png](qa/sheet-008.png) | local-F004, local-IF001, local-IF002, local-IF003 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-009.png](qa/sheet-009.png) | local-IF004, local-IF005, local-T001, local-T002 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-010.png](qa/sheet-010.png) | local-T003, local-TR001, local-TR002, local-TR003 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-011.png](qa/sheet-011.png) | local-TR004, local-TR005, local-TR006, local-TR007 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-012.png](qa/sheet-012.png) | local-TR008, local-P001, local-P002, local-RC001 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-013.png](qa/sheet-013.png) | local-RC002, local-RC003, local-UI001, local-C001 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-014.png](qa/sheet-014.png) | local-C002, local-C003, local-C004, local-C005 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-015.png](qa/sheet-015.png) | local-C006, local-C007, local-C008, local-C009 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-016.png](qa/sheet-016.png) | local-C010, local-C011, local-C012, local-C013 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-017.png](qa/sheet-017.png) | local-C014, local-U001, local-U002, local-U003 | 実画像を開き、欠け・重なりなしを確認した。 |
| [qa/sheet-018.png](qa/sheet-018.png) | local-G001-F001, local-G002-T001 | 実画像を開き、欠け・重なりなしを確認した。 |

## 元PNGの拡大確認

一覧で小さくなる縦長の処理・回復図、横に広い条件・未決の図、状態遷移と長いラベルを、次の35件の元PNGで追加確認した。全て実際に開き、ラベル・矢印を読んだ。

- [local-S002.png](diagrams/local-S002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-S007.png](diagrams/local-S007.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-S008.png](diagrams/local-S008.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-ST002.png](diagrams/local-ST002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-D001.png](diagrams/local-D001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-D002.png](diagrams/local-D002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-D003.png](diagrams/local-D003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-D004.png](diagrams/local-D004.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-R001.png](diagrams/local-R001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-R002.png](diagrams/local-R002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-R003.png](diagrams/local-R003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-R004.png](diagrams/local-R004.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-R005.png](diagrams/local-R005.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-F001.png](diagrams/local-F001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-F002.png](diagrams/local-F002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-F003.png](diagrams/local-F003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-F004.png](diagrams/local-F004.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-IF001.png](diagrams/local-IF001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-IF002.png](diagrams/local-IF002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-IF003.png](diagrams/local-IF003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-P001.png](diagrams/local-P001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-P002.png](diagrams/local-P002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-RC001.png](diagrams/local-RC001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-RC002.png](diagrams/local-RC002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-RC003.png](diagrams/local-RC003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-UI001.png](diagrams/local-UI001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C002.png](diagrams/local-C002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C006.png](diagrams/local-C006.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C010.png](diagrams/local-C010.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C011.png](diagrams/local-C011.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C013.png](diagrams/local-C013.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-C014.png](diagrams/local-C014.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-U001.png](diagrams/local-U001.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-U002.png](diagrams/local-U002.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。
- [local-U003.png](diagrams/local-U003.png): 元画像で欠け・重なりがなく、本文と同じ条件の概要であることを確認した。

## 未実施と採用条件

- C001〜C014は試験の設計であり、実装・実DB・外部サービス接続・負荷・移行・実画面の動作試験は実施していない。U001とU002に検証内容・採用条件・担当・依存先・独立して進める範囲を記録した。
- 設計採用の承認は実施していない。D001〜D004は全てproposed・unverifiedであり、実DBと認証の対象版、数値上限・監視間隔・保管期間はU003を含めて採用前に判断記録を残す。
- HTMLは生成内容を確認したが、対話操作を含むブラウザー表示試験は実施していない。PNG描画と実画像確認の範囲だけを実施済みとする。
- 入力資料とスキルのファイルは変更していない。導入・hooks登録・外部投稿・コミット・pushは行っていない。
